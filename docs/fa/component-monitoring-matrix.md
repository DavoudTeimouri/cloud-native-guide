# ماتریسmonitoring کامپوننت

*مذکر مرکزی_links بخش‌های فيталь‌تر به_GetRunbook Detailed. مشاهده只做 — نه producción Commit پیکربندی-production. همانطور که نشان داده شده است*.

این ماتریس گروه‌های کامپوننت (A–H) را بهMetrics، الاعلام و_GetRunbook Linked relevante می-{ch}|r|)karta. مانند یک اینده مرکزی-function — محتوای بزرگ را دوباره تولید نمی‌کنیم؛ به جای آن، از این ماتریس به_GetRunbook دقیق در `observability/troubleshooting.md` و دیگر منابع_GetRunbook لینک می‌دهیم.

## بررسی اجمالی گروه‌های A–H

| گروه | کامپوننت |Metrics کلیدی |_GetRunbook Linked | الاعلام rules |
|---|---|---|---|---|
| **A** | کنترل‌پرود، سرور API، etcd | `apiserver_request_latency_seconds_bucket{pct="99"}`, `etcd_disk_wal_fsync_duration_seconds_bucket{pct="99"}`, `etcd_server_leader_changes_total` | [troubleshooting.md](troubleshooting.md#kubernetes-api-latency-etcd-performance-quorum) | `APIServerDown`, `DNSPacketDrop`, `CephPoolDegraded` (partial) |
| **B** | CNI (Cilium/Calico)، شبکه | `hubble_observability_flow_dropped_total`, `cni_network_policy_drop_total`, `pod_network_reachable` | [troubleshooting.md](troubleshooting.md#cni-packet-drops-cross-node-connectivity-failures) | `CNIConnectivityLoss`, `DNSPacketDrop` |
| **C** | Ceph، PVC، Registry RGW | `ceph_health_status`, `ceph_pg_degraded`, `ceph_pg_io_rate`, `kube_pod_status_pending{reason="VolumeBoundPending"}`, `harbor_image_pull_success_total` | [troubleshooting.md](troubleshooting.md#ceph-slow-ops-degraded-pgs) | `CephPoolDegraded`, `PVCPending`, `RegistryPullFailed` |
| **D** | influx (F5 NIC، NGINX Gateway Fabric، Envoy)، L7 LB | `nginx_ingress_controller_requests_total{status="5xx"}`, `tls_handshake_failure_total`, `ingress_tls_certificate_expiry` | [troubleshooting.md](troubleshooting.md#ingress-5xx-tls-errors) | `Ingress5xxSurge`, `CertExpiringSoon` |
| **E** | Vault، Keycloak | `vault_sealed`, `vault_route_auth_login{failure="true"}`, `keycloak_auths_total`, `keycloak_sessions_active` | [troubleshooting.md](troubleshooting.md#vault-sealed-unavailable) | `VaultSealed`, `VaultAuthenticationFailure` |
| **F** | Harbor registry | `harbor_image_pull_attempt_total{result="failed"}`, `harbor_image_push_failure_total`, `harbor_image_pull_duration_seconds_bucket{pct="95"}` | [troubleshooting.md](troubleshooting.md#registry-image-push-failures) | `RegistryPullFailed`, `RegistryPushFailed` |
| **G** | چرخه عمر workload (pending, crash-loop، Velero) | `kube_pod_status_pending`, `container_crash_looping_total`, `velero_backup_success_total`, `velero_restore_success_total` | [troubleshooting.md](troubleshooting.md#pods-pending-crashloopbackoff) | `PodPending`, `CrashLoopBackOff`, `VaultSealed` (indirect) |
| **H** | Argo CD، GitOps، خطوط conduire CI/CD | `argocd_app_status_synced`, `argocd_app_reconcile_failure_total`, `prometheus_up` per job | [troubleshooting.md](troubleshooting.md#argocd-out-of-sync-reconciliation-failures) | `ArgoCDOutOfSync`, `PrometheusMissingTargets` |

##_links_GetRunbook به GetRunbook دقیق

این matrice **محتوای کامل را تکرار نمی‌کند**. بلکه:

- هر سلول به@section relevant در `observability/troubleshooting.md` به’aideAnchor (مثلاً `#Node-CPU-Memory-Saturation`) ارجاع می‌دهد.
- برای_GetRunbook خاص گروه، فایل markdown{$\acute{e}$} مستقل در `observability/` ایجاد می‌کنیم و اینجا به آن ارجاع می‌دهیم.
- **هرگز جدول بزرگ یا لیست kroppen را هر دو در matrice و_GetRunbook قرار ندهید** — matrice_links،_GetRunbook владелец محتوا است.

### مثال الگو لینک

```markdown
- **Simptom**: API server unavailable
- **Reference**: [troubleshooting.md](troubleshooting.md#kubernetes-api-latency-etcd-performance-quorum)
- **Action**: Check `apiserver_request_duration_seconds_bucket` p99; verify API server pod health
```

## ایزولایی compulsory vs ایزولایی proposta monitoring Components

معتبر تدري components زیر **درآوری (required)** هستند (ناظر وجود داشته باشد و سالم باشد تا پلتفرم قابل پشتیبانی باشد):

| Component | Category | Reason |
|---|---|---|
| `node-exporter` | Required |Metrics سخت‌افزاری nœud; بدون این، Monitoring CPU/memory وجود ندارد |
| `kube-prometheus-stack` | Required |پلیه全部基线; شاملMetrics API server، scheduler، controller-manager است |
| `alertmanager` | Required | yönrouting الاعلام؛ الاعلام سایر Components از طریق این fluflow می‌شود |
| `kube-apiserver` metrics | Required |Metricselage و latency API server پایه تمامی عملیات است |
| `etcd` metrics | Required |State consistency_cluster؛ deferred etcd باعث کل cluster شود |

معتبر تدري components زیر **یزولایی (optional)** هستند (ناظر ارزشمند است اما پلتفرم می‌تواند بدون آن‌ها operasionalized شود اگر اخیراً غیرفعال شده باشد):

| Component | Category | Note غیرفعال‌سازی |
|---|---|---|
| `thanos-sidecar` | Optional |.Long-term retention only؛ retention کوتاه‌مدت (15d) tramite Prometheus TSDB برای ops روزانه-۲ کافی است |
| `vault-exporter` | Optional |Metrics وضعیت Vault؛ اگر Vault غیرفعال باشد، نیازی به آن‌ها ندارید |
| `keycloak-exporter` | Optional |Metrics authentication Keycloak؛ اگر Keycloak غیرفعال باشد، نیازی به آن‌ها ندارید |
| `harbor-exporter` | Optional |MetricsRegistry health؛ اگر Harbor غیرفعال باشد یا pux обраراقشوند، نیازی به این‌ها ندارید |
| `ceph-exporter` | Optional |Metrics_storage Ceph؛ اگر Ceph استفاده نشود، این‌ها لازم نیست |
| `service-mesh exporters` | Optional | اگر Istio/Ambient غیرفعال باشد،Metrics مربوطه لازم نیست |
| `loki-exporter` | Optional |Metrics ingestion Logging؛ اگر centralized logging غیرفعال باشد، این‌ها لازم نیست |