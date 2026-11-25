# Platform Add-ons

Optional cluster components that are not part of the Kubernetes baseline. Each one is a separate decision: enable it because a named requirement exists, not because it is on a list.

The site exposes these as a dedicated **Add-ons** page. Selecting an add-on adds its installation step, its Helm values file, and its line in the deploy script. Versions come from `compatibility/version-matrix.md` (section *Platform add-ons*).

## Install Order

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

**Purpose.** Issues and renews X.509 certificates from a `Certificate` resource, so no team hand-copies a TLS secret.

**When to enable.** Always, unless Vault's PKI is consumed directly by every workload. The platform prefers cert-manager with a Vault-backed `ClusterIssuer`: one issuer, one audit path.

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
        secretRef:
          name: cert-manager-vault-token
          key: token
```

**Offline.** Images: `cert-manager-controller`, `cert-manager-webhook`, `cert-manager-cainjector`, `cert-manager-acmesolver` (not used in an air-gapped site). Mirror the chart too.

**Failure mode.** Webhook unavailable → `Certificate` resources stop being issued, and pods that mount an expired secret fail to start. Existing valid certificates keep working. Two replicas and a PodDisruptionBudget are the mitigation, not a guarantee: watch `certmanager_certificate_expiration_timestamp_seconds`.

**Never** run two issuers for the same domain. A self-signed issuer as a bootstrap for the Vault issuer is acceptable only while the Vault path is being built, and must be removed after.

## Metrics Server

**Purpose.** Resource metrics for `kubectl top`, HPA and the VPA recommender.

**When to enable.** Always when HPA or VPA is used. If kube-prometheus-stack is deployed, do not confuse the two: Prometheus is the long-term store, Metrics Server is the fast path the API server aggregates.

```yaml
args:
  - --kubelet-insecure-tls=false
  - --kubelet-preferred-address-types=InternalIP
  - --metric-resolution=15s
replicas: 2
```

**Offline.** One image (`metrics-server`). The APIService registration is part of the chart.

**Failure mode.** `kubectl top` fails and HPA stops scaling; workloads keep running. Check `kubectl get apiservice v1beta1.metrics.k8s.io` first — a broken APIService is the usual cause.

## Vertical Pod Autoscaler

**Purpose.** Recommends (or applies) CPU and memory requests from observed usage.

**When to enable.** When request values are guesses and the cluster has enough headroom to be wrong. **Recommendation mode is the default here.** Auto mode evicts and restarts pods, which is unacceptable for stateful workloads and for anything with a long warm-up.

```yaml
recommender:
  replicaCount: 2
admissionController:
  enabled: true
updater:
  enabled: false          # recommendation only; enable deliberately
```

**Offline.** Three images: recommender, updater, admission-controller.

**Failure mode.** With `updater.enabled: false`, no workload is ever restarted — the risk is ignoring the recommendations. Review `kubectl describe vpa` monthly.

## Descheduler

**Purpose.** Evicts pods so the scheduler can place them better: imbalance, duplicate pods on one node, violated topology constraints.

**When to enable.** Large clusters where the initial placement drifts. It is not a fix for a scheduler that is working correctly, and it must never fight a PodDisruptionBudget.

```yaml
kind: CronJob
schedule: "*/30 * * * *"
deschedulingInterval: 10m
cmdOptions:
  v: 3
strategies:
  - name: RemoveDuplicates
  - name: LowNodeUtilization
    params:
      thresholds: {cpu: 20, memory: 20, pods: 20}
      targetThresholds: {cpu: 50, memory: 50, pods: 50}
```

**Rule.** Two weeks in `--dry-run` first, and read the eviction log. Every eviction is a restart someone has to explain later.

**Offline.** One image. **Failure mode.** Excess eviction causes churn; the protection is the threshold pair and the PDBs, not the descheduler's defaults.

## External DNS

**Purpose.** Creates and removes DNS records from `Ingress`, `Service` and `HTTPRoute` objects.

**When to enable.** When services are created often enough that manual records are a source of outages. In an air-gapped site the only sane providers are RFC2136 against the internal DNS or the CoreDNS etcd provider.

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

**Rule.** `txtOwnerId` must be unique per cluster. Two clusters with the same owner id delete each other's records.

**Offline.** One image. **Failure mode.** A wrong zone or a missing `domainFilters` deletes records it does not own. Start with `policy: upsert-only`, watch for a week, then move to `sync`.

## Trivy Operator

**Purpose.** Continuous vulnerability and configuration scanning, as CRDs.

**When to enable.** When image scanning must be continuous and policy-driven. Not a replacement for CI scanning.

```yaml
trivy:
  ignoreUnfixed: true
  severity: "CRITICAL,HIGH"
operator:
  scanJobTimeout: 5m
  metricsVulnIdEnabled: true
```

**Offline.** Operator image plus the Trivy DB. The DB must be mirrored on a schedule — the operator cannot download it in an air-gapped cluster. Use `trivy.serverURL` against an internal Trivy server, or pre-seed the DB volume.

**Failure mode.** Operator cannot reach the Trivy DB → no new scans; existing reports stay valid.

## OpenTelemetry Operator

**Purpose.** Deploys the OTel Collector for traces, metrics, and logs.

**When to enable.** When the platform needs a unified telemetry pipeline. The backend (Tempo, Jaeger, etc.) must already exist.

```yaml
mode: daemonset
# ... collector config with receivers, processors, exporters
```

**Offline.** Operator image, collector image (contrib), and the target backend image.

**Failure mode.** Collector cannot reach the backend → traces queue locally until the buffer fills, then drop.

---

*Status: DRAFT | Owner: Platform Add-ons Team | Last reviewed: 2026-11-23*