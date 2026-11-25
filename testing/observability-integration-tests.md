# Section 10: Observability and Alerting Integration

## Overview
This section defines the integration tests for the observability stack — metrics, logs, traces, and alerting. The core principle: **dashboard availability ≠ monitoring functional**. Each test verifies that data flows end-to-end and that alerts are actionable and correctly routed.

## 10.1 Prometheus Target Discovery
- **Objective**: Verify that Prometheus can discover and scrape all intended targets in the cluster.
- **Scope**: All exporter endpoints, sidecar metrics, user-defined ServiceMonitors.
- **Preconditions**: Prometheus operator deployed; targets configured via ServiceMonitor or `prometheus.io` annotations.
- **Test Method**: Query `prometheus_targets_status{job="..."}`; verify `health="up"` for all expected targets; check for unexpected targets.
- **Expected Result**: All intended targets reported `up`; no missing targets; scrape interval respected.
- **Evidence**: Prometheus UI or `curl` against Prometheus API (`/api/v1/targets`).
- **Automation Potential**: High — scripted via Prometheus API in CI.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: Medium — missing targets mean missing data; alerting and SLO tracking may be blind.

## 10.2 Exporter Availability
- **Objective**: Confirm that all promised exporters (node, kube-state, cadvisor, application-specific) are running and responding.
- **Scope**: Node exporters, kube-state-metrics, cAdvisor, application exporters (e.g., PostgreSQL, Redis).
- **Preconditions**: Exporter Deployments/RSets running in `monitoring` namespace.
- **Test Method**: `curl` or `wget` against exporter endpoints; verify `/metrics` path returns valid metrics; check `kube-state-metric` helper metrics.
- **Expected Result**: Endpoints return 200; metrics output parsable; no TLS errors (certs valid/placeholder).
- **Evidence**: Endpoint response body, TLS certificate validity (placeholder: all certs illustrative).
- **Automation Potential**: High — health checks in Prometheus or independent script.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: Medium — exporter down = metrics gap.

## 10.3 Metric Ingestion
- **Objective**: Verify that metrics written to Prometheus are retained, queryable, and match the expected cardinality and type.
- **Scope**: Custom application metrics, platform metrics (CPU, memory, network).
- **Preconditions**: Application sending metrics; Prometheus receiving.
- **Test Method**: Send a known metric via `prometheuspushgateway` or direct scrape; query with Prometheus `query` API; verify label set and value.
- **Expected Result**: Metric appears in query results with correct labels and value; retention period honored.
- **Evidence**: Prometheus query result, retention metric (`prometheus_tsdb_head_series`).
- **Automation Potential**: High — automated via CI script that pushes a known metric.
- **Responsible Operator**: SRE / developer.
- **Failure Severity**: Low — metric loss affects SLO accuracy but not immediate runtime.

## 10.4 Recording Rules
- **Objective**: Verify that Prometheus recording rules are syntactically valid, evaluate without error, and produce the expected metric output.
- **Scope**: All `.rules` files in the Prometheus rule bundles.
- **Preconditions**: Prometheus rule files present; Prometheus server running with rules loaded.
- **Test Method**: `promtool check rules <rule-file>`; evaluate recording rules via API; compare output metric format to documentation.
- **Expected Result**: `promtool` reports no errors; recorded metrics are queryable and return numeric values.
- **Evidence**: `promtool` output, API evaluation results.
- **Automation Potential**: High — `promtool` integrates into CI.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: Low — broken rules cause missing derived metrics; detectable in CI.

## 10.5 Alert Rule Evaluation
- **Objective**: Verify that alert rules evaluate correctly for both firing and cleared states; no false positives from rule misconfiguration.
- **Scope**: All alert rule files (Alertmanager-compatible).
- **Preconditions**: Prometheus + Alertmanager running; rule files on disk.
- **Test Method**: `promtool check rules`; evaluate rules against test fixtures; fire alerts manually via API; verify Alertmanager receives them.
- **Expected Result**: Rules evaluate only on genuine conditions; `alertname` and labels match documentation; cleared state transitions correctly.
- **Evidence**: `promtool` output, Alertmanager UI alert list, API evaluation results.
- **Automation Potential**: High — `promtool` and alert test frameworks automate this.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: High — alert misconfiguration leads to alert fatigue or missed incidents.

## 10.6 Alertmanager Routing
- **Objective**: Verify that Alertmanager routes alerts to the correct receivers based on severity, labels, and inhibition rules.
- **Scope**: Routing tree, receiver configurations, inhibition rules.
- **Preconditions**: Alertmanager deployed; receivers configured (email, Slack, PagerDuty).
- **Test Method**: Fire alerts with specific labels; observe routing path in Alertmanager UI; verify inhibited alerts are suppressed.
- **Expected Result**: Alerts routed to correct receiver; severity-based grouping; inhibition works as documented.
- **Evidence**: Alertmanager UI routing graph, receiver notification logs.
- **Automation Potential**: Medium — can be scripted with `amtool` and alert firing.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: High — misrouted alerts mean delayed response or alert fatigue.

## 10.7 Notification Delivery
- **Objective**: Verify that notifications sent by Alertmanager are received by the intended recipients and contain actionable information.
- **Scope**: Email, Slack, PagerDuty, webhook endpoints.
- **Preconditions**: Receiver credentials configured (placeholders); test notifications allowed.
- **Test Method**: Send a test alert via Alertmanager; verify receipt in each channel; verify message contains `alertname`, `severity`, `generatorURL`, and links.
- **Expected Result**: Notifications received; subject/body contain required fields; links resolve to alert state.
- **Evidence**: Notification receipt (email inbox, Slack message, webhook payload log).
- **Automation Potential**: Medium — test alerts can be automated; manual verification of human channels.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: Medium — missed notifications delay incident response.

## 10.8 Grafana Dashboard Data
- **Objective**: Verify that Grafana dashboards display data from the expected Prometheus and Loki sources; panels do not error due to missing metrics or logs.
- **Scope**: All dashboards referenced in the platform documentation.
- **Preconditions**: Grafana configured with Prometheus and Loki data sources.
- **Test Method**: Load each dashboard; verify panels render; query unscaled time range; verify metric names match documentation.
- **Expected Result**: Panels show live data; no "No data" or "Query failed" errors (except when data genuinely absent).
- **Evidence**: Dashboard screenshots (placeholders), query responses, data source health.
- **Automation Potential**: Medium — can verify panel JSON and metric queries via API.
- **Responsible Operator**: SRE / devops.
- **Failure Severity**: Low — dashboard stale data affects visibility but not runtime.

> **Critical**: Dashboard availability ≠ monitoring functional. A dashboard may load without errors while no metrics are being ingested. Always verify data existence (panel query) rather than merely panel loading.

## 10.9 Loki Log Ingestion
- **Objective**: Verify that logs are ingested into Loki, are searchable, and that log queries return expected results.
- **Scope**: Application log streams, platform logs (kube-apiserver, etc.).
- **Preconditions**: Fluent Bit/Fwd forwarding to Loki; Loki running.
- **Test Method**: Submit a known log line; query via Loki API (`/loki/api/v1/query`); verify label extraction.
- **Expected Result**: Log appears in query results with extracted labels (stream, job, namespace).
- **Evidence**: Loki API query results, log stream listing.
- **Automation Potential**: High — log injection and query automation.
- **Responsible Operator**: SRE / logging team.
- **Failure Severity**: Low — log loss affects debugging but not runtime.

## 10.10 Fluent Bit Forwarding
- **Objective**: Verify that Fluent Bit collects logs from node sources and forwards them to Loki or other destinations.
- **Scope**: Fluent Bit DaemonSet, output configurations, tag matching.
- **Preconditions**: Fluent Bit running on all nodes; output destinations configured.
- **Test Method**: Check Fluent Bit status on a node; tag a test log; verify arrival at destination.
- **Expected Result**: Fluent Bit DaemonSet ready; logs arrive at Loki/destination; no tag mismatches.
- **Evidence**: Fluent Bit status (`fluentctl status` or `kubectl get daemonset`), destination logs.
- **Automation Potential**: High — DaemonSet health checks, tag verification scripts.
- **Responsible Operator**: SRE / logging team.
- **Failure Severity**: Low — log forwarding loss affects debugging; not immediately disruptive.

## 10.11 K8s Event Collection
- **Objective**: Verify that K8s events are collected and visible via the monitoring stack (Prometheus alerts may fire on event scarcity).
- **Scope**: Core K8s events, component events, user workload events.
- **Preconditions**: K8s event source configured in Prometheus or Loki pipeline.
- **Test Method**: Create a minor K8s event (e.g., `kubectl patch` on a resource); verify event appears in monitoring endpoint or Loki.
- **Expected Result**: Event collected; visible in monitoring endpoint; correlated with metrics if applicable.
- **Evidence**: Monitoring endpoint output, Loki query results.
- **Automation Potential**: Medium — event creation and collection verification scriptable.
- **Responsible Operator**: SRE / ops team.
- **Failure Severity**: Low — event loss affects post-incident analysis; not runtime-impacting.

## 10.12 Correlation of Logs/Metrics/Alerts
- **Objective**: Verify end-to-end correlation: a single event (request error) generates a metric, a log entry, and an alert, all linked by shared labels/trace IDs.
- **Scope**: Full stack from application request to alert notification.
- **Preconditions**: Application instrumented with metrics, tracing, and logging; Prometheus, Loki, and tracing (Jaeger/OTEL) configured.
- **Test Method**: Invoke a failing request; check that: (a) a metric increments, (b) a log entry is written, (c) an alert fires, (d) all three share labels (request ID, trace ID).
- **Expected Result**: All three data pillars fire for the same event; labels match; trace ID links them.
- **Evidence**: Metric query result, log query result, alertmanager alert payload, trace ID correlation.
- **Automation Potential**: High — automated end-to-end test with request injection.
- **Responsible Operator**: SRE / observability team.
- **Failure Severity**: High — inability to correlate logs/metrics/alerts means extended MTTR during incidents.

## 10.13 Thanos Integration
- **Objective**: Verify that Thanos sidecar combines Prometheus clusters; query range works across members; no single-node data loss.
- **Scope**: Thanos sidecars, querier, store gateway.
- **Preconditions**: Multi-cluster or single-cluster Thanos deployment.
- **Test Method**: Query across reported Prometheus instances via Thanos querier; verify consistent series; check compaction status.
- **Expected Result**: Series visible across all member Prometheus instances; compaction running; no "unknown" label gaps.
- **Evidence**: Thanos querier UI, compaction metrics (`thanos_compactor_series_total`).
- **Automation Potential**: Medium — Thanos health APIs scriptable.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: Medium — Thanos downtime affects historical query ability.

## 10.14 Monitoring Self-Observability
- **Objective**: Verify that the monitoring stack itself is observable — its own metrics, alerts, and dashboards are functional and self-describing.
- **Scope**: Monitoring component metrics (Prometheus itself, Alertmanager, Grafana, Thanos).
- **Preconditions**: Monitoring stack running; self-scraping configured.
- **Test Method**: Query monitoring-internal metrics; verify self-alerts fire; load self-dashboards.
- **Expected Result**: Monitoring components report healthy; self-alerts only on genuine component issues; dashboards render.
- **Evidence**: Internal metric queries, self-alert state, dashboard render status.
- **Automation Potential**: High — self-monitoring as a CI check.
- **Responsible Operator**: SRE / monitoring team.
- **Failure Severity**: High — if the monitoring stack cannot monitor itself, all other alerts are untrusted.

## 10.15 Synthetic Failure Scenarios and Expected Alerts
| Scenario | Trigger | Expected Alert(s) | Routing |
|----------|---------|-------------------|---------|
| Prometheus scrape failure | Target down > 2 scrape intervals | `PrometheusScrapeFailure` | SRE on-call |
| High error rate | `rate(http_requests_total{status=~"5.."}[1m]) > threshold` | `HighErrorRate` | SRE on-call, Slack #sre-alerts |
| SLO burn rate > 50% in 1h | `slo_burn_rate` > 0.5 for 1h | `SLOBurnRateHigh` | SRE on-call, PagerDuty |
| Alertmanager routing failure | Alert not routed within 5m | `AlertmanagerRoutingFailure` | SRE on-call |
| Loki log ingestion lag | Lag > 5m between app write and Loki visibility | `LokiIngestionLag` | SRE on-call |

> **Note**: Scenarios use illustrative/placeholder values. Actual thresholds are defined in the platform's SLO/error budget configuration.

## 10.16 Actionable Alert Requirements
All alerts must meet these criteria:
1. **Discriminative**: Alert name and labels distinguish the root cause from similar events.
2. **Actionable**: Recipient can determine the fix or work-around from the alert alone (no "something is wrong" generic alerts).
3. **Correctly Routed**: Reaches the team/individual best positioned to respond, within the defined MTTR window.
4. **No Alert Fatigue**: Firing frequency respects the error budget; suppressed or inhibited where appropriate.

> **Design principle**: An alert that fires too often is worse than no alert — it trains responders to ignore it. Every alert must have a documented waiver path if the false-positive rate exceeds 5%.

## 10.17 Compliance and Placholder Values
All example thresholds, labels, and names in this section are **illustrative/placeholders**. Actual values are defined in the platform's `monitoring/` configuration and must be reviewed and approved by the SRE team before production deployment.