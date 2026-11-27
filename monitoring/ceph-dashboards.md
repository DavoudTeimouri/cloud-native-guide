# Ceph Grafana Dashboards
## A. Purpose and scope
Document Ceph Grafana dashboards: cluster health, OSD performance, PG status, capacity planning.
Cross-references `monitoring/ceph-monitoring.md`, `monitoring/grafana-dashboards.md`, `storage/ceph/cephadm-deployment.md`.

## B. Dashboard categories
| Dashboard | Scope | Datasource | Description |
|-----------|-------|------------|-------------|
| Cluster health | MON status, quorum, overall health | Prometheus | Ceph cluster health overview, monitor quorum status, OSD map summary |
| OSD performance | OSD I/O latency, throughput, commit time | Prometheus | Per-OSD commit latency, I/O bytes/sec, ops/sec, device health |
| PG status | PG health distribution, state, peering | Prometheus | PG status distribution, degraded/missing/undersized counts, PG peering progress |
| Capacity planning | Pool usage, OSD capacity, warning thresholds | Prometheus | Pool byte usage, OSD used %, cluster capacity, forecast based on growth rate |

## C. Detailed dashboard panels

### 1. Cluster Health Dashboard
- **ceph_health_status** — Overall cluster health (1 = HEALTH_OK, 0 = degraded/error)
- **ceph_mon_quorum_status** — Quorum status (1 = quorum healthy, 0 = lost)
- **ceph_osd_up** — Percentage of OSDs that are up
- **ceph_osd_in** — Percentage of OSDs that are in (active member of cluster)
- **ceph_mon_up** — Percentage of MONs that are up

### 2. OSD Performance Dashboard
- **ceph_osd_commit_latency_ms** — OSD commit latency (target: < 20ms p99)
- **ceph_osd_io_bytes_total** — I/O bytes per second (read + write)
- **ceph_osd_ops** — Operations per second (read + write)
- **ceph_osd_queue_depth** — Pending I/O queue depth per OSD
- **ceph_osd_object_count** — Number of objects per OSD

### 3. PG Status Dashboard
- **ceph_pg_status** — PG health status distribution (active+clean, degraded, incomplete, undersized, misplaced)
- **ceph_pg_degraded** — Count of degraded PGs
- **ceph_pg_incomplete** — Count of incomplete PGs
- **ceph_pg_oversized** — Count of oversized PGs
- **pg_distribution** — PG count per OSD (distribution fairness metric)

### 4. Capacity Planning Dashboard
- **ceph_pool_bytes_used** — Bytes used per pool
- **ceph_pool_bytes_total** — Total bytes per pool
- **ceph_osd_used** — Used bytes per OSD
- **ceph_df** — Cluster-wide capacity (used % of total)
- **ceph_pool_target_size** — Target pool size
- **ceph_pool_size** — Pool size factor (replication factor or EC scheme)

## D. Verification
```bash
# Verify Grafana is reachable
kubectl -n monitoring get svc grafana

# Verify dashboards are provisioned
kubectl -n monitoring get grafanadashboard

# Verify datasource points to Prometheus
kubectl -n monitoring get grafanadatasource -o yaml

# Reload dashboards from Argo CD
argocd app sync mgmt-grafana
```

## E. Cross-references
- `monitoring/ceph-monitoring.md` — Ceph monitoring overview and alert rules
- `monitoring/grafana-dashboards.md` — General Grafana dashboard overview and configuration
- `storage/ceph/cephadm-deployment.md` — Ceph deployment and sizing reference
