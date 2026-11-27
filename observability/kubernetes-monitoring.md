# Kubernetes Monitoring

## Monitoring Spec Table

| Aspect | Details |
|---|---|
| **Health** | Control plane and worker node stability; API responsiveness; etcd quorum; scheduler and controller-manager liveness |
| **Metrics** | `apiserver_request_latency_seconds_bucket`, `apiserver_request_total`, `apiserver_errors_total`, `etcd_disk_wal_fsync_duration_seconds_bucket`, `etcd_server_leader_changes_total`, `kubelet_cgroup_cpu_cfs_throttled_seconds_total`, `kubelet_memory_working_set_bytes`, `kubelet_volume_stats_capacity_bytes`, `kube_pod_status_total`, `kube_pod_info`, `container_cpu_usage_seconds_total`, `container_memory_usage_bytes`, `kube_proxy_ip_frames_received_total`, `kube_proxy_ip_frames_sent_total`, `core_dns_query_total`, `core_dns_answer_total`, `containerd_task_processed_total` |
| **Collection** | `kube-state-metrics` (object-state metrics: desired/running/replicas, statuses); `cAdvisor`/`kubelet` resource-usage metrics; `Prometheus` scraping `apiserver`, `kubelet`, `kube-proxy`, `containerd` endpoints; `CoreDNS` metrics endpoint; `etcd` Prometheus metrics endpoint |
| **Dashboards** | Control plane: API server latency and error rates; etcd WAL and leader health; scheduler and controller-manager progress; K8s resource usage (CPU/memory requests/limits vs actual); pod status breakdown (pending/running/succeeded/failed); node allocation status; CNI flow metrics; CoreDNS query patterns; container resource consumption; containerd task throughput |
| **Alerts** | `APIServerDown` (up{job="apiserver"} == 0), `HighAPILatency` (apiserver_request_duration_seconds_bucket{pct="99"} > 0.5 for 5m), `EtcdQuorumLoss` (etcd_disk_wal_fsync_duration_seconds{quantile="0.50"} spike or etcd_server_leader_changes_total spike), `KubeletNotReady` (up{kubelet!="true"} == 0), `HighPodPending` (kube_pod_status_pending{reason="Unschedulable"} > 0), `CPUCFSThrottling` (kubelet_cgroup_cpu_cfs_throttled_seconds_total > 0), `ContainerCrashLoop` (container_crash_looping_total increase), `CoreDNSFailure` (core_dns_query_total{answer="false"} > 0), `ContainerdFailure` (containerd_task_processed_total decrease) |
| **SLI/SLO** | API availability SLO: 99.95% over 30d; API latency p99 SLO: 300ms over 30d; etcd quorum SLO: 100% leader availability over 30d; pod scheduling success SLO: 99% of pods scheduled within 5m over 30d; CPU throttle SLO: < 1% of container CPU time throttled over 30d; memory utilization SLO: < 85% average node memory usage over 30d; DNS success SLO: 99.9% over 30d; containerd health SLO: 100% task processing success over 30d |
| **Tuning** | API server request timeout and max request length; etcd compaction and WAL size limits; kubelet CPU/ memory request hardening; pod QOS class placement; service mesh or Ingress controller metric label tuning; cAdvisor resource limits |
| **Troubleshooting** | `kubectl get pods -n kube-system`; `kubectl top node`; `kubectl describe pod <pod> -n <namespace>`; `kubectl logs -n kube-system <pod>`; `kubectl exec -n kube-system etcd/<pod> -- etcdctl endpoint health --cluster`; `crictl pods -a`; `kubectl get events --sort-by=.metadata.creationTimestamp -n <namespace>`; `systemctl status kube-apiserver` `systemctl status kube-controller-manager` `systemctl status kube-scheduler` |
| **Recovery** | Restart stuck kube-apiserver pod (HA); free etcd disk space and defrag (`etcdctl compaction`); scale node pool or adjust resource requests for Unschedulable pods; restart kubelet if crash-looping; rewrite image tag or add pull secret for CrashLoopBackOff; restart CoreDNS or fix ConfigMap; restart containerd service; apply taints/tolerations to unblock scheduling |
| **Dependencies** | kube-apiserver reachable on port 6443; etcd cluster quorum healthy; kubelet agent on each node reachable on port 10250; containerd running on each node; CoreDNS pod healthy in kube-system; kube-state-metrics and cAdvisor exposing metrics; Prometheus scrape configuration correct for all K8s jobs |

## Validation Commands (independent of Prometheus)

| Check | Command | Expected Output |
|---|---|---|
| API server health | `kubectl get --raw "/readyz"` | `readyz` output: `P` for all checks; healthy API server responds within ms |
| API server latency | `curl -s -o /dev/null -w "%{time_total}" https://<api-host>/healthz` | Response time < 1s; p99 from histogram metrics |
| etcd health | `kubectl exec -n kube-system etcd/<pod> -- etcdctl endpoint health --cluster` | `all healthy` reported; leader stability |
| Scheduler status | `systemctl status kube-scheduler` | Active: active (running); `kubectl get pods -n kube-system -l k8s-app=kube-scheduler` |
| Controller-manager status | `systemctl status kube-controller-manager` | Active: active (running); no stuck leadership renewals |
| Kubelet status | `systemctl status kubelet` | Active: active (running); `kubectl get nodes` shows Ready status |
| kube-proxy status | `systemctl status kube-proxy` | Active: active (running); iptables or IPVS mode operational |
| CoreDNS query test | `kubectl exec -it <pod> -- nslookup kubernetes.default.svc.cluster.local` | Resolution succeeds within 1s; `core_dns_query_total` with answer="true" increments |
| Container resource usage | `kubectl top pod -A` | CPU and memory requests/limits vs actual per pod; compares to `container_cpu_usage_seconds_total` and `container_memory_usage_bytes` |
| PVC bound status | `kubectl get pvc -A` | `Bound` phase for all claimed PVCs; `kube_volume_stats_capacity_bytes` matches |
| containerd health | `crictl ps -a` | All containers listed; `containerd_task_processed_total` reflects task throughput |
