# Advanced Cross-Component Troubleshooting Workflows

Each workflow follows: symptoms → dashboards+alerts → initial diagnostic commands → isolate failing layer → root-cause investigation → safe corrective actions → post-recovery validation.

---

## Node CPU / Memory Saturation

| Step | Action |
|---|---|
| **Symptoms** | Pods evicted; kubelet reports `MemoryPressure` or `CPUThrottling`; node `NotReady` |
| **Dashboards+Alerts** | Node `cpu_cfs_throttled_total` rate > 0; `node_memory_Active_bytes` trend vs capacity; `node_exporter_memory_Active_bytes` |
| **Initial diagnostic commands** | `kubectl top node <node>`<br>`kubectl describe node <node>`<br>`ssh <node> "free -h && vmstat 1 5"` |
| **Isolate failing layer** | Check if saturation is node-wide (all pods affected) or per-pod (specific deployment impacted). Look at `kubelet_summary_bytes_total` vs `node_total_memory_bytes`. |
| **Root-cause investigation** | - Oversized deployment requesting more than available<br>- Memory leak in application container<br>- kubelet cache pressure or OOMScore adjustment too high<br>- CPU share competition between namespaces |
| **Safe corrective actions** | - Scale back deployment replica count or resource requests<br>- Restart misbehaving pod<br>- Adjust `limit` vs `request` if requests were too aggressive<br>- Evict pod with `kubectl patch pod <pod> -p '{"spec":{"terminationGracePeriodSeconds":0}}'` if stuck |
| **Post-recovery validation** | `kubectl top node <node>` shows utilization below thresholds; `kubectl get pod <pod> -o jsonpath='{.status.phase}'` = Running; monitor for 15m to confirm stable |

---

<a id="kubernetes-api-latency-etcd-performance-quorum"></a>
## Kubernetes API Latency, etcd Performance + Quorum

| Step | Action |
|---|---|
| **Symptoms** | `kubectl` commands timeout; API responses 5xx; etcd `etcdctl endpoint health` warnings |
| **Dashboards+Alerts** | `apiserver_request_duration_seconds_bucket` p99 latency; `etcd_disk_wal_fsync_duration_seconds` p99; `etcd_server_leader_changes_total` spike |
| **Initial diagnostic commands** | `kubectl get nodes -o wide`<br>`kubectl get pods -n kube-system -l k8s-app=kube-apiserver`<br>`kubectl exec -n kube-system etcd-<node> -- etcdctl endpoint health --cluster` |
| **Isolate failing layer** | Determine if latency is from the API server process, network path to API server, or etcd response time. Check `apiserver_hard_errors_total` for error type. |
| **Root-cause investigation** | - CPU throttling in apiserver pod<br>- etcd disk latency or disk full<br>- Network MTU mismatch or packet loss between nodes and control plane<br>- etcd compaction lag or WAL flood |
| **Safe corrective actions** | - Restart kube-apiserver pod if stuck<br>- Free etcd disk space; defrag if needed (`etcdctl compaction`)<br>- Upgrade etcd disk to lower latency storage<br>- Scale API server replicas if running HA |
| **Post-recovery validation** | `kubectl get pods` responds within < 1s; `etcdctl endpoint health` reports all healthy; API latency p99 back below SLO target |

---

## Pods Pending / CrashLoopBackOff

| Step | Action |
|---|---|
| **Symptoms** | `kubectl get pods` shows `Pending` indefinitely or `CrashLoopBackOff` |
| **Dashboards+Alerts** | `kube_pod_status_pending{reason="Unschedulable"} > 0`; `container_crash_looping_total` increase |
| **Initial diagnostic commands** | `kubectl describe pod <pod> -n <namespace>`<br>`kubectl get events --sort-by=.metadata.creationTimestamp -n <namespace>`<br>`crictl pods -a` (if container runtime accessible) |
| **Isolate failing layer** | - `Pending` → scheduling problem (resources, node selectors, taints)<br>- `CrashLoopBackOff` → runtime error, image issue, or startup command failure |
| **Root-cause investigation** | **Pending**: Insufficient CPU/memory, node selector/affinity mismatch, taints/tolerations, PVC not bound, default namespace resource quotos.<br>**CrashLoopBackOff**: Wrong image name/ tag, image pull secret missing, container command exits with non-zero, missing filesystem mount. |
| **Safe corrective actions** | **Pending**: Adjust resource requests; fix node selectors/affinity; add tolerations; wait for PVC binding; scale node pool.<br>**CrashLoopBackOff**: Fix image reference; add/fix image pull secret; check `kubectl logs <pod> -c <container>` for exit code; review container entrypoint. |
| **Post-recovery validation** | `kubectl get pod <pod> -n <namespace>` shows `Running`; `kubectl logs <pod> -c <container>` shows expected output; no new events in last 5m. |

---

<a id="cni-packet-drops-cross-node-connectivity-failures"></a>
## CNI Packet Drops, Cross-Node Connectivity Failures

| Step | Action |
|---|---|
| **Symptoms** | Pods can't reach service ClusterIP; `curl` from pod times out; `hubble observe` shows dropped flows |
| **Dashboards+Alerts** | `hubble_observability_flow_dropped_total` increase; `cni_network_policy_drop_total` increase; `pod_network_reachable` decrease |
| **Initial diagnostic commands** | `kubectl exec -it <pod> -- ip a`<br>`kubectl exec -it <pod> -- ping <service-clusterip>`<br>`kubectl logs -n kube-system -l k8s-app=cilium` |
| **Isolate failing layer** | Check if drop is inbound/outbound, NodePort vs ClusterIP, inter-node vs intra-node. Check Cilium status DaemonSet pods; verify BPF program load. |
| **Root-cause investigation** | - BPF program load failure (kernel version mismatch)<br>- BPF JIT compilation denied (sysctl `kernel.bpf_jit_harden`)<br>- NetworkPolicy blocking traffic<br>- MTU mismatch across nodes<br>- IP address exhaustion (CIDR too small) |
| **Safe corrective actions** | - Restart Cilium DaemonSet: `kubectl rollout restart daemonset/cilium -n kube-system`<br>- Adjust MTU uniformly across nodes<br>- Review NetworkPolicy rules for unintended blocks<br>- Increase IPv4 pod/CIDR size if exhausting |
| **Post-recovery validation** | `kubectl exec -it <pod> -- curl -s -o /dev/null -w "%{http_code}" <service>` returns 200 or expected code; hubble dropped flows back to baseline; no new policy drop events. |

---

## DNS Resolution Failures

| Step | Action |
|---|---|
| **Symptoms** | Pods cannot resolve `kubernetes.default.svc.cluster.local` or external DNS names; `nslookup` timeout |
| **Dashboards+Alerts** | `dns_response_total{answer="false"} > 0`; CoreDNS pod restarts; `dns_query_latency_seconds` p99 spike |
| **Initial diagnostic commands** | `kubectl get pods -n kube-system -l k8s-app=kube-dns`<br>`kubectl logs -n kube-system -l k8s-app=kube-dns`<br>`kubectl exec -it <pod> -- nslookup kubernetes.default.svc.cluster.local` |
| **Isolate failing layer** | - CoreDNS pod unhealthy → cluster-wide<br>- Upstream DNS unreachable → resolver config issue<br>- NetworkPolicy blocking port 53 → network policy block<br>- ConfigMap incorrect → CoreDNS ConfigMap customization |
| **Root-cause investigation** | Check CoreDNS pod status; `kubectl describe configmap coredns -n kube-system` for custom plugins; verify `upstream` directive reachability; check NetworkPolicy allow rules for UDP/53. |
| **Safe corrective actions** | - Restart CoreDNS: `kubectl rollout restart deployment/coredns -n kube-system`<br>- Fix upstream DNS IPs in ConfigMap<br>- Add NetworkPolicy allow rule for DNS if missing<br>- Revert recent CoreDNS ConfigMap changes |
| **Post-recovery validation** | All pods can `nslookup kubernetes.default.svc.cluster.local` within 1s; DNS dashboard shows `answer="false"` back to 0; no new CoreDNS restarts. |

---

## Ceph Slow Ops + Degraded PGs

| Step | Action |
|---|---|
| **Symptoms** | RBD volume I/O latency spikes; `ceph -s` reports degraded PGs; application timeout on disk I/O |
| **Dashboards+Alerts** | `ceph_osd_op_duration_seconds` p99 > threshold; `ceph_pg_degraded` count > 0; `ceph_pg_io_rate` drop |
| **Initial diagnostic commands** | `ceph -s`<br>`ceph pg ls degraded`<br>`ceph pg stat`<br>`ceph osd stat` |
| **Isolate failing layer** | Determine if PGs are degraded, incomplete, or active+undersized. Check OSD health, disk S.M.A.R.T., and network between nodes and OSDs. |
| **Root-cause investigation** | - OSD down or out → data rebalancing<br>- Disk latency or disk full (≥ 95% used)<br>- Slow network between cluster nodes and OSD hosts<br>- PG misconfiguration (poor bucket count for object count)<br>- Mon process resource pressure |
| **Safe corrective actions** | - Restart failing OSD if disk is healthy<br>- Free disk space or add new OSDs to reduce PG size<br>- Increase PG count for the pool (requires rebalancing)<br>- Optimize stripe width / pool type for the workload |
| **Post-recovery validation** | `ceph -s` shows all PGs active+clean; I/O latency p99 back below threshold; `ceph_pg_degraded` count = 0; sustained for 30m. |

---

## PVC Provisioning + Attachment Failures

| Step | Action |
|---|---|
| **Symptoms** | Pods pending; `volume is already exclusively attached to one node`; disk mount errors |
| **Dashboards+Alerts** | `kube_pod_status_pending{reason="VolumeBoundPending"} > 0`; `csi_driver_registration_status` decrease; `node_availablesystem_capacity_bytes` decrease |
| **Initial diagnostic commands** | `kubectl describe pvc <pvc> -n <namespace>`<br>`kubectl describe pod <pod> -n <namespace>`<br>`kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp` |
| **Isolate failing layer** | - Storage class provisioner not running<br>- No available nodes with matching topology<br>- Existing volume attachment conflict<br>- CSI driver not registered or healthy |
| **Root-cause investigation** | Check storage class `provisioner`, `reclaimPolicy`, `volumeBindingMode`. Verify node has the volume attached; check CSI driver logs (`kubectl logs -n kube-system <csi-plugin-pod>`). Check for volume expansion constraints. |
| **Safe corrective actions** | - Restart provisioner pod<br>- Expand PVC if `volumeBindingMode: Immediate` and expansion supported<br>- Fix node affinity/topo-requirements in storage class<br>- Rebind volume if stale attachment: `kubectl patch pv <pv> -p '{"spec":{"claimRef": null}}'` then recreate pod |
| **Post-recovery validation** | PVC `phase: Bound`; pod `Running`; I/O latency back to baseline; no new pending events in 10m. |

---

<a id="registry-image-push-failures"></a>
## Registry Image Pull / Push Failures

| Step | Action |
|---|---|
| **Symptoms** | Pods `ImagePullBackOff`; push rejected; CI pipeline timeout fetching image |
| **Dashboards+Alerts** | `harbor_image_pull_attempt_total` with `result=failed`; `harbor_image_push_failure_total` increase; registry TLS certificate expiry alert |
| **Initial diagnostic commands** | `kubectl describe pod <pod> -n <namespace>` (look at `Warning: Scheduled failed...`)<br>`docker pull <image>` manually from a node<br>`kubectl get secret <secret> -n <namespace> -o yaml` (for pull secrets) |
| **Isolate failing layer** | - Authentication failure (bad secret)<br>- Image not found in registry<br>- Registry rate-limited or down<br>- TLS certificate expired or misconfigured |
| **Root-cause investigation** | Check registry exporter metrics; verify secret contains correct `.dockercfg` or `.dockerconfigjson`; test `docker login <registry>` from a cluster node; check registry logs for authentication failures. |
| **Safe corrective actions** | - Regenerate and update image pull secret<br>- Push image to registry if push failure<br>- Renew TLS certificate if expired<br>- Increase registry rate limit or contact registry operator |
| **Post-recovery validation** | `kubectl pull <image>` succeeds; pod starts in `Running` state; push from CI succeeds; metrics show `result=success` for pulls/pushes. |

---

## Proxy Cache + Upstream Sync Failures

| Step | Action |
|---|---|
| **Symptoms** | Upstream responses 5xx; cache hit rate drops; stale content served; origin timeout errors |
| **Dashboards+Alerts** | `proxy_upstream_requests_total{status="5xx"} > 0`; `proxy_cache_status_miss_total` increase; `upstream_sync_duration_seconds` p99 spike |
| **Initial diagnostic commands** | `curl -v <cache-endpoint>` to check headers<br>`docker exec <proxy-pod> cache-tool metro show`<br>`curl -s <upstream-health-endpoint>` |
| **Isolate failing layer** | - Cache misconfigured (wrong TTL, wrong invalidation)<br>- Upstream service down or degraded<br>- Cache store full (disk capacity)<br>- Sync mechanism backlog (queued updates not applied) |
| **Root-cause investigation** | Check proxy logs for `cache_fill` vs `cache_hit` ratios; verify upstream health endpoints; check backend server capacity; review invalidation webhook logs. |
| **Safe corrective actions** | - Clear cache if stale content is the issue<br>- Scale cache backend or increase disk capacity<br>- Bring up upstream service; restart if stuck<br>- Reset sync queue if backlog accumulated; investigate why sync lagged |
| **Post-recovery validation** | Cache hit rate returns to normal; upstream 5xx rates back to baseline; sync duration p99 back below threshold; no new miss spikes. |

---

<a id="vault-sealed-unavailable"></a>
## Vault Sealed / Unavailable

| Step | Action |
|---|---|
| **Symptoms** | Applications fail to start; secrets rotation errors; `kubectl get secret` returns "not found" |
| **Dashboards+Alerts** | `vault_sealed == 1`; `vault_route_auth_login{failure="true"} > 0`; secret renewal failures |
| **Initial diagnostic commands** | `kubectl get pods -n vault -l app=vault`<br>`kubectl exec -it <vault-pod> -- vault status`<br>`kubectl logs -n vault <vault-agent-pod>` |
| **Isolate failing layer** | - Primary vault sealed (no active seal/unseal leader)<br>- Secondary/replica down<br>- Network partition between vault nodes<br>- Storage backend issue (etcd, PV) |
| **Root-cause investigation** | Check `vault status` output: `sealed`, `keyshares`, `keys_threshold`. Verify etcd/PV health for vault storage. Check vault node networking. For sealed vault, initiate unseal with existing keys or generate new ones. |
| **Safe corrective actions** | - If primary sealed and replica available, promote replica<br>- If all sealed, restore from backup if keys available; otherwise initiate emergency unseal<br>- Check and repair storage backend<br>- Restart vault pods if crash-looping |
| **Post-recovery validation** | `vault status` shows `sealed=0`; secrets operator can fetch secrets; application health checks pass; no new seal alerts in 15m. |

---

<a id="argocd-out-of-sync-reconciliation-failures"></a>
## Argo CD OutOfSync + Reconciliation Failures

| Step | Action |
|---|---|
| **Symptoms** | Argo CD UI shows `OutOfSync`; `kubectl apply` does not reconcile desired state; application stuck in `Progressing` |
| **Dashboards+Alerts** | `argocd_app_status_synced == 0`; `argocd_app_reconcile_failure_total` increase; `app_deviation` alert |
| **Initial diagnostic commands** | `argocd app get <app> --json`<br>`argocd app symptoms <app>`<br>`kubectl get events -n <ns> --sort-by=.metadata.creationTimestamp` |
| **Isolate failing layer** | - Source repo commit not reachable<br>- Helm chart error or template failure<br>- Resource quotas exceeded in target namespace<br>- Drift detected outside GitOps (manual changes) |
| **Root-cause investigation** | Check Argo CD app `source.status.hook` and `source.status.targetRevision`; examine `argocd app look <app>` for resource tree; check if a Helm `value` changed or a secret was rotated without updating the repo. |
| **Safe corrective actions** | - `argocd app sync <app>` to force sync<br>- `argocd app patch <app> --strategy merge` to adjust strategy<br>- Repo `git checkout` to last known good commit; `argocd app sync <app>`<br>- Remove manual drift if safe; otherwise document and accept<br>- Fix Helm values or chart; trigger re-sync |
| **Post-recovery validation** | Argo CD shows `Synced`; `argocd app get <app>` shows healthy resources; no `OutOfSync` for 10m; reconciliation rate back to normal. |

---

<a id="ingress-5xx-TLS-errors"></a>
## Ingress 5xx + TLS Errors

| Step | Action |
|---|---|
| **Symptoms** | Users see 5xx from ingress; TLS handshake failures in browser; mTLS errors in service mesh |
| **Dashboards+Alerts** | `nginx_ingress_controller_requests_total{status="5xx"} > 0`; `tls_handshake_failure_total` increase; `ingress_tls_certificate_expiry` near date |
| **Initial diagnostic commands** | `kubectl get ingress -A`<br>`kubectl logs -n kube-system <ingress-pod>`<br>`openssl s_client -connect <host>:443 -servername <host>` |
| **Isolate failing layer** | - TLS certificate expired or misconfigured<br>- Backend service returning 5xx<br>- Ingress controller misconfiguration (wrong rewrite, annotations)<br>- SNI mismatch or cipher suite mismatch |
| **Root-cause investigation** | Check ingress controller logs for TLS errors; verify certificate validity period; inspect backend service health (`kubectl get pods -l app=<backend>`); check Ingress API version and annotations. |
| **Safe corrective actions** | - Renew or replace expired TLS certificate via cert-manager<br>- Restart backend pods if unhealthy<br>- Fix ingress annotations or revert recent changes<br>- Update cipher suite or TLS version settings in ingress resource |
| **Post-recovery validation** | Browser can load `https://<host>` without errors; ingress 5xx rate back to 0; TLS handshake failures = 0; certificate expiry dashboard shows healthy margin. |

---

## Prometheus Missing Targets + Excessive Memory Use

| Step | Action |
|---|---|
| **Symptoms** | `prometheus_up == 0`; Prometheus OOM killed; TSDB compaction failures; slow UI |
| **Dashboards+Alerts** | `up{prometheus="true"} == 0` per job; `prometheus_tsdb_health_status != 3`; `process_resident_memory_bytes` > limit |
| **Initial diagnostic commands** | `curl http://localhost:9090/api/v1/targets`<br>`kubectl -n monitoring get pods -l k8s-app=prometheus`<br>`kubectl top pod -n monitoring -l k8s-app=prometheus` |
| **Isolate failing layer** | - ServiceMonitor selector mismatch → no targets<br>- Endpoint deprecated or removed<br>- Scrape config removed or syntax error<br>- Prometheus TSDB corrupted or OOM |
| **Root-cause investigation** | Check Prometheus status page (`/status`); examine `targets` page for `health: down`; check `prometheus.tsdb_objects`; review recent rule or scrape config changes. |
| **Safe corrective actions** | - Fix ServiceMonitor selector or add missing labels<br>- Restore scrape config from Git if recently changed<br>- Recycle Prometheus pod; if TSDB corrupted, recover from Thanos object storage<br>- Increase Prometheus storage size or memory limits if OOM |
| **Post-recovery validation** | All targets `health: up` in Prometheus UI; `prometheus_up == 1` for all jobs; TSDB health = 3; memory within limits; UI responsive. |

---

## Alertmanager Notification Failures

| Step | Action |
|---|---|
| **Symptoms** | No pager notifications; Slack channel silent on alert firings; email not delivered |
| **Dashboards+Alerts** | `alertmanager_notifications_failed_total > 0`; `alertmanager_alerts_dropped_total > 0`; receiver `smtp` or `slack` error logs |
| **Initial diagnostic commands** | `kubectl -n monitoring get pods -l app=alertmanager`<br>`kubectl -n monitoring logs sts/alertmanager-main`<br>`kubectl -n monitoring port-forward svc/alertmanager-main 9093:9093`<br>`curl http://localhost:9093/api/v1/status receivers` |
| **Isolate failing layer** | - SMTP auth change; TLS cert expired<br>- Slack webhook revoked or channel deleted<br>- Receiver configuration mismatch (labels don't match)<br>- Alertmanager itself down or partitioned |
| **Root-cause investigation** | Check Alertmanager config (`kubectl -n monitoring get configmap alertmanager-main -o yaml`); test webhook manually; verify SMTP credentials; check network connectivity to external services. |
| **Safe corrective actions** | - Update SMTP credentials or TLS cert<br>- Re-create Slack webhook if revoked<br>- Fix receiver label matchers to align with alert labels<br>- Restart Alertmanager if config change not picking up |
| **Post-recovery validation** | Fire a test alert (`kubectl -n monitoring exec ... -c prometheus -- wget -qO- 'http://localhost:9090/api/v1/alerts'`); verify notification delivered; `alertmanager_notifications_failed_total` back to 0; no dropped alerts in last 10m. |

---

## Loki Ingestion + Query Problems

| Step | Action |
|---|---|
| **Symptoms** | Cannot write logs via `kubectl logs` or Fluent Bit; queries return empty or error; log query latency spikes |
| **Dashboards+Alerts** | `loki_ingestion_errors_total > 0`; `loki_query_duration_seconds` p99 spike; `loki_rows_returned` 0 for expected queries |
| **Initial diagnostic commands** | `kubectl logs -n loki <loki-pod>`<br>`kubectl -n loki get pods`<br>`curl -s http://localhost:3100/ready`<br>`curl -s http://localhost:3100/api/promtail/version` |
| **Isolate failing layer** | - Promtail cannot reach Loki (network/PV)<br>- Loki compaction lagging → read path blocked<br>- Ingestion pipeline backlog (queue full)<br>- Config mismatch between Promtail and Loki (label sets) |
| **Root-cause investigation** | Check Loki `compaction` status; verify Promtail `client.max_payload_size` matches Loki `max_component_size`; check PV storage for Loki; review Promtail logs for `failed to push` errors. |
| **Safe corrective actions** | - Restart Loki server if compaction stuck<br>- Free disk space on Loki PV; increase PVC size<br>- Adjust Promtail `batch_size` or `chunk_encoding` if payload too large<br>- Reconcile label sets between Promtail and Loki |
| **Post-recovery validation** | Fluent Bit / Promtail successfully pushes logs; Loki query returns expected log entries within 2s; ingestion errors = 0; query latency p99 back below 2s. |

---

## Troubleshooting Summary

| Principle | Guideline |
|---|---|
| **Symptoms first** | Start from observed user-facing impact; never jump to root cause without data. |
| **Dashboards+alerts check** | Verify what already fires before picking up ad-hoc commands. |
| **Isolate layer** | Network → Storage → Compute → Application. Narrow the layer before digging. |
| **Safe actions first** | Prefer restart, scale, or config-revert over destructive operations. |
| **Post-recovery validation** | Always verify the fix and monitor for recurrence (15–30 min minimum). |
| **Document the gap** | If a gap is found in monitoring (missing alert, blind spot), file an observability ADR or ticket to close it. |