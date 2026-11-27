# Monitoring Alert Validation and Troubleshooting

## A. Purpose and scope

Document monitoring alert validation procedures, including alert testing, silences, inhibition rules, troubleshooting firing alerts, and capacity visibility. All procedures integrate with the Prometheus + Alertmanager stack and follow the SRE reliability framework guidelines from the engineering SRE specialist.

---

## B. Alert testing

### B.1. Unit-testing rules with promtool

```bash
# Validate individual rules
promtool check rules /path/to/alert-rules.yml

# Validate recording rules
promtool check rules /path/to/recording-rules.yml --output json

# Validate full PrometheusRule CR
promtool check crds
```

### B.2. Integration-testing via CI

- CI pipeline runs `promtool check rules` on every PR merge to `monitoring/`.
- Fails the build if any rule has syntax errors, missing `for:` durations, or invalid Expr.

### B.3. Manual alert trigger

```bash
# Fire an alert manually for testing notification routing
kubectl -n monitoring exec deployment/alertmanager -- \
  amtool alert add \
    --alertname=TestAlert \
    --severity=warning \
    --annotation=summary="Manual test alert" \
    --annotation=description="Testing alert routing and silences"
```

### B.4. Verifying alert delivery

```bash
# Check that a test alert reached its receiver
kubectl -n monitoring logs deployment/alertmanager | grep -i "TestAlert"

# Verify webhook payload
curl -s http://localhost:9093/api/v2/alerts | jq '.[] | select(.alertname=="TestAlert")'
```

---

## C. Silences

### C.1. Creating silences

```bash
# UI: Alertmanager UI → Silences → New silence
# Define matchers, startsAt, endsAt, and a descriptive comment.

# API: Create a silence via curl
curl -X POST http://alertmanager:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "startsAt": "2026-01-01T00:00:00Z",
    "endsAt": "2026-01-01T02:00:00Z",
    "createdBy": "maintenance",
    "comment": "Node reboot for firmware update",
    "matchers": [
      {"name": "alertname", "value": "NodeCPUUsageHigh", "isRegex": false},
      {"name": "cluster", "value": "prod", "isRegex": false}
    ]
  }'

# API: Delete a silence
curl -X DELETE http://alertmanager:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {"name": "alertname", "value": "NodeCPUUsageHigh"},
      {"name": "cluster", "value": "prod"}
    ]
  }'
```

### C.2. Silence lifecycle

| Step | Action | Owner | Frequency |
|------|--------|-------|-----------|
| Create | Define matchers + `endsAt` | SRE on-call | As needed |
| Review | Check silences still relevant | SRE lead | Weekly |
| Cleanup | Delete expired silences | SRE on-call | After each maintenance window |

### C.3. Listing and inspecting silences

```bash
# List all active silences
kubectl -n monitoring exec deployment/alertmanager -- \
  amtool silence list

# Show silence details by ID
amtool silence info <silence-id>
```

---

## D. Inhibition rules

### D.1. Purpose

Inhibition rules suppress redundant alerts so a single root-cause alert (e.g., `ClusterDown`) suppresses lower-severity node/container alerts for the same cluster.

### D.2. Example inhibition rule set

```yaml
inhibit_rules:
  # ClusterDown suppresses NodeCPUUsageHigh, MemoryUsageHigh, DiskUsageHigh
  - source_match:
      severity: 'critical'
      alertname: 'ClusterDown'
    target_match:
      severity: 'warning'
      alertname: 'NodeCPUUsageHigh'
    equal: ['cluster']
  - source_match:
      severity: 'critical'
      alertname: 'ClusterDown'
    target_match:
      severity: 'warning'
      alertname: 'MemoryUsageHigh'
    equal: ['cluster']
  - source_match:
      severity: 'critical'
      alertname: 'ClusterDown'
    target_match:
      severity: 'warning'
      alertname: 'DiskUsageHigh'
    equal: ['cluster']

  # NodeCPUUsageHigh suppresses DiskUsageHigh at warning level (same cluster)
  - source_match:
      severity: 'warning'
      alertname: 'NodeCPUUsageHigh'
    target_match:
      severity: 'info'
      alertname: 'DiskUsageHigh'
    equal: ['cluster']
```

### D.2. Verifying inhibition rules

```bash
# Generate test alert data
echo '{"alerts": [{"labels": {"alertname": "ClusterDown", "severity": "critical", "cluster": "prod"}, "status": "firing"}]}' | \
  kubectl -n monitoring exec deployment/alertmanager -- \
    amtool inhibit -

# Expected: NodeCPUUsageHigh, MemoryUsageHigh, DiskUsageHigh from cluster=prod are suppressed
```

### D.3. Inhibition best practices

- Keep `equal` labels minimal: `cluster` + `alertname` when needed.
- Avoid chained inhibition (A → B → C) — it creates suppression ambiguity.
- Document each rule's intent in the rule comment and this file.
- Validate with `amtool inhibit` in CI.

---

## E. Troubleshooting firing alerts

### E.1. Initial diagnosis

```bash
# List firing Prometheus alerts
kubectl -n monitoring get prometheusrules -o json | \
  jq '.items[]?.status?.ruleStatus?.[]?.status == "firing"' | grep true

# Show all firing alerts with labels
kubectl -n monitoring get alerts --all-namespaces -o wide

# Check Alertmanager routing status
amtool alert list
```

### E.2. Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Alert not firing despite condition true | `for:` duration not met | Adjust `for:` in rule or check Prometheus scrape interval |
| Alert firing but no notification sent | Receiver misconfiguration | Verify routing rules; check receiver secrets |
| Multiple identical alerts firing | Missing inhibition rules | Add inhibition rule with correct `equal:` labels |
| Alert silenced unexpectedly | Active silence with matching matchers | List silences; update `endsAt` or remove silence |
| Alert routing to wrong receiver | Label mismatch in routing rule | Adjust `match:` labels; verify `group_by` |
| Alert firing every `repeat_interval` | `repeat_interval` set too low | Increase `repeat_interval`; add `wait` for first notification |

### E.3. Runbook references

- Each alert in `monitoring/prometheus-alert-rules.md` must link to a runbook in `troubleshooting/`.
- Runbooks follow the template: `troubleshooting/<alertname>.md`.
- If no runbook exists, create one before deploying the alert.

### E.4. Escalation path

1. **On-call SRE** (0-15 min): Check firing alerts, silences, and inhibition.
2. **SRE lead** (15-30 min): Review recent changes; correlate with deployment history.
3. **Platform team** (30+ min): Investigate Prometheus/Alertmanager infrastructure issues.

---

## F. Capacity visibility procedures

### F.1. Golden signals to monitor

| Pillar | Metric | Alert | SLO target |
|---|---|---|---|
| **Latency** | `histogram_quantile(0.99, rate(request_duration_seconds_bucket[5m]))` | p99 latency > 300ms | 99% under 300ms |
| **Traffic** | `rate(http_requests_total[5m])` | Traffic spike > 200% baseline | N/A (observability) |
| **Errors** | `rate(http_requests_total{status=~"5.."}[5m])` | Error rate > 1% | < 1% (error budget) |
| **Saturation** | `100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100)` | Memory > 85% | < 85% utilization |

### F.2. Capacity dashboards

- Grafana dashboards in `monitoring/grafana-dashboards.md` display real-time capacity.
- Dashboards are versioned in Git and applied by Argo CD.
- Key dashboards: `node-capacity`, `cluster-resources`, `ceph-pool-usage`.

### F.3. Capacity alert thresholds

```yaml
# Example: Node memory capacity alert
- alert: NodeMemoryCapacityHigh
  expr: 100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100) > 85
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Node memory usage high on {{ $labels.instance }}"
    description: "Memory usage at {{ $value }}% for 10m. Review workloads or scale up."
```

### F.4. Capacity planning workflow

1. **Collect**: Pull 30-day trends from Prometheus TSDB (`prometheus query` or Grafana).
2. **Forecast**: Project resource needs 30/60/90 days forward using linear regression.
3. **Validate**: Compare forecast against SLO error budget consumption.
4. **Act**: If forecasted utilization > 80% at 30d, file a capacity ticket; if > 90%, schedule immediate resize.
5. **Review**: Post-action review to confirm forecast accuracy and update assumptions.

### F.5. Capacity alert acknowledgment

```bash
# Acknowledge a capacity alert in Alertmanager
amtool alert acknowledge <alert-id> --comment "Investigating capacity issue"

# Declare alert resolved once issue is fixed
amtool alert resolve <alert-id> --comment "Capacity resolved after scaling"
```
