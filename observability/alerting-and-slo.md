# Alerting and SLO Design

*Illustrative only — not production-committed objectives. Marked as such where indicated.*

---

## SLI/SLO Examples (Illustrative)

| Service | SLO Name | Target | Window | Illustrative Mark |
|---|---|---|---|---|
| Kubernetes API | API Availability | 99.95% | 30d | **Illustrative target — not an approved production objective** |
| Kubernetes API | API Latency (p99) | 300ms | 30d | **Illustrative target — not an approved production objective** |
| DNS Resolution | DNS Success Rate | 99.9% | 30d | **Illustrative target — not an approved production objective** |
| CNI | Connectivity Success | 99.9% | 30d | **Illustrative target — not an approved production objective** |
| Ceph | Availability | 99.9% | 30d | **Illustrative target — not an approved production objective** |
| Ceph | PG Degraded Rate < 1% | 1% | 30d | **Illustrative target — not an approved production objective** |
| PVC | Provisioning Success | 99.9% | 30d | **Illustrative target — not an approved production objective** |
| Registry | Image Pull Success | 99.9% | 30d | **Illustrative target — not an approved production objective** |
| Registry | Image Pull Latency (p95) | 10s | 30d | **Illustrative target — not an approved production objective** |
| Vault | Availability | 99.9% | 30d | **Illustrative target — not an approved production objective** |
| Vault | Request Errors | < 0.1% | 30d | **Illustrative target — not an approved production objective** |
| Argo CD | Reconciliation Health | 99% | 30d | **Illustrative target — not an approved production objective** |
| Ingress | Request Success | 99.9% | 30d | **Illustrative target — not an approved production objective** |
| Ingress | Latency (p99) | 500ms | 30d | **Illustrative target — not an approved production objective** |
| Certificates | Renewal Success | 100% per cycle | 30d | **Illustrative target — not an approved production objective** |

---

### Kubernetes API Availability
- **User-visible impact**: Inability to `kubectl apply`, scale, or reconcile resources; GitOps pipelines stall.
- **Measurement definition**: `count(status < 500) / count(total)` over the SLO window.
- **Calculation**: successful HTTP responses (1xx, 2xx, 3xx, 4xx) divided by total requests.
- **Measurement source**: `apiserver_request_count` or `apiserver_request_latency_seconds_bucket` from the KubeAPI exporter.
- **Illustrative target**: Not an approved production objective.

### DNS Resolution Success
- **User-visible impact**: Services cannot resolve each other; internal traffic drops; GitOps agents fail to fetch manifests.
- **Measurement definition**: Successful DNS A/AAAA response count divided by total DNS query count.
- **Calculation**: `dns_responses_successful_total / dns_queries_total`.
- **Measurement source**: CoreDNS `dns_response_total` or `dns_query_total` metrics.
- **Illustrative target**: Not an approved production objective.

### CNI Connectivity
- **User-visible impact**: Pods cannot reach cluster IP services or egress; `ping`/`curl` from pods fails.
- **Measurement definition**: Pod-to-service successful connection count divided by total connection attempts.
- **Calculation**: `hubble_observability_flow_sent_total / hubble_observability_flow_total` (or equivalent CNI flow metrics).
- **Measurement source**: Cilium Hubble flow metrics or kube-proxy metrics.
- **Illustrative target**: Not an approved production objective.

### Ceph Availability + Latency
- **User-visible impact**: RBD/CephFS volume I/O errors; pod restart loops; PVC bound but I/O times out.
- **Measurement definition**: `ceph_health_status == 0` availability; `ceph_mon_command_latency_seconds` p99 latency.
- **Calculation**: availability = `1 - (ceph_cluster_stale_osds + ceph_cluster_missing_osds) / total_osds`; latency p99 from histogram.
- **Measurement source**: ceph-exporter or Ceph MGR Prometheus module.
- **Illustrative target**: Not an approved production objective.

### PVC Provisioning Success
- **User-visible impact**: Pods pending; applications fail to start; storage-related errors in logs.
- **Measurement definition**: PVC bound count divided by PVC creation count over the window.
- **Calculation**: `count(kubelet_volume_stats_capacity_bytes{job="node"} > 0 and kube_phase == "Bound") / count(kube_pod_info)` — approximate; actual measurement via Velero or CSI endpoint metrics.
- **Measurement source**: CSI driver metrics, Node volume stats, or Velero backup/restore metrics.
- **Illustrative target**: Not an approved production objective.

### Registry Image Pull Success + Latency
- **User-visible impact**: Pods stuck in `ImagePullBackOff`; deployments stall; CI pipelines timeout.
- **Measurement definition**: Successful image pull count divided by total pull attempts; p95 pull latency.
- **Calculation**: `harbor_image_pull_success_total / harbor_image_pull_attempt_total`; latency p95 from `harbor_image_pull_duration_seconds_bucket`.
- **Measurement source**: Harbor exporter metrics.
- **Illustrative target**: Not an approved production objective.

### Vault Availability + Request Errors
- **User-visible impact**: Secrets rotation fails; database credentials rotation blocked; applications crash on startup missing creds.
- **Measurement definition**: `up{vault="true"} == 1` for availability; `rate(vault_route_auth_login[5m])` failure rate for errors.
- **Calculation**: availability = `count(vault_sealed == 0) / count(total)`; error rate = `rate(vault_audit_auth_failure[5m])`.
- **Measurement source**: Vault telemetry/exporter metrics (`vault_sealed`, `vault_audit_auth_failure`).
- **Illustrative target**: Not an approved production objective.

### Argo CD Reconciliation Health
- **User-visible impact**: Drift not detected; applications out of sync; desired state not enforced.
- **Measurement definition**: Successful reconciliation count divided by total reconciliations; `argocd_app_status_synced` ratio.
- **Calculation**: `sum(argocd_app_reconcile_success) / sum(argocd_app_reconcile_total)`.
- **Measurement source**: Argo CD API (`/api/v1/applications`) status fields or Argo CD telemetry.
- **Illustrative target**: Not an approved production objective.

### Ingress Request Success + Latency
- **User-visible impact**: 5xx responses from ingress; users cannot load pages; API consumers get errors.
- **Measurement definition**: Successful HTTP response count divided by total; p99 latency from ingress controller.
- **Calculation**: `nginx_ingress_controller_requests_total / nginx_ingress_controller_requests_total{status_code=~"[23].."}`; latency p99 from histogram.
- **Measurement source**: NGINX Ingress Controller metrics or NGINX Gateway Fabric metrics.
- **Illustrative target**: Not an approved production objective.

### Certificate Renewal Success
- **User-visible impact**: TLS errors in browsers; service mesh mTLS handshake failures; ingress TLS termination breaks.
- **Measurement definition**: Certificate renewal run count where `post_renewal_validity > 0`.
- **Calculation**: `count(certificate_renewal_success == true) / count(certificate_renewal_attempts)`.
- **Measurement source**: cert-manager `certificate_condition` or Vault PKI endpoint metrics.
- **Illustrative target**: Not an approved production objective.

---

## Alert Design

| Alert | Severity | Runbook Reference | First Diagnostic Action |
|---|---|---|---|
| `APIServerDown` | critical | troubleshooting/kubernetes.md #API-Server-Unavailable | Check `up{job="apiserver"} == 0`; verify API server pod health |
| `DNSPacketDrop` | warning | troubleshooting/kubernetes.md #DNS-Resolution-Failures | Check CoreDNS pod status; query `kubernetes.default.svc.cluster.local` from a pod |
| `CNIConnectivityLoss` | critical | troubleshooting/kubernetes.md #Pods-Stuck-in-Pending | Check Cilium pods; verify Hubble flow health |
| `CephPoolDegraded` | warning | troubleshooting/kubernetes.md #Ceph slow ops + degraded PGs | Check `ceph_pool_degraded` count; PG state via `ceph pg ls` |
| `PVCPending` | warning | troubleshooting/kubernetes.md #Pods-Stuck-in-Pending | Check PVC `phase: Bound`; storage class provisioner logs |
| `RegistryPullFailed` | critical | troubleshooting/kubernetes.md #Pods-Stuck-in-ContainerCreating | Check image pull secret; verify registry reachability |
| `VaultSealed` | critical | troubleshooting/kubernetes.md #Vault sealed/unavailable | Check `vault_sealed == 1`; unseal if needed |
| `ArgoCDOutOfSync` | warning | troubleshooting/kubernetes.md #Argo-CD-OutOfSync-Reconciliation-Failures | Check `argocd app get <app> --json` for sync status |
| `Ingress5xxSurge` | critical | troubleshooting/kubernetes.md #Ingress-5xx--TLS-errors | Check ingress 5xx rate; backend health |
| `CertExpiringSoon` | warning | troubleshooting/kubernetes.md #Certificate-Renewal-Success | Check cert-manager certificates; cert approaching `notAfter` |

**Alert grouping**: Alerts are grouped by `cluster`, `namespace`, `job` to keep cardinality low. Critical alerts route to on-call pager; warnings to ticket queue; info to dashboard only.

**Inhibition**: `ClusterDown` inhibits all node-level and service-level alerts in that cluster. `APIServerDown` inhibits all namespace-level application alerts when the API is unavailable.

**Receiver design**:
- `critical` → PagerDuty/Slack #on-call-alerts
- `warning` → Jira ticket queue / Slack #alerts-warnings
- `info` → Grafana dashboard only; no notifications

---

## Burn-Rate Alerting

Burn-rate alerts track the rate at which the error budget is consumed relative to time remaining in the SLO window.

| Severity | Short Window | Long Window | Factor |
|---|---|---|---|
| critical | 5m | 1h | 14.4 |
| warning | 30m | 6h | 6 |

**Example**: If the API Availability SLO is 99.95% over 30d and the error budget is 0.05%, a burn-rate of 14.4x in the 5m short window means the budget would be exhausted in ~5m / 14.4 ≈ 21 seconds at the current rate. This triggers a critical alert even though the 30d average may still look healthy.

Burn-rate is calculated as: `(sli_rate / sli_target) * (window_remaining / window_elapsed)`.

- When burn-rate > 1: budget being consumed at or below the planned rate.
- When burn-rate ≥ threshold (e.g., 3 for warning, 7 for critical): budget depleting faster than planned → alert.

---

## Anti-Patterns (to avoid)

- **Excessive cardinality**: Adding `pod_uid`, `request_id`, or per-user labels to metrics that are then used in alerts → Prometheus performance degradation.
- **Duplicate alerts**: Same condition alerting through multiple jobs/receivers → notification storms.
- **Alert fatigue**: High-volume low-value alerts engineers learn to ignore → critical alerts buried.
- **Low-value dashboards**: Dashboards that are never reviewed → wasted maintenance effort.
- **Missing scrape targets**: ServiceMonitor selector misconfiguration → silence; no alert that Prometheus is down.
- **Silent monitoring failures**: Alertmanager down, Thanos sidecar degraded — no one notices because no alert covers the monitor itself.
- **Excessive Prometheus memory**: Unbounded label sets, huge recording rules, or long retention without adequate storage.
