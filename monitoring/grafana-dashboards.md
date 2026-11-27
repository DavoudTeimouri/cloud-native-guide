# Grafana Dashboards

## A. Purpose and scope

Document the Grafana dashboards used for cluster, node, storage (Ceph), platform services (Rancher), and GPU monitoring. Dashboards are JSON files stored in the `obs-monitoring` GitLab project and applied by Argo CD — they are versioned and reviewable, not baked into container images.

This file covers:

- **Dashboard JSON management** — storage, naming, validation
- **Data sources** — Prometheus and supported datasource configuration
- **Variable templates** — reusable templating for clusters, namespaces, and environments
- **Dashboard-as-code workflows** — edit → commit → Argo CD sync → verification
- **Operational views** — K8s, Ceph, and Rancher-specific dashboard categories

## B. Dashboard categories

| Dashboard | Scope | Datasource | Applied by |
|-----------|-------|------------|------------|
| Cluster overview | API server, scheduler, controller-manager, etcd | Prometheus | Argo CD |
| Node | kubelet, node_exporter, CPU, memory, disk, network | Prometheus | Argo CD |
| Storage | Ceph, Rook-Ceph, ceph-csi, PVC bindings | Prometheus | Argo CD |
| Platform services | Rancher, Argo CD, Keycloak, GitLab, Harbor, Vault | Prometheus | Argo CD |
| GPU | NVIDIA GPU utilization, MIG, driver, thermals | Prometheus | Argo CD |
| Ingress | NGINX ingress, MetalLB, external load balancer | Prometheus | Argo CD |

## C. Dashboard JSON management

### Storage and naming conventions

- Dashboard JSON files are stored in the `obs-monitoring` GitLab project under the `dashboards/` directory.
- Files follow the naming convention: `<dashboard-category>-<resource>.json` (e.g., `cluster-overview.json`, `ceph-osd-performance.json`).
- JSON files are vendored from the GitLab project and applied by Argo CD to the `monitoring` namespace.

### Syntax validation

```bash
# Validate a dashboard JSON file syntax
kubectl get secret -n monitoring grafana-dashboards -o jsonpath='{.data.dashboards}' | base64 --decode | python3 -m json.tool > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
```

### Example dashboard JSON structure

```json
{
  "dashboard": {
    "id": null,
    "uid": "example-uid",
    "title": "Example Dashboard",
    "timezone": "browser",
    "panels": [],
    "templating": {
      "list": []
    }
  },
  "folder": "Example",
  "overwrite": true
}
```

## D. Data source configuration

### Supported data sources

- **Prometheus** — primary datasource for K8s, Ceph, and platform metrics
- **Tempo** — for tracing (if enabled)
- **Loki** — for log querying (if enabled)

### Prometheus data source provisioning

```yaml
apiVersion: 1
kind: datasource
metadata:
  name: Prometheus
  uid: prometheus-main
type: prometheus
access: proxy
url: http://prometheus.monitoring.svc:9090
version: 1
```

### Verifying datasource configuration

```bash
# List all Grafana data sources
kubectl -n monitoring get grafanadatasource -o yaml

# Verify a specific datasource is reachable
curl -s http://prometheus.monitoring.svc:9090/api/v1/query?query=up | python3 -m json.tool
```

### Reload dashboards after datasource changes

```bash
argocd app sync mgmt-grafana
```

## E. Variable templates

### Cluster selection variable

```json
{
  "type": "query",
  "name": "cluster",
  "label": "Cluster",
  "datasource": "Prometheus",
  "query": "label_values(kubernetes_pod_info{cluster!=\"\"}, cluster)",
  "refresh": 5
}
```

### Namespace filtering variable

```json
{
  "type": "query",
  "name": "namespace",
  "label": "Namespace",
  "datasource": "Prometheus",
  "query": "label_values(kubernetes_namespace_info)",
  "refresh": 5,
  "multi": true
}
```

### Using variables in panel queries

```promql
rate(container_cpu_usage_seconds_total{cluster="$cluster",namespace="$namespace"}[1m])
rate(ceph_osd_io_bytes_total{cluster="$cluster"}[1m])
```

### Variable best practices

- Use `refresh` intervals appropriate for the dashboard's purpose (5s for real-time, 30s for overview).
- Set `multi: true` for variables that may match multiple values (namespaces, environments).
- Include a default value or "All" option in the variable's value mappings.
- Avoid hardcoding values — use Prometheus label queries for dynamic population.

## F. Dashboard-as-code workflows

### Lifecycle: edit → commit → Argo CD sync → verification

```bash
# 1. Edit a dashboard JSON file
vim monitoring/provisioning/dashboards/ceph-osd-performance.json

# 2. Commit and push the change
git add monitoring/provisioning/dashboards/ceph-osd-performance.json
git commit -m "Update Ceph OSD performance dashboard: add commit latency panel"
git push origin main

# 3. Wait for Argo CD to apply the change
kubectl -n argocd wait application mgmt-grafana --for=condition=Healthy --timeout=300s

# 4. Verify the dashboard is provisioned
kubectl -n monitoring get grafanadashboard ceph-osd-performance -o jsonpath='{.metadata.name}'

# 5. Run link and syntax validation
python3 scripts/check_links.py monitoring/grafana-dashboards.md
```

### Rolling back a dashboard change

```bash
# Revert to previous commit
git revert HEAD

# Or restore from Argo CD source
kubectl -n monitoring get grafanadashboard -o yaml | base64 --decode > previous-version.json
```

### Dashboard version tracking

```bash
# Tag a dashboard version after Argo CD sync
git tag -a "dashboards-v1.2.0" -m "Release ceph dashboards v1.2.0 after Argo CD sync"
git push origin "dashboards-v1.2.0"
```

### Argo CD Application manifest example

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: mgmt-grafana
  namespace: argocd
spec:
  source:
    repoURL: https://gitlab.example.com/obs-monitoring/obs-monitoring
    targetRevision: main
    path: dashboards
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## G. Operational views

### K8s operational views

| Dashboard | Key metrics |
|-----------|-------------|
| Cluster overview | API server latency, scheduler queue length, etcd operation duration, controller-manager health |
| Node | kubelet status, CPU/memory pressure, disk I/O, network throughput, pod status |
| Ingress | NGINX request rate, MetalLB allocation, external LB health checks, backend response time |

### Ceph operational views

| Dashboard | Key metrics |
|-----------|-------------|
| Cluster health | MON status, quorum, overall health (ceph_health_status), quorum status, MON/OSD uptime |
| OSD performance | OSD commit latency p99, I/O bytes/sec, ops/sec, queue depth, device health |
| PG status | PG health distribution (active+clean, degraded, incomplete, undersized, misplaced), PG peering progress |
| Capacity planning | Pool byte usage, OSD used %, cluster capacity forecast, pool target size vs actual size |

### Rancher operational views

| Dashboard | Key metrics |
|-----------|-------------|
| Rancher server | API server latency, authentication success/failure, cluster registration status, webhook response time |
| Workload scheduling | Pod pending reasons, resource reservation, node selector matches, taint status |
| Argo CD integration | Application sync status, health source status, repository health, cluster health |
| Keycloak | Authentication success rate, login latency, user session count, failed auth attempts |
| Harbor | Image push/pull latency, repository storage usage, scan status, registry health |
| Vault | Secret access rate, lease expiration, auth success/failure, performance latency |

## H. Verification

```bash
# Verify Grafana is reachable
kubectl -n monitoring get svc grafana

# Verify dashboards are provisioned
kubectl -n monitoring get grafanadashboard

# Verify datasource points to Prometheus
kubectl -n monitoring get grafanadatasource -o yaml

# Reload dashboards from Argo CD
argocd app sync mgmt-grafana
```

## I. Cross-references

- `monitoring/prometheus.md` — Prometheus and Alertmanager architecture
- `monitoring/alerting-rules.md` — Alerting rules and Alertmanager routing
- `monitoring/grafana-dashboard-provisioning.md` — Detailed dashboard provisioning configuration
- `monitoring/ceph-dashboards.md` — Ceph-specific dashboard configurations and panel details
- `storage/ceph/cephadm-deployment.md` — Ceph deployment and sizing reference
