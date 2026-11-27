# Argo CD + Ingress + cert-manager Monitoring

## Monitoring Spec Table

| Aspect | Details |
|---|---|
| **Health** | Argo CD application sync+health status; ingress controller availability and request latency; cert-manager certificate readiness and renewal; TLS handshake failures; backend errors and upstream timeouts |
| **Metrics** | `argocd_app_status_synced`, `argocd_app_reconcile_failure_total`, `argocd_app_deviation_total`, `nginx_ingress_controller_requests_total{status!="200"}`, `nginx_ingress_controller_requests_total`, `ingress_tls_handshake_failure_total`, `ingress_backend_error_total`, `upstream_request_timeout_total`, `certificate_ready_total`, `certificate_renewal_failure_total`, `certificate_expiry_days`, `tls_handshake_failure_total{cert!=""}` |
| **Collection** | Argo CD API (`/api/v1/applications` with status fields); Argo CD repo connectivity (`/api/v1/repositories` health); Ingress controller metrics endpoint (`/metrics` for NGINX, `/metrics` for Gateway Fabric); cert-manager webhook and controller metrics (`/metrics`); cert-manager `certificate_condition`; Ingress API status (`/status` for NGINX); upstream service health checks; TLS exporter metrics |
| **Dashboards** | Argo CD app sync health and deviation; reconciliation failure rate and trends; ingress request rate and latency (p99); 4xx/5xx error rates by backend; TLS handshake failure count and rate; certificate expiry timeline (days remaining); renewal success/failure rate; backend health up/down status; upstream timeout count |
| **Alerts** | `ArgoCDOutOfSync` (argocd_app_status_synced == 0 for 5m), `ArgoCDReconcileFailure` (argocd_app_reconcile_failure_total increase for 5m), `ArgoCDDeviation` (argocd_app_deviation_total > 0), `Ingress5xxSurge` (nginx_ingress_controller_requests_total{status="5xx"} increase for 5m), `TLSHandshakeFailure` (ingress_tls_handshake_failure_total increase for 5m), `BackendError` (ingress_backend_error_total increase for 5m), `UpstreamTimeout` (upstream_request_timeout_total increase for 5m), `CertExpiringSoon` (certificate_expiry_days < 7), `CertRenewalFailure` (certificate_renewal_failure_total > 0), `ArgCDRepoDisconnected` (argocd_repo_connectivity == "disconnected") |
| **SLI/SLO** | Argo CD sync health SLO: 99% of apps synced over 30d (argocd_app_status_synced == 1 ratio); reconciliation success SLO: < 1% failure rate over 30d (argocd_app_reconcile_success / argocd_app_reconcile_total); ingress request success SLO: 99.9% 2xx/3xx over 30d; ingress latency p99 SLO: < 500ms over 30d; TLS handshake success SLO: 100% over 30d (ingress_tls_handshake_failure_total == 0); backend error SLO: < 0.1% 5xx over 30d; certificate renewal SLO: 100% renewal success per cycle over 30d; repo connectivity SLO: 100% connected over 30d |
| **Tuning** | Argo CD app sync window and interval; reconciliation concurrency and resource limits; ingress controller worker processes and thread tuning; cert-manager CA duration and renewal interval; upstream service health check interval and timeout; cache TTL for repo connectivity and certificate status |
| **Troubleshooting** | `argocd app get <app> --json`; `argcd app symptoms <app>`; `kubectl -n argocd get pods`; `kubectl -n argocd logs <argocd-server-pod>`; `argocd repo sync <repo>`; `kubectl get ingress -A`; `kubectl describe ingress <ingress> -n <namespace>`; `openssl s_client -connect <host>:443 -servername <host>`; `kubectl get pods -l app=<backend>`; `cert-manager certificates describe <cert>`; `kubectl logs -n cert-manager <cert-manager-controller-pod>` |
| **Recovery** | `argocd app sync <app>` to force sync; `argocd app patch <app> --strategy merge` to adjust strategy; repo `git checkout` to last good commit; `argocd app sync <app>`; renew or replace expired certificates via cert-manager (`cert-manager cert renew <cert>`); restart ingress controller (`kubectl rollout restart deployment/<ingress> -n <namespace>`); fix backend health by restarting pods or scaling; clear deviated resources and re-sync; restore Argo CD repo from backup if corrupted |
| **Dependencies** | Argo CD server running in `argocd` namespace; API reachable on port 443 or 80; cert-manager controller and webhook running in `cert-manager` namespace; ingress controller running in its namespace; Kubernetes API reachable for all operations; container registry reachable for image updates; upstream services healthy and reachable from ingress |

## Validation Commands (independent of Prometheus)

| Check | Command | Expected Output |
|---|---|---|
| Argo CD app sync | `argocd app get <app> --name <namespace>` | `Synced` or `OutOfSync` status; `argocd_app_status_synced` value |
| Argo CD repo health | `argocd repo get <repo> --name <namespace>` | `Connected` or `Disconnected`; `argocd_repo_connectivity` value |
| Ingress TLS test | `openssl s_client -connect <host>:443 -servername <host>` | `Verify return code: 0` (success); handshake fails if cert expired |
| Ingress health check | `curl -k https://<host>/` | `200` response; TLS handshake successful |
| cert-manager certificate | `kubectl describe certificate <cert> -n cert-manager` | `Ready` condition: `True`; `expiry` date shown |
| cert-manager renewal test | `kubectl cert-manager renew <cert> -n cert-manager` | `Certificate renewed` or `renewal failed`; `certificate_renewal_failure_total` increments |
| Argo CD repo connectivity | `argocd repo login <repo>` | `Logged in successfully`; repo accessible |
| Ingress backend health | `kubectl get pods -l app=<backend> -n <namespace>` | `Ready` status; backend healthy if Ready == `True` |
| Upstream timeout test | `curl -w "%{time_total}" -o /dev/null -s https://<host>/large-payload` | Response time; `upstream_request_timeout_total` increments if > timeout |
