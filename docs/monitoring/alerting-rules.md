# Alerting Rules

## A. Purpose and scope

Document the Prometheus alerting rules and Alertmanager routing configuration. Alerts fire from Prometheus and are routed by Alertmanager to receivers (email, webhook, chat).

## B. Alert severity levels

| Severity | Meaning | Response time | Example |
|----------|---------|---------------|---------|
| Critical | Service outage or data loss risk | Immediate (15 min) | etcd down, API server unreachable |
| Warning | Degraded performance or capacity risk | Within 1 hour | Node CPU > 85%, disk > 80% |
| Info | Informational, no immediate action | Next business day | New version available, deprecated API |

## C. Alert rule categories

| Category | Rules covered | Example alert |
|----------|--------------|---------------|
| Cluster | API server, scheduler, controller-manager, etcd | `KubeAPIDown` |
| Node | kubelet, node_exporter, CPU, memory, disk | `NodeCPUUsageHigh` |
| Storage | Ceph, Rook-Ceph, ceph-csi, PVC | `CephOsdDown`, `PVCNotBound` |
| Platform | Rancher, Argo CD, Keycloak, GitLab, Harbor, Vault | `ArgoCDApplicationNotHealthy` |
| GPU | NVIDIA GPU utilization, driver, thermals | `NVIDIA GPUTemperatureHigh` |
| Ingress | NGINX ingress, MetalLB, external LB | `IngressBackendDown` |

## D. Alertmanager routing

Alerts are routed by Alertmanager based on severity, cluster, and service:

- Critical → PagerDuty, Slack #critical-alerts
- Warning → Slack #warnings-alerts
- Info → Slack #info-alerts

## E. Verification

```bash
# Verify Alertmanager is reachable
kubectl -n monitoring get svc alertmanager

# Verify alerting rules are loaded
kubectl -n monitoring get prometheusrules

# Check firing alerts
kubectl -n monitoring get prometheusrules -o yaml | grep -A5 state: firing
```

## E. Cross-references

- `monitoring/prometheus.md` — Prometheus and Alertmanager architecture
- `monitoring/grafana-dashboards.md` — Grafana dashboards
