# ملاحظات معماری نظارت

*مشاهده فقط — اینştir پیکربندی تولیداتی productions Commit نشده است. همانطور که نشان داده شده است در。*

## بررسی اجمالی

این مستند معماری نظارت و مشاهده‌ای بر سطح کامپوننت برای پلتفرم توصیف می‌کند. آن تعریف می‌کند که چه چیزی نظارت دارد، چگونه و شرایط شکست انتظار چیست. **میãosبه‌های ایزولایی به صراحت با razemдар کردن ضروریそれと明確に識別されています。**

## مؤلفه‌های نظارت

| součást | ضروری | هدف | روش اسکرپ | نظرات |
|---|---|---|---|---|
| `kube-prometheus-stack` | ✅ ضروری | پمetheus تمام استک + Grafana + Alertmanager از طریق Helm | CRDs ServiceMonitor | déploy پیش‌فرض؛Metrics پایه nœud، API و کلاستر را شامل می‌شود |
| `kube-prometheus-stack.thanos` | ایزولایی | نگهداری بلندمدت از طریق Thanos | ServiceMonitor + ذخیره‌سازی شیء | `thanos-query` و `thanos-sidecar` را اضافه می‌کند؛ برای сохранности بیشتر از 15 روز توصیه می‌شود |
| `vault-exporter` | ایزولایی | وضعیت وارد کردن و قفل از Cubbyhole | ServiceMonitor با انتخالیyzer `app=vault-exporter` | مقیاس‌ها: `vault_sealed`, `vault_auth_failures_total` |
| `keycloak-exporter` | ایزولایی | المقیاس‌های احراز هویت و جلسه Keycloak | ServiceMonitor با انتخالیyzer `app=keycloak-exporter` | مقیاس‌ها: `keycloak_auths_total`, `keycloak_sessions_active` |
| `harbor-exporter` | ایزولایی | المقیاس‌های سلامت و pux از ocasiones occassion | ServiceMonitor با انتخالیyzer `app=harbor-exporter` | مقیاس‌ها: `harbor_image_pull_success_total`, `harbor_image_pull_failure_total` |
| `ceph-exporter` | ایزولایی | وضعیت کلاستر ذخیره‌سازی Ceph | ServiceMonitor با انتخالیyzer `app=ceph-exporter` | مقیاس‌ها: `ceph_health_status`, `ceph_pg_degraded` |
| `node-exporter` | ✅ ضروری | المقیاس‌های سخت‌افزاری nœud (CPU، حافظه، دیسک) | ServiceMonitor خودکار همان Sass_discovered kubernetes_sd | پمیتروس استاندارد |
| `pod-exporter` | ✅ ضروری | المقیاس‌های مصرف منبع pods | ServiceMonitor خودکار |summary CPU و حافظه container限制 |
| `alertmanager` | ✅ ضروری | yönleme ureth وإيقاف اعلامیه‌ها | درج شده در kube-prometheus-stack | yön: critiacl→صف،warning→Jira،info→ فقط داشبورد |

## گروه‌ها از A تا H

گروه‌های زیر محدوده نظارت را بر حسب کامپوننت تعریف می‌کنند. هر گروه مجموعه‌ای از قوانین ثبت، guidelines الاعلام و داشبورد Grafana راayah می‌کند.

| گروه | مؤلفه‌ها | المقیاس‌های شامل | داشبورد پیش‌فرض |
|---|---|---|---|
| **گروه A** | کنترل‌پرود، سرور API، etcd | `apiserver_request_latency_seconds_bucket`, `etcd_disk_wal_fsync_duration_seconds_bucket` | بررسی_API و etcd |
| **گروه B** | CNI، شبکه، Cilium | `hubble_observability_flow_dropped_total`, `cni_network_policy_drop_total` | سیاست‌های شبکه و سلامت جریان |
| **گروه C** | ذخیره‌سازی (Ceph، PVC، RGW) | `ceph_health_status`, `ceph_pg_degraded`, `kube_pod_status_pending{reason="VolumeBoundPending"}` | سلامت ذخیره‌سازی و تأخیر I/O |
| **گروه D** | cungelage، تر uncontrolledL7 | `nginx_ingress_controller_requests_total{status="5xx"}, `tls_handshake_failure_total` | سلامت ingress و TLS |
| **گروه E** | sır، احراز هویت | `vault_sealed`, `vault_route_auth_login{failure="true"}, `keycloak_auths_total` | وضعیت auth و sır |
| **گروه F** | registry، condelay pipeline | `harbor_image_pull_success_total`, `harbor_image_pull_attempt_total{result="failed"}` |مقیاس‌های registry و موفقیت pux |
| **گروه G** | برنامه‌ریزی کار، cykl życia | `kube_pod_status_pending`, `container_crash_looping_total`, `velero_backup_success_total` |cheduled وbackup health |
| **گروه H** | GitOps، CI-CD | `argocd_app_status_synced`, `argocd_app_reconcile_failure_total`, `prometheus_up` | GitOps & جریان pipeline health |

## نتایج انتظار + شرایط شکست

هر گروه المقیاس‌های موفقیت تعریف شده و شرایط شکست مشخص هستند. وقتی هر与此指标 crosses его порог، associated alert fia و runbook.invoke می‌شود.

### گروه A — کنترل‌پرود

- **موفقیت**: `apiserver_request_latency_seconds_bucket{pct="99"} < 0.5s` در 30d؛ `etcd_disk_wal_fsync_duration_seconds_bucket{pct="99"} < 5s`
- **شکست**: `up{job="apiserver"} == 0` → `APIServerDown` critical alert؛ `etcd_leader_changes_total` spike > 1/hour

### گروه B — شبکه

- **موفقیت**: `hubble_observability_flow_dropped_total` < 1% از `hubble_observability_flow_total`؛ رویدادی new `cni_network_policy_drop_total` ندارد
- **شکست**: `hubble_observability_flow_dropped_total` افزایش → `CNIConnectivityLoss` critical alert؛ خرابی بارگذاری BPF

###_group C — ذخیره‌سازی

- **موفقیت**: `ceph_health_status == 0`؛ `ceph_pg_degraded == 0`؛ PVC bound rate > 99.9% در 30d
- **شکست**: `ceph_pg_degraded > 0` → `CephPoolDegraded` warning alert؛ toward PVC provisioning failures → `PVCPending` warning

### گروه D — ingress / TLS

- **موفقیت**: Ingress 5xx rate < 0.1%؛ `tls_handshake_failure_total == 0`؛ cert expiry در 30d ندارد
- **شکست**: `nginx_ingress_controller_requests_total{status="5xx"} > 0` → `Ingress5xxSurge` critical alert؛ `tls_handshake_failure_total` aumento

### گروه E — sır / auth

- **موفقیت**: `vault_sealed == 0`؛ `vault_route_auth_login{failure="true"} == 0`؛ شکست ورود secret 없지
- **شکست**: `vault_sealed == 1` → `VaultSealed` critical alert؛auth login failures → `VaultAuthenticationFailure` warning

### گروه F — registry

- **موفقیت**: `harbor_image_pull_success_total / harbor_image_pull_attempt_total > 99.9%`؛ p95 pull latency < 30s
- **شکست**: `harbor_image_pull_attempt_total{result="failed"} > 0` → `RegistryPullFailed` critical alert؛ TLS certificate expiry

###_group G —iklifecycle workload

- **موفقیت**: `kube_pod_status_pending{reason!="Unschedulable"} < 0.5%`؛ `container_crash_looping_total` ثابت یا کاهش
- **شکست**: Pods `Pending` به مدت طولانی -> investigated؛ `container_crash_looping_total` aumento -> `CrashLoopBackOff` diagnostics

###_group H — GitOps / CI-CD

- **موفقیت**: `argocd_app_status_synced == 1` برای تمام اپلیکیشن‌ها؛ `prometheus_up == 1` برای تمام job scrape
- **شکست**: `argocd_app_status_synced == 0` → `ArgoCDOutOfSync` warning alert؛ `prometheus_up == 0` per job → monitoring coverage gap

## upstream References

- پمetheus operator docs: <https://prometheus-operator.dev>
- Grafana dashboard best practices: <https://grafana.com/docs/grafana/latest/dashboards/>
- Alertmanager documentation: <https://prometheus.io/docs/alertmanaging/>
- kube-prometheus-stack chart: <https://github.com/prometheus-operator/kube-prometheus-stack>