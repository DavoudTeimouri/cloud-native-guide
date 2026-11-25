# MAP-وابستگی

*مثالی است.*

## MAP-وابستگی-1. لایه‌ها

۵ لایه: سیستم عامل، Kubernetes، ذخیره، خدمات پلتفرم، نظارت و امنیت.

جدول‌ها: وابستگی مستقیم، غیرمستقیم، نقاط یکپارچگی حیاتی، فروش شکست، وابستگی بازسازی، وابستگی دایره‌ای.

نمودار وابستگی (Mermaid) هر لایه.

**خطر وابستگی دایره‌ای تحلیل شده:**

۱. `etcd` → `kube-apiserver` — **وابستگی Hard startup (یک‌طرفه)**: kube-apiserver برای حالت دایم کلاست Kubernetes به etcd وابسته است و بدون quorum قابل‌رسانی etcd نمی‌تواند API را سرویس دهد. etcd برای شروع یا ارائه ذخیره کلید-مقدار به kube-apiserver نیاز ندارد؛ etcd یک KV store مستقل است. بنابراین این deadlock mutual نیست و وابستگی دایره‌ای نیست. بارهای کاری در حین outage kube-apiserver ادامه می‌دهند (data-plane متأثر نیست). beating quorum و outage API failure modes و بازیابی متفاوت‌اند: etcd snapshot restore برای beating quorum; restart API server برای outage API. Classification: Hard startup dependency (kube-apiserver → etcd only).

۲. `CoreDNS` → `API_server` — **Management/control-plane dependency**: CoreDNS Entpoints و Service objects خود را به ازایسérver API ثبت می‌کند. اگر API server در پایین باشد، CoreDNS نمی‌کند Entpoints یا به‌روزرسانی Entpoints خود را ثبت کند که به/janne می‌کند CoreDNS نمی‌تواند خود را ثبت کند. API server به CoreDNS برای کار خود وابسته نیست. کش CoreDNS ممکن است ancora names bereitsشده را حل کند. Classification: Management/control-plane dependency (یک-way: CoreDNS به API_server برای ثبت خود зависи).

۳. `Rancher` → `etcd` — **Management/control-plane dependency**: Rancher état etcd_cluster مدیریت می‌کند. اگر etcd قفل شده یا lost باشد، Rancher_cluster state را reconcile کند،_cluster add/remove clusters، یا_topology دقیق را刻镜ować. با این حال، etcd می‌تواند مستقل olarak作为_KV store_ برای_plane_kubernetes_control بدون Rancher running.Functioning. تمدن دسترسی Rancher management یک fall_domainifferent از downstream Kubernetes workload availability است. Classification: Management/control-plane dependency (Rancher به etcd depends, notvice versa).

۴. `cert-manager` → `ClusterIssuer` → `kube-apiserver` — **Management/control-plane dependency**: cert-manager و ClusterIssuer به/api_serveraccessAPI برای certificate rotation, order management, و validation depend. اگر API server در پایین باشد، pending cert orders stall و new cert issuance cannot proceed. با این حال، **Existing certificates can continue serving traffic during a control-plane outage** — the data plane is unaffected. The cert-manager ↔ ClusterIssuer relationship یک normal runtime API interaction (not a bootstrap deadlock) درasmuch as both are control-plane components that depend on the kube-apiserver for their operational plane. Classification: Management/control-plane dependency (cert-manager/ClusterIssuer depend on kube-apiserver for normal operation; existing certs serve traffic independently).

۵. **CNI bootstrap and control-plane connectivity** — **Hard startup dependency**: CNI plugins (Cilium, CoreDNS) برای a functioning control-plane (kubelet, API server) to register node information, pod CIDRs، و endpoint endpoints require. Without control-plane connectivity, CNI نمی‌کند pod networking را initialize کند. این یک dependency bootstrap genuine است: the control plane باید operational باشد قبل از CNI can function. Classification: Hard startup dependency.

۶. **CSI controller/node components and Ceph availability** — **Recovery dependency**: CSI controller/node components depend on Ceph cluster availability for dynamic provisioning of PVs. If Ceph degraded or unavailable باشد، PVCs Pending remain و new volumes cannot be claimed. با این حال، existing volume attachments functional remain (the volume already attached). CSI drivers можуть retry provisioning when Ceph recovers. Classification: Recovery dependency.

۷. **Registry/repository availability during bootstrap and upgrades** — **External dependency**: Container image registries (Harbor, Nexus) به_Kubernetes control_plane external هستند. During bootstrap، registry availability برای container image pulls مطلوب است. During upgrades، registry downtime new image pulls blocks but running workloads continue if images locally present هستند. The registry یک separate service با its own HA configuration است. Classification: External dependency.

۸. **Monitoring/alerting dependencies during component failures** — **Observability dependency**: Monitoring components (Prometheus, Alertmanager) ممکن(collection/alerting capability) را component failures در component losses without causing the monitored services themselves to fail. Alerts may not fire, metrics may not be collected، و dashboards may show no data، workloads continuous running. این یک visibility gap، not a service outage Classification: Observability dependency.

۹. **GitOps recovery dependencies** — **Recovery dependency**: GitOps recovery (Argo CD application restoration) depends on a healthy control-plane to perform application syncs. If the control-plane unavailable باشد، GitOps cannot sync new applications، running applications existing unaffected continue. Recovery requires control-plane restoration before GitOps sync can resume. Classification: Recovery dependency.

ترتیبی بازسازی از لایه OS تا لایه_security.

---

*SND 004-P11.7 — MAP-وابستگی (illustrative)*
