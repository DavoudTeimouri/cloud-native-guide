# Grafana Dashboard Provisioning

## Purpose

Provision Grafana dashboards as code using JSON files, configuration files, and Argo CD. This approach replaces manual dashboard creation with reproducible, version-controlled workflows.

## Dashboard JSON Management

Dashboards are stored as JSON files in the repository and applied via Argo CD to the `mgmt-argocd` namespace. Each dashboard JSON file follows a naming convention that reflects its purpose and category.

### Example: Listing dashboard JSON files

```bash
# Find all Grafana dashboard JSON files in the monitoring directory
find ./monitoring -name "*.json" | sort

# Validate a dashboard JSON file syntax
kubectl get secret -n monitoring grafana-dashboards -o jsonpath='{.data.dashboards}' | base64 --decode | python3 -m json.tool > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
```

### Example: Dashboard JSON structure overview

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

## Dashboard Provisioning Files

Provisioning files declare which dashboards should be loaded into Grafana and how they are configured. These are processed by Grafana's dashboard provisioning API on startup.

### Example: Dashboard provisioning directory structure

```text
monitoring/provisioning/dashboards/
├── cluster-overview.json
├── node-metrics.json
├── storage.json
└── platform-services.json
```

### Example: Provisioning dashboard via Argo CD Application

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

## Data Source Configuration

Data sources must be configured before dashboards can render metrics. Provisioning supports Prometheus and other supported datasources.

### Example: Prometheus data source provisioning file

```yaml
apiVersion: 1
kind: datasource
metadata:
  name: Prometheus
  uid: prometheus-example
type: prometheus
access: proxy
url: http://prometheus.monitoring.svc:9090
version: 1
```

### Example: Verifying datasource configuration

```bash
# List all Grafana data sources
kubectl -n monitoring get grafanadatasource -o yaml

# Verify a specific datasource is reachable
curl -s http://prometheus.monitoring.svc:9090/api/v1/query?query=up | python3 -m json.tool
```

## Variable Templates

Dashboards use templating variables to make them reusable across clusters, namespaces, and environments. Variables are defined in the dashboard JSON or via provisioning ConfigMaps.

### Example: Dashboard variable for cluster selection

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

### Example: Variable for namespace filtering

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

### Example: Using variables in panel queries

Prometheus query with variable:

```
rate(container_cpu_usage_seconds_total{cluster="$cluster",namespace="$namespace"}[1m])
```

## Dashboard as Code Workflows

The dashboard as code lifecycle follows: edit JSON → commit → Argo CD sync → verification.

### Example: Workflow steps

```bash
# 1. Edit a dashboard JSON file
vim monitoring/provisioning/dashboards/node-metrics.json

# 2. Commit and push the change
git add monitoring/provisioning/dashboards/node-metrics.json
git commit -m "Update node metrics dashboard: add CPU panel"
git push origin main

# 3. Wait for Argo CD to apply the change
kubectl -n argocd wait application mgmt-grafana --for=condition=Healthy --timeout=300s

# 4. Verify the dashboard is provisioned
kubectl -n monitoring get grafanadashboard node-metrics -o jsonpath='{.metadata.name}'

# 5. Run link and syntax validation
python3 scripts/check_links.py monitoring/grafana-dashboard-provisioning.md
```

### Example: Rolling back a dashboard change

```bash
# Revert to previous commit
git revert HEAD

# Or restore from Argo CD source
kubectl -n monitoring get grafanadashboard -o yaml | base64 --decode > previous-version.json
```

### Example: Dashboard version tracking

```bash
# Tag a dashboard version after Argo CD sync
git tag -a "dashboards-v1.2.0" -m "Release node-metrics v1.2.0 after Argo CD sync"
git push origin "dashboards-v1.2.0"
```

## Related Monitoring Documentation

- `monitoring/prometheus.md` — Prometheus and Alertmanager architecture
- `monitoring/alerting-rules.md` — Alerting rules and Alertmanager routing
- `monitoring/ceph-dashboards.md` — Ceph-specific dashboard configurations
- `monitoring/slo-sla.md` — Service level objectives and error budgets
