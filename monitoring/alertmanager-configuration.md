# Alertmanager Configuration

## A. Purpose and scope

Document the Alertmanager configuration including receiver definitions, routing rules, inhibition rules, silence management, and notification templates. Alertmanager receives alerts from Prometheus and routes them to the appropriate receivers based on alert severity, alertname, and custom labels. All configuration is stored in Git and applied by Argo CD.

This document integrates with:

- `monitoring/prometheus.md` — Prometheus and Alertmanager architecture
- `monitoring/alerting-rules.md` — Cluster-wide alert severity definitions and routing
- `monitoring/prometheus-alert-rules.md` — Prometheus alerting rules, recording rules, and notification routing
- `monitoring/slo-sla.md` — SLOs and error budgets that alert severity maps to

---

## B. Alertmanager architecture

```text
Prometheus --> |Alerts| --> Alertmanager --> |Routes| --> Receivers
       |                      |
       |                      +--> Inhibition rules (suppress duplicates)
       +--> Silences (suppress temporarily)
```

---

## C. Receiver definitions

Receivers define where alerts are sent. Receiver names are referenced in routing rules.

### Email receiver

```yaml
receivers:
- name: 'email-admins'
  email_configs:
  - to: 'sre-admins@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.example.com:25'
    hello: 'alertmanager.example.com'
    subject: 'Alert: {{ .CommonLabels.alertname }} — {{ .Status }}'
    body: |
      {{ if .CommonAnnotations.summary }}
      Summary: {{ .CommonAnnotations.summary }}
      {{ end }}
      {{ if .CommonAnnotations.description }}
      Description: {{ .CommonAnnotations.description }}
      {{ end }}
      {{ if .Alerts }}
      Alerts:
      {{- range .Alerts }}
      - {{ .Labels.severity }}: {{ .Annotations.description }} ({{ .StartsAt }})
      {{- end }}
      {{ end }}
```

### Slack receivers (by severity)

```yaml
receivers:
- name: 'slack-critical'
  slack_configs:
  - channel: '#critical-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookCritical }}'
    send_resolved: true
    title: '{{ .CommonLabels.alertname }} — {{ .Status }}'
    text: |
      *Summary*: {{ .CommonAnnotations.summary }}
      *Description*: {{ .CommonAnnotations.description }}
      *Severity*: critical
      *Alertname*: {{ .CommonLabels.alertname }}
      *Cluster*: {{ .CommonLabels.cluster }}
      *Service*: {{ .CommonLabels.service }}

- name: 'slack-warning'
  slack_configs:
  - channel: '#warnings-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookWarning }}'
    send_resolved: true
    title: '{{ .CommonLabels.alertname }} — {{ .Status }}'
    text: |
      *Summary*: {{ .CommonAnnotations.summary }}
      *Description*: {{ .CommonAnnotations.description }}
      *Severity*: warning
      *Alertname*: {{ .CommonLabels.alertname }}
      *Cluster*: {{ .CommonLabels.cluster }}
      *Service*: {{ .CommonLabels.service }}

- name: 'slack-info'
  slack_configs:
  - channel: '#info-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookInfo }}'
    send_resolved: true
    title: '{{ .CommonLabels.alertname }} — {{ .Status }}'
    text: |
      *Summary*: {{ .CommonAnnotations.summary }}
      *Description*: {{ .CommonAnnotations.description }}
      *Severity*: info
      *Alertname*: {{ .CommonLabels.alertname }}
      *Cluster*: {{ .CommonLabels.cluster }}
      *Service*: {{ .CommonLabels.service }}
```

### PagerDuty receiver

```yaml
receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '{{ .Chart.Secrets.PagerDutyKey }}'
    description: '{{ .CommonAnnotations.summary }}'
    severity: critical
    client: 'alertmanager'
    client_url: 'https://example.com'
```

### Webhook receiver

```yaml
receivers:
- name: 'webhook-incident'
  webhook_configs:
  - url: 'https://internal.example.com/api/v1/alerts'
    send_resolved: true
    http_config:
      bearer_token: '{{ .Chart.Secrets.IncidentWebhookToken }}'
      tls_config:
        insecure_skip_verify: false
```

---

## D. Routing rules

Routing directs alerts to receivers based on label matching. Rules are evaluated top-down; the first matching rule wins.

```yaml
route:
  receiver: 'slack-info'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 24h

  # Route critical alerts to PagerDuty
  routes:
  - match:
      severity: 'critical'
    receiver: 'pagerduty-critical'
    continue: true

  # Route warning alerts to Slack warnings
  - match:
      severity: 'warning'
    receiver: 'slack-warning'

  # Route info alerts to Slack info
  - match:
      severity: 'info'
    receiver: 'slack-info'

  # Default fallback
  - match: {}
    receiver: 'slack-info'
```

**Routing logic:**

- `group_by`: How alerts are grouped into a single notification
- `group_wait`: Wait this long before sending the first notification for a group
- `group_interval`: How often to repeat notifications for the same group
- `repeat_interval`: How often to repeat the notification if the alert remains firing
- `receiver`: Default receiver if no match is found
- `routes`: Nested routes evaluated after the initial match; `continue: true` allows falling through to child routes

---

## E. Inhibition rules

Inhibition rules suppress redundant alerts. For example, a `ClusterDown` alert should suppress all lower-severity alerts from the same cluster.

```yaml
inhibit_rules:
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
    severity: 'warning'
    alertname: 'NodeCPUUsageHigh'
  target_match:
    severity: 'info'
    alertname: 'DiskUsageHigh'
  equal: ['cluster']
```

**Inhibition logic:**

- `source_match`: The alert that, when firing, triggers suppression
- `target_match`: The alerts that get suppressed
- `equal`: Labels that must match between source and target (alerts are only suppressed if all `equal` labels match)

---

## F. Silence management

Silences suppress alerts for a defined duration, useful during maintenance windows or known issues.

### Creating silences

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

### UI operations

- **New silence**: Define matchers, start/end time, and comment
- **Edit silence**: Modify duration or matchers of an existing silence
- **Delete silence**: Remove a silence to re-enable alerts

### Silencing via PrometheusRule (annotation)

Silences are managed externally through the Alertmanager UI or API. They are not defined in PrometheusRule objects, but alerts can be annotated to opt-out of silencing:

```yaml
metadata:
  annotations:
    alertmanager.openshift.io/skipSilence: "true"
```

---

## G. Notification templates

Alertmanager uses Go templates for notification formatting. Available data context:

| Variable | Description |
|---|---|
| `.CommonLabels` | All label key-value pairs from the alert |
| `.CommonAnnotations` | All annotation key-value pairs from the alert |
| `.Alerts` | List of alerts in the group |
| `.Status` | `"firing"` or `"resolved"` |
| `.GroupLabels` | Labels grouping the alerts |
| `.GroupKey` | Key for the alert group |
| `.CommonTimestamp` | Timestamp of the status change |
| `.ExternalURL` | URL base for links to Alertmanager |

### Example template snippet

```
Summary: {{ .CommonAnnotations.summary }}
Description: {{ .CommonAnnotations.description }}
Alert: {{ .CommonLabels.alertname }}
Severity: {{ .CommonLabels.severity }}
Cluster: {{ .CommonLabels.cluster }}
Starts at: {{ .CommonTimestamp }}
```

---

## H. Example alertmanager.yml

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: '{{ .Chart.Secrets.SlackWebhookCritical }}'
  pagerduty_url: '{{ .Chart.Secrets.PagerDutyKey }}'

route:
  receiver: 'slack-info'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 24h
  routes:
  - match:
      severity: 'critical'
    receiver: 'pagerduty-critical'
    continue: true
  - match:
      severity: 'warning'
    receiver: 'slack-warning'
  - match:
      severity: 'info'
    receiver: 'slack-info'

inhibit_rules:
- source_match:
    severity: 'critical'
    alertname: 'ClusterDown'
  target_match:
    severity: 'warning'
    alertname: 'NodeCPUUsageHigh'
  equal: ['cluster']

receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '{{ .Chart.Secrets.PagerDutyKey }}'
    severity: critical

- name: 'slack-warning'
  slack_configs:
  - channel: '#warnings-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookWarning }}'
    send_resolved: true

- name: 'slack-info'
  slack_configs:
  - channel: '#info-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookInfo }}'
    send_resolved: true

- name: 'email-admins'
  email_configs:
  - to: 'sre-admins@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.example.com:25'
    subject: 'Alert: {{ .CommonLabels.alertname }}'
    body: '{{ .CommonAnnotations.summary }}'
```

---

## I. Verification

```bash
# Verify Alertmanager configuration is valid
amtool validate config alertmanager.yml

# Verify Alertmanager is reachable
kubectl -n monitoring get svc alertmanager

# Verify alerting rules are loaded
kubectl -n monitoring get prometheusrules

# Check firing alerts
kubectl -n monitoring get prometheusrules -o yaml | grep -A5 state: firing

# Check routes and receivers
amtool route alerts --config=alertmanager.yml < alert.json

# Check inhibition
amtool inhibit alertmanager.yml < alert.json
```

---

## J. Best practices

**Mandatory:**

- All Alertmanager configuration lives in Git, applied by Argo CD. Never edit Alertmanager directly in the cluster.
- Validate configuration with `amtool validate config` in CI.
- Keep receiver names consistent across all configuration files.
- Use `continue: true` in routing only when intentional fan-out is needed.
- Document inhibition rules to prevent alert storms.

**Strongly recommended:**

- Use `send_resolved: true` for Slack receivers to get resolution notifications.
- Group alerts by `alertname`, `cluster`, and `service` to keep notifications focused.
- Set appropriate `repeat_interval` to avoid notification fatigue.
- Store receiver secrets (API keys, webhook URLs) in External Secrets or Vault, not in plain YAML.
- Run a canary Alertmanager in the Management Cluster for testing.
- Every alert must link to a runbook in `troubleshooting/`.

**Anti-patterns to avoid:**

- Overly specific matchers that make routing brittle — prefer label-based matching.
- `for: 0s` on Prometheus rules — always include a duration before firing.
- Too many inhibition rules — keep them focused on the most disruptive duplicates.
- Silences that are never cleaned up — set `endsAt` explicitly and review periodically.
- Notification templates without annotations — receivers will have no useful context.