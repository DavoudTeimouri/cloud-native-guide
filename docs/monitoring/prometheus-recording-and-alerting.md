# Prometheus Recording and Alerting Rules

## A. Purpose and scope

Document the Prometheus recording rules and alerting rules used across the Kubernetes and Ceph clusters. Recording rules pre-compute expensive queries for use in dashboards and other rules. Alerting rules fire when an expressed condition is true for a sustained duration. All rules are stored as `PrometheusRule` custom resources in Git and applied by Argo CD.

---

## B. Rule syntax

### Prometheus rule types

| Rule type | File extension | Purpose |
|---|---|---|
| `AlertingRule` | `.yml` / `.yaml` | Fires when an expressed condition is true for a sustained duration |
| `RecordingRule` | `.yml` / `.yaml` | Pre-computes expensive queries for use in dashboards and other rules |

### Alerting rule structure

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: example-rules
  namespace: monitoring
spec:
  groups:
  - name: example-group
    interval: 30s
    rules:
    - alert: ExampleAlert
      expr: node_cpu_seconds_total{mode!="system"} > 300
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High CPU usage on {{ $labels.instance }}"
        description: "CPU usage has been above 300 seconds for 5 minutes. Value: {{ $value }}s Instance: {{ $labels.instance }}"
```

### Key fields

| Field | Description |
|---|---|
| `expr` | PromQL expression that evaluates to boolean |
| `for` | Duration the expression must be true before firing |
| `labels` | Static labels added to the alert (e.g., `severity`) |
| `annotations` | Human-readable text rendered in notifications |
| `interval` | How often the rule is evaluated (default 1m) |

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

Recording rules pre-compute queries that are expensive or used repeatedly, reducing dashboard query latency and ensuring consistent metrics across visualizations.

---

## C. Alert severity levels

| Severity | Code | Response time | Typical use |
|---|---|---|---|
| `critical` | `critical` | Immediate (15 min) | Service outage, data loss risk, PagerDuty |
| `warning` | `warning` | Within 1 hour | Degraded performance, capacity risk |
| `info` | `info` | Next business day | Informational, no immediate action needed |
| `none` | `none` | Suppressed | Used for testing or suppressed alerts |

Severity is set via the `labels.severity` field in the rule and is the primary factor in Alertmanager routing.

---

## D. Notification routing

Alertmanager routes alerts based on labels, particularly `severity`, `alertname`, and custom labels such as `cluster` and `service`.

### Routing tree example

```yaml
groups:
- name: 'example'
  interval: 1m
  rules:
  - receiver: 'pagerduty-critical'
    match:
      severity: 'critical'
    continue: true
  - receiver: 'slack-warning'
    match:
      severity: 'warning'
  - receiver: 'slack-info'
    match:
      severity: 'info'
receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '{{ .Chart.Secrets.PagerDutyKey }}'
- name: 'slack-warning'
  slack_configs:
  - channel: '#warnings-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookWarning }}'
- name: 'slack-info'
  slack_configs:
  - channel: '#info-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookInfo }}'
```

### Inhibition rules

Inhibition rules suppress redundant alerts. For example, a `ClusterDown` alert inhibits all lower-severity alerts from the same cluster:

```yaml
- source_match:
    severity: 'warning'
    alertname: 'NodeCPUUsageHigh'
  target_match:
    severity: 'critical'
    alertname: 'ClusterDown'
  equal: ['cluster']
```

---

## E. Alert silencing

Silences suppress alerts for a defined duration, useful during maintenance windows or known issues.

### Creating a silence

```bash
# UI: Alertmanager UI → Silences → New silence
# API:
curl -X POST http://alertmanager:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "startsAt": "2026-01-01T00:00:00Z",
    "endsAt": "2026-01-01T02:00:00Z",
    "createdBy": "maintenance",
    "comment": "Node reboot for firmware update",
    "matchers": [
      { "name": "alertname", "value": "NodeCPUUsageHigh", "isRegex": false },
      { "name": "cluster", "value": "prod", "isRegex": false }
    ]
  }'
```

Silences are managed externally through the Alertmanager UI or API; they are not defined in PrometheusRule objects.

---

## F. Common alert patterns for Kubernetes

### Availability alerts

| Alert name | PromQL expression | Condition |
|---|---|---|
| `KubeAPIDown` | `up{job="kubernetes-apiserver"} == 0` | API server not reachable |
| `KubeStateMetricsNoData` | `count by (job) (kube_deployment_status_replicas{job="kube-state-metrics"}) == 0` | No metrics received for 10m |
| `NodeNotReady` | `kube_node_status_condition{condition="Ready", status="true"} == 0` | Node not ready |

### Node alerts

| Alert name | PromQL expression | Condition |
|---|---|---|
| `NodeCPUUsageHigh` | `100 - (rate(node_cpu_seconds_total{mode="idle"}[1m]) * 100) > 85` | CPU usage > 85% for 10m |
| `NodeMemoryUsageHigh` | `100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100) > 85` | Memory usage > 85% |
| `NodeDiskPressure` | `node_filesystem_avail_bytes{mountpoint="/"} < 20% * node_filesystem_size_bytes{mountpoint="/"}` | Disk < 20% available |

### Pod/Container alerts

| Alert name | PromQL expression | Condition |
|---|---|---|
| `PodRestarted` | `increase(kube_pod_container_status_restarts_total[5m]) > 3` | Pod restarted > 3 times in 5m |
| `ContainerCrashLoop` | `kube_pod_container_status_phase{phase="CrashLoopBackoff"} == 1` | Container in crash loop |
| `PodDown` | `up{pod!=""} == 0` for 5m | Pod not running |

### Network alerts

| Alert name | PromQL expression | Condition |
|---|---|---|
| `IngressBackendDown` | `count by (ingress) (nginx_ingress_up{backend!=""} == 0)` | Ingress backend unreachable |
| `MetalLBPoolUnavailable` | `lb_set{pool!=""} == 0` | MetalLB pool has no available members |

---

## G. Common alert patterns for Ceph

### Ceph cluster health

| Alert name | PromQL expression | Condition |
|---|---|---|
| `CephHealthError` | `ceph_health_status == 1` | Ceph reports non-healthy status |
| `CephOSDDown` | `ceph_osd_up == 0` | One or more OSDs down |
| `CephPGDegraded` | `ceph_pg_degraded > 0` | PGs in degraded state |
| `CephPGRecoveryStuck` | `ceph_pg_recovery_acting > 0 and ceph_pg_recovery_queue > 1000` | Recovery queue stuck |

### Ceph OSD alerts

| Alert name | PromQL expression | Condition |
|---|---|---|
| `CephOSDFull` | `ceph_osd_full > 0` | OSD(s) at or near capacity |
| `CephOSDNearFull` | `ceph_osd_nearfull > 0` | OSD(s) near full threshold |
| `CephOSDHeartbeatLost` | `increase(ceph_osd_heartbeat_lost[5m]) > 0` | OSD heartbeat lost |

### Ceph pool alerts

| Alert name | PromQL expression | Condition |
|---|---|---|
| `CephPoolNearFull` | `ceph_pool_bytes_used / ceph_pool_bytes_total > 0.85` | Pool > 85% used |
| `CephPoolFull` | `ceph_pool_bytes_used / ceph_pool_bytes_total >= 1.0` | Pool 100% used |

### Ceph mon/manager alerts

| Alert name | PromQL expression | Condition |
|---|---|---|
| `CephMonDown` | `ceph_mon_up == 0` | Monitor daemon down |
| `CephMgrDown` | `ceph_mgr_up == 0` | Manager daemon down |

---

## H. Best practices

**Mandatory:**

- All rules and dashboards live in Git, applied by Argo CD. Never `kubectl apply` a rule by hand.
- Validate rules in CI with `promtool check rules`.
- Inhibit duplicates at the cluster level — a single `ClusterDown` alert should suppress all node-level alerts for that cluster.
- Prometheus storage on a real PVC with a size limit, not emptyDir.
- Scrape credentials and receiver secrets come from Vault via External Secrets, not from a values file.

**Strongly recommended:**

- Keep the scrape label set small; `pod`, `namespace`, `container`, `job` are enough. Adding `pod_uid` or request IDs destroys performance.
- Record rules for expensive queries so dashboards do not recompute them.
- Run a canary Prometheus in the Management Cluster scraping both clusters as a second line of visibility.
- Alert on "no data" separately from "bad data" — a Prometheus that cannot scrape produces silence, not an alert.
- Every alert must link to a runbook in `troubleshooting/`.

**Anti-patterns to avoid:**

- Overly specific PromQL that matches only a single pod by `pod_uid` — makes silencing and scaling difficult.
- `for: 0s` on alerts — fires instantly on any single scrape failure; always include a `for` duration.
- Recording rules with high cardinality group-by labels — can blow up the TSDB.
- Alerts without annotations — notifications will have no useful context.

---

## I. Cross-references

- `monitoring/prometheus.md` — Prometheus and Alertmanager architecture, installation, and validation
- `monitoring/prometheus-alert-rules.md` — Cluster-wide alert severity definitions and Alertmanager routing configuration (existing detailed alert list)
- `monitoring/alerting-rules.md` — Alert severity definitions and routing configuration
- `monitoring/slo-sla.md` — SLOs and error budgets that alert severity maps to
- `troubleshooting/` — Runbooks for individual alerts
- `monitoring/recording-rules.md` — (future) dedicated recording rules reference