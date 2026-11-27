# SLOs and SLAs

## A. Purpose and scope

Document SLOs and SLAs: control-plane availability, etcd latency, API server response time, storage IOPS, network latency, alert thresholds.

Cross-references `monitoring/prometheus.md`, `monitoring/alerting-rules.md`, `monitoring/grafana-dashboards.md`.

## B. SLO targets (illustrative — pending approval)

The targets below are illustrative defaults. They are **not yet production-committed**. Approve production SLO targets and burn-rate alert factors with SRE and business stakeholders before using them for alerting or error-budget decisions.

## C. Production SLO approval register

Owner and target values below are **placeholders pending user approval**. Fill in the Approved target and Owner, then remove the "pending approval" note from section B.

| SLO | Proposed target | Measurement window | Approved target | Owner | Approval date |
|-----|-----------------|-------------------|-----------------|-------|---------------|
| Control-plane availability | 99.9% | 30 days | `<user-decision>` | `<user-decision>` | `<user-decision>` |
| etcd p99 read latency | < 10ms | 5 minutes | `<user-decision>` | `<user-decision>` | `<user-decision>` |
| etcd p99 write latency | < 50ms | 5 minutes | `<user-decision>` | `<user-decision>` | `<user-decision>` |
| API server p99 response time | < 500ms | 5 minutes | `<user-decision>` | `<user-decision>` | `<user-decision>` |
| Storage IOPS (RBD) | > 1000 | 5 minutes | `<user-decision>` | `<user-decision>` | `<user-decision>` |
| Storage latency (CephFS) | < 20ms | 5 minutes | `<user-decision>` | `<user-decision>` | `<user-decision>` |
| Network latency (node-to-node) | < 2ms | 5 minutes | `<user-decision>` | `<user-decision>` | `<user-decision>` |
| Alert delivery | < 2 minutes | Per alert | `<user-decision>` | `<user-decision>` | `<user-decision>` |

## E. Burn-rate alerts

Burn-rate alerts fire when error budget is consumed faster than allowed:

| Alert | Condition | Severity |
|-------|-----------|----------|
| Fast burn | >14.4x budget burn rate over 5 min | Critical |
| Slow burn | >6x budget burn rate over 6h | Warning |

Implement these in Prometheus recording/alerting rules once SLO targets are approved. See `monitoring/alerting-rules.md`.

## F. SLO targets table (provisional)

| SLO | Target | Measurement window | Alert threshold |
|-----|--------|-------------------|-----------------|
| Control-plane availability | 99.9% | 30 days | 99.0% |
| etcd p99 read latency | < 10ms | 5 minutes | > 50ms |
| etcd p99 write latency | < 50ms | 5 minutes | > 100ms |
| API server p99 response time | < 500ms | 5 minutes | > 2s |
| Storage IOPS (RBD) | > 1000 | 5 minutes | < 500 |
| Storage latency (CephFS) | < 20ms | 5 minutes | > 100ms |
| Network latency (node-to-node) | < 2ms | 5 minutes | > 10ms |
| Alert delivery | < 2 minutes | Per alert | > 5 minutes |

## G. Alert thresholds

| Alert | Condition | Severity |
|-------|-----------|----------|
| etcd down | etcd instance unavailable | Critical |
| etcd quorum lost | etcd majority unavailable | Critical |
| API server down | kube-apiserver unhealthy | Critical |
| Control plane unavailable | No Ready control-plane nodes | Critical |
| etcd high latency | p99 write latency > 100ms | Warning |
| Storage full | PVC usage > 85% | Warning |
| Network high latency | Node-to-node > 10ms | Warning |
| Alert not delivered | Alert not acknowledged in 5 min | Warning |

## H. SLO measurement

SLOs are measured from Prometheus metrics:

```promql
# Control-plane availability
up{job="kubernetes-nodes", node=~"control-plane.*"}

# etcd p99 write latency
histogram_quantile(0.99, rate(etcd_server_proposals_commit_seconds_bucket[5m]))

# API server p99 response time
histogram_quantile(0.99, rate(apiserver_request_duration_seconds_bucket[5m]))
```

## I. Cross-references

- `monitoring/prometheus.md` — Prometheus metrics
- `monitoring/alerting-rules.md` — Alert rules
- `monitoring/grafana-dashboards.md` — Dashboards
- `monitoring/slo-alert-validation.md` — Alert validation
