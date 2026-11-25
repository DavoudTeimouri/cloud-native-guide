# عملیاتPrometheus و Grafana

*مشاهده فقط — اینstellar illustrative only — not production-committed configurations. Marked as such where indicated.*

## طراحیJob اسکرپ

|Aspect|Design|
|---|---|
|**Service discovery**|استفاده از CRDs `ServiceMonitor` از بسته `prometheus-operator`. چند-cluster: پرونده-cluster Prometheus flawed `ServiceMonitor` با `namespaceSelector`.|
|**Relabeling**|بخش labelها minimal 유지: `cluster`, `namespace`, `job`, `instance`. `pod_uid`, `container_hash`، یا هر شناسه per-request را حذف کنید. از `keep`/`drop` actions برای کنترل etiquet‌های 드러 شده استفاده کنید.|
|**Metric cardinality control**|رد یا حذف labelها با cardinality بالا در زمان اسکرپ.俗 pattern: `metadata_exporter: keep_our_labels` که فقط `namespace`, `pod`, `container` را ذخیره می‌کند و `pod_uid`, `app_kubernetes_io_instance` و غیره را Drop می‌کند.|
|**Scrape intervals**|پیش‌فرض: `15s`. حداقل:.trade-off Prometheus `scrape_interval` / `evaluation_interval` را بررسی کنید. زیر 5s تنظیم نکنید بدون ارزشlend TSDB load.|
|**Scrape timeouts**|پیش‌فرض: `10s`. اگر اسکرپ بیش از بازه مدت interval انقدر طول بکشد، نتیجهPartialprevious محفوظ می‌شود و یک `scrape_duration_seconds` metric مدت زمان واقعی اسکرپ را ثبت می‌کند.Timeout > interval意味着 overlapping scraps — را از این خودداری کنید.|

**Valid Prometheus scrape config (illustrative):**

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - source_labels: [__meta_kubernetes_node_name]
        target_labels: [instance]
      - regex: .*
        target_labels: cluster
        replacement: '$KUBERNETES_CLUSTER_ID'
        action: labelmap
    metrics:
      node_exporter:
        enabled: true

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        target_labels: __path__
        action: replace
    metrics:
      selector: '.+'
      field: value
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token

  - job_name: 'cadvisor'
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - source_labels: [__meta_kubernetes_node_name]
        target_labels: instance
```

## Recording Rules and Alert Rules

**Recording rules (illustrative, placeholders labeled):**

```yaml
groups:
- name: illustrative-recording-rules
  rules:
  - record: job:node_memory_Mb:avg1m
    expr: (node_memory_MemTotal_bytes - node_memory_Blr_bytes) / 1024 / 1024 / 60
  - record: job:node_cpu_utilization:avg5m
    expr: 100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)
  - record: api_server_requests_per_second
    expr: rate(apiserver_request_count[1m])
  - record: dns_queries_failed_total
    expr: rate(dns_query_total{answer="false"}[1m])
```

**Alert rules (illustrative, placeholders labeled):**

```yaml
groups:
- name: illustrative-alert-rules
  rules:
  - alert: APIServerDown
    expr: up{job="apiserver"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "API server job has no healthy targets"
      runbook: "https://internal.runbooks/kubernetes.md#api-server-unavailable"

  - alert: HighErrorBudgetBurnRate
    expr: BurnRate(api_availability) > 7
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "API availability error budget burning faster than expected"
      runbook: "https://internal.runbooks/observability.md#burn-rate-alerting"

  - alert: DNSPacketDrop
    expr: dns_response_total{answer="false"} > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "DNS queries returning errors"
      runbook: "https://internal.runbooks/kubernetes.md#dns-resolution-failures"

  - alert: CephPGDegraded
    expr: ceph_pg_degraded > 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Ceph PGs in degraded state"
      runbook: "https://internal.runbooks/kubernetes.md#ceph-slow-ops--degraded-pgs"
```

**Alert grouping** uses `cluster`, `namespace`, `job` as group labels. inhibitions prevent a high-level alert from firing when lower-level alerts already cover the same condition.

**Inhibition examples (illustrative):**

```yaml
groups:
- name: illustrative-inhibitions
  rules:
  - alert: ClusterDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    matchers:
      - cluster = "production"

  - alert: NodeDown
    expr: up == 0
    for: 1m
    severity: warning
    matchers:
      - cluster != "production"

  - inhibitor:
    target_matchers:
      - cluster = "production"
    source_matchers:
      - cluster != "production"
    equal: ["alertname", "cluster"]
```

## OrganisationDashboard, Provisions and Version Control

- Dashboards are JSON files stored in Git under `observability/grafana-dashboards/`.
- Grafana provisioning uses labels `dashboard: true` and `search: true` to auto-discover dashboards; no need to hardcode UIDs.
- Version control: all dashboards, rules, and scrape configs live in Git; Argo CD applies them to the monitoring namespace.
- Change workflow: PR → CI (`promtool check rules`, `promtool check dashboards`) → merge → Argo CD sync.
- Dashboard categories (by scope):
  - `cluster-overview` — node/resource summary
  - `service-health` — per-service SLO progress
  - `infra-latency` — ingress, API, DB latency
  - `storage-health` — Ceph, PVC, registry
  - `auth-and-secrets` — Vault, Keycloak

## Prometheus Retention, Thanos HA and Failure Recovery

|| Component | Default | Configurable | HA / Recovery |
|---|---|---|---|
| **Prometheus TSDB retention** | 15d | via `prometheusSpec.retention` Helm value + PVC size | Restart with larger PVC; retention shortening does not auto-shrink volume |
| **Thanos sidecar** | — | `thanosSidecar.enabled` | Multiple sidecars per cluster; object storage is single source of truth |
| **Thanos querier** | — | — | Horizontally scalable; serves merged view across clusters |
| **Alertmanager** | — | `alertmanagerSpec.replicas` | Deploy as StatefulSet with `alertmanager-main` network; use `cluster` label for inhibition |

**Failure recovery**: If Prometheus process dies, the Operator restarts it from the last TSDB snapshot. If the PVC is lost, recover from Thanos object storage via `thanos replay` or `thanos object` to verify completeness.

## Sizing Monitoring Stack Resources; Monitoring Its Own Availability

|| Component | Requests | Limits | Typical PVC |
|---|---|---|---|
| Prometheus | 500m CPU, 2Gi memory | 2 CPU, 4Gi | 200Gi ceph-block |
| Alertmanager | 256m CPU, 1Gi memory | 1 CPU, 2Gi | 20Gi ceph-block |
| Grafana | 128m CPU, 512Mi memory | 512m CPU, 2Gi | 10Gi ceph-block (ephemeral) |
| Thanos sidecar | 256m CPU, 1Gi memory | 1 CPU, 2Gi | — (streams to object storage) |

**Self-monitoring**: The monitoring stack itself exports `prometheus_up`, `alertmanager_up`, `grafana_serving_status`. An auxiliary "monitoring-of-monitoring" ServiceMonitor scraps the `/metrics` endpoints of each component and alerts if any returns `up == 0`.

**Anti-pattern**: Running Prometheus with ` retention = 0` or extremely large `retentionSize` without adequate storage → OOM killer triggers → silent monitoring loss.

## Anti-Patterns

|| Anti-pattern | Risk | Mitigation |
|---|---|---|---|
| **Excessive cardinality** | TSDB memory explosion; slow queries | Keep label sets minimal; drop high-cardinality labels at scrape/relabel time |
| **Duplicate alerts** | Notification storms; engineers mute all alerts | Use inhibitions; deduplicate by `alertname` + `cluster` + `service` |
| **Alert fatigue** | Critical alerts buried in noise | Review alert volume quarterly; retire alerts with 0 firings in 30d |
| **Low-value dashboards** | Waste of maintenance time; false confidence | Dashboards must have an owner; retire if no one views them in 30d |
| **Missing scrape targets** | Silence; no visibility into failure | Alert on `up == 0` for each scrape job; use `probe` or `endpoint` health checks |
| **Silent monitoring failures** | Engineers don't know monitoring is broken | Alertmanager alerts if it cannot send notifications; Prometheus alerts if scrape fails |
| **Excessive Prometheus memory** | OOM; long GC pauses; missed scraps | Cap `storage.size`; monitor `prometheus_tsdb_flushed_samples_total`; profile heap regularly |

## Valid Examples

**Prometheus scrape config** — see section above.

**PromQL example (illustrative):**

```promql
# API availability over last 30d
availability_30d: (count(apiserver_request_count{job="apiserver", status=~"[1234].."}) / count(apiserver_request_count{job="apiserver"})) * 100

# Burn rate: how fast error budget depletes
burn_rate: (api_availability / 99.95) * (30d - time() + wall_time_start) / 30d

# p99 latency for ingress
ingress_latency_p99: histogram_quantile(0.99, sum(rate(nginx_ingress_controller_request_duration_seconds_bucket[5m])) by (le))
```

**Recording rule example** — see section above.

**Alert rule example** — see section above.