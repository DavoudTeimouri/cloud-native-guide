# Prometheus Recording Rules

## A. Purpose and scope

Document the Prometheus recording rules used across the Kubernetes, Ceph, and Rancher clusters. Recording rules pre-compute expensive PromQL queries for use in dashboards, alerts, and other queries. All rules are stored as `PrometheusRule` custom resources in Git and applied by Argo CD.

This file is dedicated to recording rules; see `monitoring/prometheus-alert-rules.md` for alerting rules and `monitoring/prometheus-architecture.md` for the overall Prometheus deployment architecture.

---

## B. Rule syntax

### Prometheus rule types

| Rule type | File extension | Purpose |
|---|---|---|
| `AlertingRule` | `.yml` / `.yaml` | Fires when an expressed condition is true for a sustained duration |
| `RecordingRule` | `.yml` / `.yaml` | Pre-computes expensive queries for use in dashboards and other rules |

### Recording rule structure

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: recording-rules
  namespace: monitoring
spec:
  groups:
  - name: recording-group
    interval: 1m
    rules:
    - record: job:node_cpu_seconds:sumrate
      expr: rate(node_cpu_seconds_total{mode!="system"}[1m])
```

**Key fields:**

| Field | Description |
|---|---|
| `expr` | PromQL expression to pre-compute |
| `record` | Name of the new vector time-series to record |
| `interval` | How often the rule is evaluated (default 1m) |

Recording rules pre-compute queries that are expensive or used repeatedly, reducing dashboard query latency and ensuring consistent metrics across visualizations.

---

## C. Rule definitions

### Kubernetes metrics

| Record name | PromQL expression | Description |
|---|---|---|
| `kube:node:cpu:sumrate` | `rate(node_cpu_seconds_total{mode!="system"}[1m])` | Node CPU usage in seconds per second (summed across all nodes) |
| `kube:node:memory:available` | `node_memory_MemAvailable_bytes` | Available memory bytes per node |
| `kube:pod:restart:count` | `increase(kube_pod_container_status_restarts_total[5m])` | Pod container restarts in last 5 minutes |
| `kube:namespace:count` | `count by (namespace) (kube_namespace_status_phase)` | Number of namespaces in each phase |
| `kube:ingress:up` | `count by (ingress) (nginx_ingress_up)` | Ingress availability status |
| `kube:persistentvolume:bound` | `count by (pv) (kube_persistentvolume_status{phase="Bound"})` | Bound persistent volumes |

### Ceph metrics

| Record name | PromQL expression | Description |
|---|---|---|
| `ceph:osd:up` | `ceph_osd_up` | Whether OSDs are up (1 = up, 0 = down) |
| `ceph:pg:degraded` | `ceph_pg_degraded` | Number of PGs in degraded state |
| `ceph:pool:bytes:used:ratio` | `ceph_pool_bytes_used / ceph_pool_bytes_total` | Pool usage ratio (0-1) |
| `ceph:health:status` | `ceph_health_status` | Ceph cluster health status (0 = healthy, 1 = error) |
| `ceph:osd:heartbeat:lost` | `increase(ceph_osd_heartbeat_lost[5m])` | Lost OSD heartbeats in last 5 minutes |
| `ceph:mon:up` | `ceph_mon_up` | Whether Ceph monitors are up |

### Rancher metrics

| Record name | PromQL expression | Description |
|---|---|---|
| `rancher:cluster:count` | `count by (cluster) (rancher_cluster_active)` | Number of active Rancher clusters |
| `rancher:service:cpu:sumrate` | `rate(rancher_service_cpu_seconds_total[1m])` | Rancher service CPU usage |
| `rancher:workload:phase` | `rancher_workload_phase{workload!=""}` | Workload phase status (running, stopped, etc.) |
| `rancher:endpoint:health` | `count by (endpoint) (rancher_endpoint_health)` | Rancher endpoint health status |

---

## D. Aggregation strategies

### Common aggregation patterns

| Pattern | PromQL example | Use case |
|---|---|---|
| **Rate per second** | `rate(node_cpu_seconds_total[1m])` | CPU utilization trends |
| **Increase over interval** | `increase(node_cpu_seconds_total[5m])` | Total CPU seconds elapsed |
| **Sum across labels** | `sum by (cluster) (node_cpu_seconds_total)` | Cluster-level totals |
| **Count distinct** | `count by (namespace) (kube_pod)` | Number of pods per namespace |
| **Histogram quantiles** | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` | Latency p95 |
| **In-rate** | `irange(node_cpu_seconds_total[1m])` | Instant rate over 1m |

### Grouping strategies

- **By cluster**: `sum by (cluster) (...)` — aggregate across all clusters in a fleet
- **By namespace**: `sum by (namespace) (...)` — isolate per-namespace metrics
- **By service**: `sum by (service) (...)` — service-level aggregation
- **Without cardinality**: Remove high-cardinality labels (`pod_uid`, `container_id`) from recording rules to avoid TSDB bloat

---

## E. Recording rule templates

### Template: Kubernetes node overview

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-node-recording-rules
  namespace: monitoring
spec:
  groups:
  - name: kubernetes-node
    interval: 1m
    rules:
    - record: kube:node:cpu:sumrate
      expr: rate(node_cpu_seconds_total{mode!="system"}[1m])
    - record: kube:node:memory:available
      expr: node_memory_MemAvailable_bytes
    - record: kube:node:disk:available
      expr: node_filesystem_avail_bytes{mountpoint="/"}
```

### Template: Ceph cluster health

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ceph-recording-rules
  namespace: monitoring
spec:
  groups:
  - name: ceph
    interval: 1m
    rules:
    - record: ceph:osd:up
      expr: ceph_osd_up
    - record: ceph:pg:degraded
      expr: ceph_pg_degraded
    - record: ceph:pool:bytes:used:ratio
      expr: ceph_pool_bytes_used / ceph_pool_bytes_total
    - record: ceph:health:status
      expr: ceph_health_status
```

### Template: Rancher cluster overview

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: rancher-recording-rules
  namespace: monitoring
spec:
  groups:
  - name: rancher
    interval: 1m
    rules:
    - record: rancher:cluster:count
      expr: count by (cluster) (rancher_cluster_active)
    - record: rancher:service:cpu:sumrate
      expr: rate(rancher_service_cpu_seconds_total[1m])
    - record: rancher:workload:phase
      expr: rancher_workload_phase{workload!=""}
```

---

## F. Maintenance procedures

### Validation

- Run `promtool check rules <rule-file>.yaml` against every PrometheusRule to catch syntax errors and cardinality issues.
- Verify recorded series appear in Prometheus with `vector( recording_rule_name )` queries.
- Check TSDB growth after deploying new recording rules; high cardinality will increase storage costs.

### Review cycle

| Activity | Frequency | Owner |
|---|---|---|
| Review rule expressions for deprecated PromQL | Quarterly | SRE team |
| Re-run `promtool check rules` after any change | On every PR | PR author |
| Prune recording rules unused for > 90 days | Semi-annual | Platform team |
| Update documentation when rules change | On every change | SRE team |

### Deployment flow

1. Add or edit `.yaml` files in `monitoring/` directory
2. Open a PR against the cloud-native-guide repo
3. Ensure CI passes `promtool check rules` validation
4. Argo CD automatically applies merged changes to the cluster
5. Verify recorded series in Prometheus UI after deployment
6. Update this documentation if rule names or expressions change

### Rollback procedure

1. If a new recording rule causes TSDB bloat or errors, revert the PrometheusRule change in Git.
2. Argo CD will sync back to the previous state within the sync interval.
3. Monitor `prometheus_tsdb_errors_total` for any spike indicating a bad rule.
4. File a follow-up task to rewrite the rule with corrected cardinality.

---

## G. Cross-references

- `monitoring/prometheus.md` — Prometheus and Alertmanager architecture, installation, and validation
- `monitoring/prometheus-alert-rules.md` — Cluster-wide alert severity definitions and Alertmanager routing configuration
- `monitoring/alerting-rules.md` — Alert severity definitions and routing configuration
- `monitoring/slo-sla.md` — SLOs and error budgets that alert severity maps to
- `monitoring/grafana-dashboards.md` — Dashboards that use recorded series
- `troubleshooting/` — Runbooks for individual recording rules
- `monitoring/prometheus-recording-and-alerting.md` — High-level overview (this file is the dedicated recording rules reference)
