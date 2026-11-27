# External DNS

External DNS publishes DNS records for Services and Ingresses to the internal DNS server. It is a cluster-scoped component that reads Kubernetes resources and writes to the DNS control plane. Kubernetes RBAC and DNS-provider authorization are separate concerns: RBAC governs what ExternalDNS may read from the API server; DNS credentials govern what it may write to the DNS server.

## RBAC and permissions

ExternalDNS runs with cluster-scoped RBAC by default (`rbac.create: true`). It requires Kubernetes read/list/watch permissions on `Ingress`, `Service`, and (optionally) `HTTPRoute` resources for each enabled source. Gateway API (`HTTPRoute`) permissions are required only when the Gateway API source is enabled; do not add them otherwise.

The chart supports namespace-scoped operation (`namespaced: true`), which creates Role/RoleBinding instead of ClusterRole/ClusterRoleBinding. Namespace-scoped mode limits ExternalDNS to resources in one namespace and avoids cluster-scoped RBAC for Gateway sources. Choose cluster-wide mode when ExternalDNS manages records across multiple namespaces; choose namespace-scoped when a single application team owns a dedicated namespace.

## RFC2136 configuration (air-gapped)

In an air-gapped site the only supported providers are RFC2136 against the internal DNS or the CoreDNS etcd provider. Public providers (Route 53, Cloudflare, etc.) require internet connectivity and are not usable offline.

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

- `EXTERNAL_DNS_RFC2136_TSIG_SECRET` is sensitive and must never appear in Git or Helm values. It is injected only through the verified `env.valueFrom.secretKeyRef` structure above, referencing a Kubernetes Secret produced by External Secrets Operator from Vault KV v2.
- Host, port, zone, key name, and algorithm are non-sensitive configuration and may remain as plain `value` entries.
- The chart exposes `env` as a standard Kubernetes environment-variable list. `envFrom` and `extraEnv` are not supported by chart 1.23.0.

## Secret delivery (Vault KV → ExternalSecret → K8s Secret)

Store the TSIG secret in Vault KV v2, then use External Secrets Operator to sync it into a Kubernetes Secret referenced by `secretKeyRef`. See `secrets-management/kubernetes-integration/secret-delivery.md` for the ClusterSecretStore and ExternalSecret patterns. The Vault secret path is distinct from Vault PKI certificate issuance; do not confuse KV credentials with PKI intermediates.

Chart version: `external-dns` 1.23.0 (application `v0.23.0`). See `compatibility/version-matrix.md`.

## Air-gap deployment

- Mirror the `external-dns` Helm chart and container image to `registry.internal:5000/...`.
- At runtime, ExternalDNS must reach the RFC2136 DNS server (e.g. `10.10.0.53`) over TCP/UDP port 53. An internet-isolated cluster is not the same as a DNS control plane that is unreachable: Kubernetes can be air-gapped while the internal DNS remains reachable.
- Mirror chart and images per `offline-artifacts/artifact-matrix.md`.

## DNS safety and production behavior

- `domainFilters` restricts ExternalDNS to the zones it may touch. A missing or over-broad filter lets ExternalDNS create or delete records outside its intended scope.
- `registry: txt` uses TXT ownership records. `txtOwnerId` must be unique per cluster; two clusters sharing an owner ID delete each other's records.
- Start with `policy: upsert-only`. ExternalDNS creates and updates records but never deletes. Run for at least one week before switching.
- `policy: sync` adds deletion. It requires `--rfc2136-axfr` (zone transfer) on the ExternalDNS command, and the DNS server must authorize AXFR from ExternalDNS Pod addresses using the TSIG identity. Without AXFR, `sync` behaves like `create-only` and never deletes stale records.
- A wrong zone or missing `domainFilters` can delete records ExternalDNS does not own. Validate in `upsert-only` first.

## Secret rotation

TSIG secret rotation follows: Vault KV update → ESO refresh (on `refreshInterval`) → Kubernetes Secret update → ExternalDNS Deployment rollout restart. Environment variables are read at process start; they do not update inside an already-running ExternalDNS process. After the K8s Secret changes, trigger `kubectl rollout restart deployment externaldns -n <ns>` (or the namespace ExternalDNS runs in).

## Monitoring and troubleshooting

- `kubectl get deployment external-dns -n <namespace>` — verify the ExternalDNS Deployment exists and is available.
- `kubectl get pods -l app.kubernetes.io/name=external-dns -n <namespace>` — inspect ExternalDNS pods.
- `kubectl describe deployment external-dns -n <namespace>` — inspect Deployment events and configuration.
- `kubectl logs -n <namespace> -l app.kubernetes.io/name=external-dns --tail=100` — inspect record creation failures.
- `nslookup <service>.<zone>` from inside the cluster — confirm the record resolves.
- The metrics endpoint is on port 7979; do not invent metric names.

## Related documentation

- Secret delivery: `secrets-management/kubernetes-integration/secret-delivery.md`
- Version pins: `compatibility/version-matrix.md`
- Air-gap artifacts: `offline-artifacts/artifact-matrix.md`
