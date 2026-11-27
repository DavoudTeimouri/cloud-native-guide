# SLOs and SLAs

## A. Purpose and scope

Document SLOs and SLAs: control-plane availability, etcd latency, API server response time, storage IOPS, network latency, alert thresholds.

Cross-references `monitoring/prometheus.md`, `monitoring/alerting-rules.md`, `monitoring/grafana-dashboards.md`.

## B. SLO targets

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

## C. Alert thresholds

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

## D. SLO measurement

SLOs are measured from Prometheus metrics:

```promql
# Control-plane availability
up{job="kubernetes-nodes", node=~"control-plane.*"}

# etcd p99 write latency
histogram_quantile(0.99, rate(etcd_server_proposals_commit_seconds_bucket[5m]))

# API server p99 response time
histogram_quantile(0.99, rate(apiserver_request_duration_seconds_bucket[5m]))
```

## E. Cross-references

- `monitoring/prometheus.md` — Prometheus metrics
- `monitoring/alerting-rules.md` — Alert rules
- `monitoring/grafana-dashboards.md` — Dashboards
- `monitoring/slo-alert-validation.md` — Alert validation
