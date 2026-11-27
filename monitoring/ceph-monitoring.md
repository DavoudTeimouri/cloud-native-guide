# Ceph Monitoring

## A. Purpose and scope

Document Ceph monitoring: cluster health, OSD status, PG status, capacity, performance, alerting rules for Ceph.

Cross-references `storage/ceph/cephadm-deployment.md`, `monitoring/prometheus.md`, `monitoring/alerting-rules.md`.

## B. Cluster health checks

```bash
# Overall cluster health
ceph health detail

# Cluster status
ceph status

# OSD status
ceph osd status

# PG status
ceph pg status

# Pool status
ceph df
```

## C. Alert rules for Ceph

| Alert | Condition | Severity |
|-------|-----------|----------|
| Ceph health degraded | ceph health != HEALTH_OK | Critical |
| OSD down | OSD marked down | Warning |
| OSD full | OSD usage > 85% | Critical |
| PG degraded | PGs in degraded state | Warning |
| PG undersized | PGs below min_size | Critical |
| PG misplaced | PGs not where they should be | Warning |
| Capacity full | Cluster capacity > 85% | Critical |

```yaml
# Prometheus alert rule for Ceph health
- alert: CephHealthDegraded
  expr: ceph_health_status != 1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Ceph cluster health degraded"
```

## D. Performance metrics

| Metric | Prometheus query | Target |
|--------|-----------------|--------|
| Cluster throughput | rate(ceph_rbd_bytes[5m]) | Depends on workload |
| IOPS | rate(ceph_rbd_ops[5m]) | Depends on workload |
| Latency | ceph_rbd_latency_seconds | < 20ms |
| Recovery rate | ceph_recovery_bytes_total | < network bandwidth |

## E. Cross-references

- `storage/ceph/cephadm-deployment.md` — Ceph deployment
- `monitoring/prometheus.md` — Prometheus metrics
- `monitoring/alerting-rules.md` — Alert rules
