# Section 8: Rancher and Platform Component Lifecycle

*Illustrative only — not production-committed configurations. No live system is upgraded from this document. All examples are version-dependent and labeled as such.*

## 8.1 Component-specific lifecycle guidance

| Component | Upgrade ordering | Config migration | CRD changes | Data/DB requirements | Backup needed | Health check | Rollback limitation |
|---|---|---|---|---|---|---|---|
| Rancher | After K8s, before downstream clusters | `rancher` Helm values | Operator CRDs | etcd/DB (embedded or external) | Yes — config + DB | `kubectl rollout status` | In-place downgrade not supported |
| Nexus | After K8s, before app sync | Helm values | None | PostgreSQL + blobstore | Yes — DB + blobs | `/service/rest/v1/status` | DB schema rollback not supported |
| Harbor | After K8s, before image pulls | Helm values | None | PostgreSQL + Redis + object storage | Yes — DB + blobs | `/api/v2.0/health` | Restore from backup only |
| HAProxy | Before/after K8s (independent) | `haproxy.cfg` | None | None | Yes — config | Health check endpoint | Config rollback supported |
| Nginx | Before/after K8s (independent) | `nginx.conf` | None | None | Yes — config | Health check endpoint | Config rollback supported |
| Keepalived | Before/after K8s (independent) | `keepalived.conf` | None | None | Yes — config | VRRP state | Config rollback supported |
| Argo CD | After K8s API version confirmed | Helm values | Application CRDs | PostgreSQL | Yes — DB + repos | `argocd app list` | Restore from backup |
| Ingress controllers | After cert-manager | Helm values | Ingress CRDs | None | Yes — config | Health check endpoint | Config rollback supported |
| cert-manager | Before ingress controllers | Helm values | Certificate CRDs | None (K8s secrets) | Yes — certs + config | `kubectl rollout status` | Cert rollback not supported |
| Vault/OpenBao | Before dependent apps | Helm values | None | Raft storage + unseal keys | Yes — snapshot + keys | `vault status` | Downgrade unsafe; restore from snapshot |
| Keycloak | After K8s, before OIDC consumers | Helm values | Realm CRDs | PostgreSQL | Yes — DB + realm export | Health endpoint | DB schema rollback not supported |
| Prometheus | After K8s, before dashboards | Helm values | Prometheus CRDs | TSDB storage | Yes — TSDB + config | `/-/healthy` | TSDB rollback not supported |
| Grafana | After Prometheus | `grafana.ini` | None | SQLite/DB | Yes — DB + dashboards | Health endpoint | Config rollback supported |
| Alertmanager | After Prometheus | `alertmanager.yml` | None | None | Yes — config | Health endpoint | Config rollback supported |
| Thanos | After Prometheus | Helm values | Object storage CRDs | Object storage | Yes — object storage | Health endpoint | Object storage rollback unsafe |
| Loki | After Prometheus | Helm values | Loki CRDs | Object storage | Yes — object storage | Health endpoint | Index rollback unsafe |
| Fluent Bit | Independent | `fluent-bit.conf` | None | None | Yes — config | Health endpoint | Config rollback supported |
| Gatekeeper | With admission webhooks | Helm values | ConstraintTemplate CRDs | None | Yes — policies | `kubectl get constraints` | Policy rollback supported |
| Kyverno | With admission webhooks | Helm values | Policy CRDs | None | Yes — policies | `kubectl get policies` | Policy rollback supported |
| Falco | Independent | `falco.yaml` | None | None | Yes — config + rules | `falcoctl` health | Rules rollback supported |
| Trivy | Independent | Config | None | Trivy DB | Yes — DB | Trivy scan health | DB rollback supported |
| Cosign | Independent | None | None | None | Yes — keys | `cosign verify` | Key rollback requires re-sign |

Avoid writing identical generic instructions for components with materially different upgrade mechanisms (e.g., Vault requires unseal keys; cert-manager requires webhook availability; Thanos object storage rollback is unsafe).

## 8.2 Rancher upgrade

Rancher upgrade depends on the target Kubernetes version:

1. Confirm downstream clusters are compatible with target Rancher version.
2. Back up Rancher (embedded etcd or external DB).
3. Upgrade Rancher Helm chart; verify `kubectl rollout status deployment/rancher -n cattle-system`.
4. Verify downstream cluster connectivity.

## 8.3 Nexus and Harbor upgrade

- Nexus: back up PostgreSQL + blobstore; upgrade Helm chart; verify repository metadata integrity.
- Harbor: back up PostgreSQL + Redis + object storage; upgrade Helm chart; verify image pull/pull-through proxy.
- Consistency between metadata and stored artifacts must be validated after upgrade (`curl` artifact URLs).

## 8.4 Vault/OpenBao upgrade

- Back up Raft snapshot + unseal keys before upgrade (see `operations/registry-identity-secrets-recovery.md` Section 7.4).
- Upgrade Vault first, then rotate secrets; applications may need restart after Vault API change.
- Downgrade is unsafe; restore from snapshot if needed.

## 8.5 Keycloak upgrade

- Back up PostgreSQL + realm export.
- Keycloak upgrade may change token formats/claim names; OIDC consumers (Argo CD, Harbor, etc.) must be updated in sync.
- Test login and token issuance after upgrade.

## 8.6 Monitoring stack upgrade

Order: Prometheus → Thanos/Mimir → Grafana → Alertmanager → Loki → Fluent Bit → Tempo.

- Exporter versions must support target Prometheus API/label changes.
- Grafana dashboards may need updates for new data source fields.
- Alertmanager routes must be re-validated.

## 8.7 Health checks and post-upgrade validation

For each component after upgrade:

- Verify the component's health endpoint (`/health`, `/-/healthy`, `/api/v2.0/health`, `vault status`).
- Verify dependent workloads can reach the component.
- Verify CRDs and custom resources are intact (`kubectl get crd`).

## 8.8 Rollback limitations by component

- Supported in-place rollback: HAProxy, Nginx, Keepalived, Fluent Bit, Gatekeeper/Kyverno policies, Falco rules, Grafana config, Alertmanager config.
- Restore from backup only: Nexus, Harbor, Argo CD, Keycloak, Prometheus TSDB, Loki index, Thanos object storage, Vault.
- Forward-fix only / unsafe downgrade: Vault, Keycloak DB schema, Ceph (see `lifecycle/ceph-rook-upgrade.md`), cert-manager certificates.

Never claim a component supports rollback unless upstream documentation confirms it.

---

*SND 004-P11.6 — Rancher and Platform Component Lifecycle (illustrative)*
