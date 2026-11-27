# Platform add-ons

Optional cluster components that are not part of the Kubernetes baseline. Each one is a separate
decision: enable it because a named requirement exists, not because it is on a list.

The site exposes these as a dedicated **Add-ons** page. Selecting an add-on adds its installation
step, its Helm values file, and its line in the deploy script. Versions come from
`compatibility/version-matrix.md` (section *Platform add-ons*).

## Install order

Order matters because later add-ons depend on earlier ones.

| # | Add-on | Depends on | Why the order |
|---|---|---|---|
| 1 | cert-manager | Vault (for the PKI issuer) | Every TLS-dependent add-on needs an issuer first |
| 2 | Metrics Server | — | HPA and VPA both scrape it |
| 3 | Vertical Pod Autoscaler | Metrics Server | The recommender reads metrics |
| 4 | Descheduler | Metrics Server | Eviction decisions use utilisation |
| 5 | external-dns | cert-manager (webhook TLS), internal DNS | Creates records only after the edge VIP exists |
| 6 | Trivy Operator | — | Scans workloads; needs the offline vulnerability DB |
| 7 | OpenTelemetry Operator | — | Collects traces; the backend must accept them |

## cert-manager

**Purpose.** Issues and renews X.509 certificates from a `Certificate` resource, so no team
hand-copies a TLS secret.

**When to enable.** Always, unless Vault's PKI is consumed directly by every workload. The platform
prefers cert-manager with a Vault-backed `ClusterIssuer`: one issuer, one audit path.

**Install shape.**

```yaml
# values.yaml (excerpt)
installCRDs: true
replicaCount: 2
prometheus:
  enabled: true
  servicemonitor:
    enabled: true
extraArgs:
  - --dns01-recursive-nameservers-only=false
```

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: vault-pki
spec:
  vault:
    server: https://vault.internal:8200
    path: pki/sign/platform
    auth:
      kubernetes:
        role: cert-manager
        mountPath: /v1/auth/kubernetes
        serviceAccountRef:
          name: cert-manager-vault-issuer
```

**ClusterIssuer namespace semantics (cert-manager v1.21):** `serviceAccountRef` has no namespace field. The referenced ServiceAccount resolves in cert-manager's configured `--cluster-resource-namespace` — `cert-manager` is only an example and only if that is the configured value. The dedicated ServiceAccount `cert-manager-vault-issuer`, its Role, and its RoleBinding must be created in the configured ClusterResourceNamespace. The RoleBinding subject must identify the actual cert-manager controller ServiceAccount and its actual controller namespace (which may differ from the ClusterResourceNamespace). Verify the effective ClusterResourceNamespace from the cert-manager controller deployment arguments or configuration, as it is not necessarily the Helm release namespace.

**cert-manager v1.21 TokenRequest RBAC:** cert-manager v1.21 no longer grants the controller ServiceAccount permission to create tokens for itself by default. When `serviceAccountRef.name` points to a ServiceAccount, you must create:

- A dedicated ServiceAccount for Vault certificate issuance (`cert-manager-vault-issuer` in the configured ClusterResourceNamespace).
- A narrow Role allowing `create` on `serviceaccounts/token` for that ServiceAccount only, in the ClusterResourceNamespace.
- A RoleBinding allowing the cert-manager controller ServiceAccount (in its actual namespace) to use that Role, in the ClusterResourceNamespace.
- A Vault Kubernetes-auth role (`cert-manager`) bound to that ServiceAccount and its namespace, with `pki/sign/platform` signing permissions.

Example (substitute namespace and ServiceAccount name as needed; the namespace shown is the configured ClusterResourceNamespace, not assumed to always be `cert-manager`):

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cert-manager-vault-issuer
  namespace: <cluster-resource-namespace>
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: cert-manager-vault-token-request
  namespace: <cluster-resource-namespace>
rules:
- apiGroups: [""]
  resources: ["serviceaccounts/token"]
  resourceNames: ["cert-manager-vault-issuer"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: cert-manager-vault-token-request
  namespace: <cluster-resource-namespace>
subjects:
- kind: ServiceAccount
  name: <controller-serviceaccount-name>
  namespace: <controller-namespace>
roleRef:
  kind: Role
  name: cert-manager-vault-token-request
  apiGroup: rbac.authorization.k8s.io
```

**Vault audience:** cert-manager automatically includes the Vault server address from `spec.vault.server` and the issuer-specific audience `vault://vault-pki` (the form `vault://<cluster-issuer-name>` for a ClusterIssuer) in the projected ServiceAccount JWT via the Kubernetes TokenRequest API. Do not describe `https://kubernetes.default.svc` as cert-manager's default audience.

**Kubernetes API audience is conditional:** When Vault uses a configured `token_reviewer_jwt`, cert-manager does not need to add the Kubernetes API audience merely for that reason. When Vault runs outside Kubernetes and reuses the cert-manager JWT for TokenReview, with `token_reviewer_jwt` omitted, the JWT must additionally include the actual Kubernetes API server audience. In that case, configure `serviceAccountRef.audiences` with the API server audience discovered from the cluster — do not use a hardcoded universal value. The automatically generated Vault server and issuer-specific audiences are preserved; `serviceAccountRef.audiences` adds audiences rather than replacing them.

**Safe audience discovery:** Obtain a short-lived token with `kubectl create token` and inspect its `aud` claim to discover the Kubernetes API audience. Do not print or persist a live token in documentation or logs.

**Vault role audience:** For a dedicated ClusterIssuer Vault role using Kubernetes auth, the issuer-specific audience `vault://vault-pki` must match the Vault role's `audience` restriction (the Kubernetes auth role field is `audience`; `bound_audiences` is for JWT auth roles). The actual ClusterIssuer name must match the audience configured in Vault. Keep `bound_service_account_names` and `bound_service_account_namespaces` aligned with the dedicated ServiceAccount and its actual ClusterResourceNamespace.

**ServiceAccount token projection:** cert-manager uses its own ServiceAccount (in the controller namespace) to request a short-lived, projected JWT from the Kubernetes API server and presents it to Vault. Configure an RBAC rule allowing `cert-manager` to request tokens, and a Vault Kubernetes-auth role (`cert-manager`) bound to that ServiceAccount with `pki/sign/platform` signing permissions. Token audiences follow the Vault role configuration; no manually provisioned token Secret is required.

**Offline.** Images: `cert-manager-controller`, `cert-manager-webhook`, `cert-manager-cainjector`,
`cert-manager-acmesolver` (not used in an air-gapped site). Mirror the chart too.

**Failure mode.** Webhook unavailable → `Certificate` resources stop being issued, and pods that
mount an expired secret fail to start. Existing valid certificates keep working. Two replicas and a
PodDisruptionBudget are the mitigation, not a guarantee: watch `certmanager_certificate_expiration_timestamp_seconds`.

**Never** run two issuers for the same domain. A self-signed issuer as a bootstrap for the Vault
issuer is acceptable only while the Vault path is being built, and must be removed after.

## Metrics Server

**Purpose.** Resource metrics for `kubectl top`, HPA and the VPA recommender.

**When to enable.** Always when HPA or VPA is used. If kube-prometheus-stack is deployed, do not
confuse the two: Prometheus is the long-term store, Metrics Server is the fast path the API server
aggregates.

```yaml
args:
  - --kubelet-insecure-tls=false
  - --kubelet-preferred-address-types=InternalIP
  - --metric-resolution=15s
replicas: 2
```

**Offline.** One image (`metrics-server`). The APIService registration is part of the chart.

**Failure mode.** `kubectl top` fails and HPA stops scaling; workloads keep running. Check
`kubectl get apiservice v1beta1.metrics.k8s.io` first — a broken APIService is the usual cause.

## Vertical Pod Autoscaler

**Purpose.** Recommends (or applies) CPU and memory requests from observed usage.

**When to enable.** When request values are guesses and the cluster has enough headroom to be
wrong. **Recommendation mode is the default here.** Auto mode evicts and restarts pods, which is
unacceptable for stateful workloads and for anything with a long warm-up.

```yaml
recommender:
  replicaCount: 2
admissionController:
  enabled: true
updater:
  enabled: false          # recommendation only; enable deliberately
```

**Offline.** Three images: recommender, updater, admission-controller.

**Failure mode.** With `updater.enabled: false`, no workload is ever restarted — the risk is
ignoring the recommendations. Review `kubectl describe vpa` monthly.

## Descheduler

## Installation

Descheduler is installed via the upstream `kubernetes-sigs/descheduler` Helm chart, managed by Argo CD as the single reconciler (ADR-0014). The application version is pinned at `v0.37.0` in `compatibility/version-matrix.md`. The Helm chart version must be verified separately — it may differ from the application version — and is pinned through the repository's image-management process. The chart is mirrored to the internal Helm repository (`registry.internal:5000/charts/`) and installed from there.

```yaml
# Argo CD Application (single reconciler — ADR-0014)
# PLACEHOLDERS: substitute environment-specific values before applying.
#   project:   an existing AppProject (e.g. team-payments, per argocd.md)
#   repoURL:   your registered GitLab repository (e.g. https://gitlab.internal/apps/<team>)
#   path:      repository-relative chart directory (e.g. k8s/descheduler)
#   namespace: deployment namespace (illustrative: descheduler-system)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: descheduler
  namespace: argocd
spec:
  project: <existing-AppProject>
  source:
    repoURL: <registered-GitLab-repository>
    targetRevision: main
    path: <relative-chart-path>
  destination:
    server: https://kubernetes.default.svc
    namespace: descheduler-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

```yaml
# Descheduler Helm values
# Chart: kubernetes-sigs/descheduler (internal Helm mirror)
# Application version: v0.37.0 (compatibility/version-matrix.md)
# Chart version: verify separately; may differ from application version
# Image digest: verify and pin through the repository's image-management process
schedule: "*/30 * * * *"
deschedulingInterval: 10m
strategies:
  - name: RemoveDuplicates
  - name: LowNodeUtilization
    params:
      thresholds: {cpu: 20, memory: 20, pods: 20}
      targetThresholds: {cpu: 50, memory: 50, pods: 50}
```

**Rule.** Two weeks in `--dry-run` first, and read the eviction log. Every eviction is a restart someone has to explain later. Enable `dryRun: true` during the two-week validation period, then set `dryRun: false`.

**Offline.** Mirror the Descheduler Helm chart and its image to `registry.internal:5000/...`. The image digest must be verified and pinned through the repository's approved image-management process; this documentation does not invent an immutable digest.

**Upgrade.** Change the Helm chart version in the Argo CD Application source or values and let Argo CD sync. Rollback: revert the Git commit and re-sync. Removal: delete the Argo CD Application, then remove the Helm release; CRDs are cleaned up by the chart.

**Do not** run `helm install` or `kubectl apply` against the same release outside Argo CD — Argo CD is the single reconciler (ADR-0014).

A raw CronJob manifest is not a production installation method. It may appear only as a non-production educational example, clearly labeled as such, and is not independently managed.

## external-dns

**Purpose.** Creates and removes DNS records from `Ingress`, `Service` and `HTTPRoute` objects.

**When to enable.** When services are created often enough that manual records are a source of
outages. In an air-gapped site the only sane providers are RFC2136 against the internal DNS or the
CoreDNS etcd provider.

```yaml
provider:
  name: rfc2136
env:
  - name: EXTERNAL_DNS_RFC2136_HOST
    value: "10.10.0.53"
  - name: EXTERNAL_DNS_RFC2136_PORT
    value: "53"
  - name: EXTERNAL_DNS_RFC2136_ZONE
    value: "internal.example.com."
  - name: EXTERNAL_DNS_RFC2136_TSIG_KEYNAME
    value: "externaldns-key"
  - name: EXTERNAL_DNS_RFC2136_TSIG_SECRET_ALG
    value: "hmac-sha256"
  - name: EXTERNAL_DNS_RFC2136_TSIG_SECRET
    valueFrom:
      secretKeyRef:
        name: externaldns-tsig-secret
        key: tsig-secret
domainFilters: ["internal.example.com"]
policy: upsert-only
registry: txt
txtOwnerId: "{{clusterName}}"
```
**The TSIG secret is injected through `env.valueFrom.secretKeyRef`, referencing a Kubernetes Secret produced by External Secrets Operator from Vault KV v2.** The secret value never appears in Helm values or Git. See `secrets-management/kubernetes-integration/secret-delivery.md` for the ClusterSecretStore and ExternalSecret patterns.

**Policy.** `upsert-only` creates and updates records but never deletes. Start here and run for at least one week before switching. `policy: sync` adds deletion and requires `--rfc2136-axfr` on ExternalDNS plus DNS server authorization for AXFR from ExternalDNS Pod addresses using the TSIG identity. Without AXFR, `sync` behaves like `create-only` and never deletes stale records.

**Rule.** `txtOwnerId` must be unique per cluster. Two clusters with the same owner id delete each
other's records.

**Offline.** One image. **Failure mode.** A wrong zone or a missing `domainFilters` deletes records
it does not own. Start with `policy: upsert-only`, watch for a week, then move to `sync`.

## Trivy Operator

**Purpose.** Continuous vulnerability and configuration scanning, as CRDs
(`VulnerabilityReport`, `ConfigAuditReport`), not as a CI step.

**When to enable.** When the image supply chain must be observed at runtime, not only at build.

```yaml
trivy:
  ignoreUnfixed: true
  severity: CRITICAL,HIGH
operator:
  scanJobTimeout: 5m
  metricsVulnIdEnabled: true
```

**Offline.** The operator image plus the Trivy DB. The DB must be mirrored on a schedule — the
operator cannot download it in an air-gapped cluster. Use `trivy.serverURL` against an internal
Trivy server, or pre-seed the DB volume.

**Failure mode.** Without a fresh DB, results silently age. Alert on the DB timestamp, not on the
scan count.

## OpenTelemetry Operator

**Purpose.** Runs and configures OpenTelemetry Collectors from a CRD, so instrumentation config is
declarative.

**When to enable.** When traces are required. **Not** a second metrics pipeline: metrics stay in
Prometheus. Traces go to Tempo (or another OTLP backend).

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel
  namespace: observability
spec:
  mode: daemonset
  config:
    receivers:
      otlp:
        protocols: {grpc: {}, http: {}}
    processors:
      batch: {}
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
    exporters:
      otlp:
        endpoint: tempo.observability.svc:4317
        tls: {insecure: false}
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch]
          exporters: [otlp]
```

**Offline.** Operator, collector (contrib), and the target backend images.

**Failure mode.** A collector that cannot reach the backend buffers and eventually drops spans. Set
`memory_limiter` and a queue size; a full collector must never OOM the node.

## Removing an add-on

Removal is a migration, not a delete:

1. Remove the consumers first (Ingress annotations, CRs, webhook configurations).
2. Delete the CRDs last — deleting a CRD deletes every custom resource with it.
3. Confirm nothing still references the add-on's `APIService`, `ValidatingWebhookConfiguration` or
   `MutatingWebhookConfiguration`. A stale webhook in `failurePolicy: Fail` blocks the whole API
   server from creating objects.
