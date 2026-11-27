# Rancher and Cluster Management Monitoring

## Monitoring Spec Table

| Aspect | Details |
|---|---|
| **Health** | Rancher server availability and responsiveness; cluster health status; namespace and workload health; API authentication and authorization |
| **Metrics** | `ranchermgmt_deployment_status`, `rancher_api_request_duration_seconds_bucket`, `rancher_api_request_total{status!="200"}`, `cluster_condition_total{condition!="Healthy"}`, `workload_status_total{status!="Running"}`, `namespace_health_total`, `kubeapiserver_request_duration_seconds_bucket`, `auth_requests_total{result!="success"}`, `postgres_query_duration_seconds_bucket` (for embedded DB) |
| **Collection** | `rancher` agent endpoints (`/ping`, `/version`); Rancher API (`/api/rarancher.iostream.v1ClusterManagementService/health`) with auth; Prometheus scraping RanGER metrics endpoint; embedded PostgreSQL metrics; `kube-state-metrics` for cluster resources; `kubelet` node exporter metrics per cluster |
| **Dashboards** | Rancher server health and API latency; cluster condition distribution (Healthy/Unhealthy/NotReady); workload status across all clusters; namespace health heatmap; API request success/error rates; authentication failure trends; embedded PostgreSQL query latency; agent heartbeat frequency |
| **Alerts** | `RancherServerDown` (up{job="rancher"} == 0), `RancherAPIHighLatency` (rancher_api_request_duration_seconds_bucket{pct="99"} > 2 for 5m), `ClusterUnhealthy` (cluster_condition_total{condition!="Healthy"} > 0 for 10m), `WorkloadFailure` (workload_status_total{status!="Running"} > 0), `RancherAPIAuthFailure` (auth_requests_total{result="failure"} > 0), `EmbeddedDBSlowQueries` (postgres_query_duration_seconds_bucket{pct="99"} > 5 for 5m), `AgentHeartbeatLost` (heartbeat gap > 5m) |
| **SLI/SLO** | Server availability SLO: 99.9% over 30d (up{job="rancher"} == 1); API latency p99 SLO: < 3s over 30d (rancher_api_request_duration_seconds_bucket{pct="99"}); cluster health SLO: 95% clusters Healthy over 30d; workload success SLO: 98% workloads Running over 30d; API success SLO: 99% requests 2xx/3xx over 30d; auth success SLO: 99.9% auth attempts success over 30d; DB query SLO: p99 < 5s over 30d |
| **Tuning** | Rancher API request timeout and rate limiting; embedded PostgreSQL connection pool and query optimization; agent heartbeat interval and retry configuration; cluster health check frequency; authentication cache TTL; API batch size for list/watch operations |
| **Troubleshooting** | `curl -k https://<rancher-host>/ping`; `kubectl -n cattle-system get pods`; `kubectl -n cattle-system describe pod <pod>`; ` Rancher API /health` endpoint; `kubectl get clusters`; `kubectl describe cluster <cluster>`; `kubectl get nodes -A`; `kubectl get events -A --sort-by=.metadata.creationTimestamp`; `docker logs <rancher-pod>`; `kubectl get pg -n cattle-system` (for embedded PG) |
| **Recovery** | Restart Rancher deployment: `kubectl rollout restart deployment/rancher -n cattle-system`; check embedded PostgreSQL health and restart if needed; fix API auth by regenerating kubeconfig; scale Rancher resources (CPU/memory) if resource-starved; restore from backup if etcd data corrupted; redeploy agents if heartbeats lost; isolate and restart specific clusters if only some are affected |
| **Dependencies** | Rancher server pod running in cattle-system namespace; embedded PostgreSQL (or external DB) reachable; API auth secrets valid; Kubernetes clusters registered and reachable; Cattle agent running on each cluster; network connectivity between Rancher and managed clusters on ports 443/80 |

## Validation Commands (independent of Prometheus)

| Check | Command | Expected Output |
|---|---|---|
| Rancher server ping | `curl -k https://<rancher-host>/ping` | `pong` response within 2s; confirms server reachable |
| Rancher API health | `curl -k https://<rancher-host>/api/health` | `200` with `healthy: true`; API responsive |
| Cluster list | `kubectl get clusters -A` | All registered clusters listed; status shown |
| Cluster condition | `kubectl get cluster <cluster> -o jsonpath='{.status.conditions[?(@.type=="Healthy")].status}'` | `True` or `False`; indicates cluster health |
| Workload status | `kubectl get ws -A` (workloads) | List of workloads and their `Ready` status |
| Agent heartbeat | `kubectl get nodes -A` | Nodes listed and `Ready`; agent status visible |
| Embedded PG status | `kubectl -n cattle-system get pod -l app=postgres` | PG pod listed; `kubectl -n cattle-system logs <pg-pod>` for status |
| Rancher API auth test | `curl -k -H "Authorization: Bearer <token>" https://<rancher-host>/api/clusters` | `200` with clusters list; invalid token returns `401` |