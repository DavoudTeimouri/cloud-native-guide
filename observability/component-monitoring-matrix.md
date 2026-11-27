# Component Monitoring Matrix

*Central index linking detailed runbooks per component group. Illustrative only — not production-committed. Marked as such where indicated.*

This matrix maps each component group (A–H) to its monitoring metrics, alerts, and linked runbooks. It serves as the central index — do not duplicate large content in individual component pages; instead, link from this matrix to the detailed runbooks in `observability/troubleshooting.md` and other runbook sources.

## Component Groups A–H Monitoring Overview

| Group | Components | Key Metrics | Linked Runbook | Alert Rules |
|---|---|---|---|---|
| **A** | Control plane, API server, etcd | `apiserver_request_latency_seconds_bucket{pct="99"}`, `etcd_disk_wal_fsync_duration_seconds_bucket{pct="99"}`, `etcd_server_leader_changes_total` | [troubleshooting.md](troubleshooting.md#kubernetes-api-latency-etcd-performance-quorum) | `APIServerDown`, `DNSPacketDrop`, `CephPoolDegraded` (partial) |
| **B** | CNI (Cilium/Calico), networking | `hubble_observability_flow_dropped_total`, `cni_network_policy_drop_total`, `pod_network_reachable` | [troubleshooting.md](troubleshooting.md#cni-packet-drops-cross-node-connectivity-failures) | `CNIConnectivityLoss`, `DNSPacketDrop` |
| **C** | Ceph, PVC, Registry RGW | `ceph_health_status`, `ceph_pg_degraded`, `ceph_pg_io_rate`, `kube_pod_status_pending{reason="VolumeBoundPending"}`, `harbor_image_pull_success_total` | [troubleshooting.md](troubleshooting.md#ceph-slow-ops-degraded-pgs) | `CephPoolDegraded`, `PVCPending`, `RegistryPullFailed` |
| **D** | Ingress (F5 NIC, NGINX Gateway Fabric, Envoy), L7 LB | `nginx_ingress_controller_requests_total{status="5xx"}`, `tls_handshake_failure_total`, `ingress_tls_certificate_expiry` | [troubleshooting.md](troubleshooting.md#ingress-5xx-tls-errors) | `Ingress5xxSurge`, `CertExpiringSoon` |
| **E** | Vault, Keycloak | `vault_sealed`, `vault_route_auth_login{failure="true"}`, `keycloak_auths_total`, `keycloak_sessions_active` | [troubleshooting.md](troubleshooting.md#vault-sealed-unavailable) | `VaultSealed`, `VaultAuthenticationFailure` |
| **F** | Harbor registry | `harbor_image_pull_attempt_total{result="failed"}`, `harbor_image_push_failure_total`, `harbor_image_pull_duration_seconds_bucket{pct="95"}` | [troubleshooting.md](troubleshooting.md#registry-image-push-failures) | `RegistryPullFailed`, `RegistryPushFailed` |
| **G** | Workload lifecycle (pending, crash-loop, Velero) | `kube_pod_status_pending`, `container_crash_looping_total`, `velero_backup_success_total`, `velero_restore_success_total` | [troubleshooting.md](troubleshooting.md#pods-pending-crashloopbackoff) | `PodPending`, `CrashLoopBackOff`, `VaultSealed` (indirect) |
| **H** | Argo CD, GitOps, CI/CD pipelines | `argocd_app_status_synced`, `argocd_app_reconcile_failure_total`, `prometheus_up` per job | [troubleshooting.md](troubleshooting.md#argocd-out-of-sync-reconciliation-failures) | `ArgoCDOutOfSync`, `PrometheusMissingTargets` |

## Linking to Detailed Runbooks

This matrix **does not duplicate** the full runbook content. Instead:

- Each cell references the relevant section in `observability/troubleshooting.md` by heading anchor (e.g., `#Node-CPU-Memory-Saturation`).
- For group-specific runbooks not in `troubleshooting.md`, create standalone markdown files in `observability/` and reference them here.
- **Never place the same large table or step list in both the matrix and a runbook** — the matrix links, the runbook owns the content.

### Example Link Pattern

```markdown
- **Symptom**: API server unavailable
- **Reference**: [troubleshooting.md](troubleshooting.md#kubernetes-api-latency-etcd-performance-quorum)
- **Action**: Check `apiserver_request_duration_seconds_bucket` p99; verify API server pod health
```

## Optional vs Required Monitoring Components

The following components are **required** (monitoring must be present and healthy for the platform to be supportable):

| Component | Category | Reason |
|---|---|---|
| `node-exporter` | Required | Node hardware metrics; without this, no CPU/memory monitoring exists |
| `kube-prometheus-stack` | Required | Full-stack baseline; includes API server, scheduler, controller-manager metrics |
| `alertmanager` | Required | Notification routing; alerts for all other components flow through this |
| `kube-apiserver` metrics | Required | API server availability and latency are foundational for all operations |
| `etcd` metrics | Required | Cluster state consistency; etcd degradation affects entire cluster |

The following components are **optional** (monitoring is valuable but the platform can operate without them if explicitly disabled):

| Component | Category | Disabling Note |
|---|---|---|
| `thanos-sidecar` | Optional | Long-term retention only; short-term (15d) retention via Prometheus TSDB is sufficient for day-2 ops |
| `vault-exporter` | Optional | Vault status metrics; if Vault is disabled, these are not needed |
| `keycloak-exporter` | Optional | Keycloak authentication metrics; if Keycloak is disabled, these are not needed |
| `harbor-exporter` | Optional | Registry health metrics; if Harbor is disabled or image pulls are not monitored, these are not needed |
| `ceph-exporter` | Optional | Ceph storage metrics; if Ceph is not used, these are not needed |
| `service-mesh exporters` | Optional | If Istio/Ambient is disabled, related metrics are not needed |
| `loki-exporter` | Optional | Logging ingestion metrics; if centralized logging is disabled, these are not needed |

## Upstream Documentation References

- Prometheus operator: <https://prometheus-operator.dev/docs/>
- kube-prometheus-stack: <https://github.com/prometheus-operator/kube-prometheus-stack>
- Alertmanager: <https://prometheus.io/docs/alertmanaging/>
- Grafana dashboards: <https://grafana.com/grafana/dashboards/>
- Cilium Hubble: <https://cilium.io/docs/network/getting-started/hubble/>
- Ceph exporter: <https://github.com/ceph/ceph-exporter>
- Harbor exporter: <https://github.com/goharbor/harbor-exporter>
- Vault exporter: <https://github.com/vault-triumph/vault-exporter>
- Keycloak exporter: <https://github.com/keylessapps/keycloak-exporter>
