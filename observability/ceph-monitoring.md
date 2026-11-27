# Ceph and Rook-Ceph Monitoring

## Monitoring Spec Table

| Aspect | Details |
|---|---|
| **Health** | MON quorum availability; OSD availability and health; PG state (active+clean, degraded, incomplete); cluster capacity and utilization |
| **Metrics** | `ceph_health_status`, `ceph_pg_degraded`, `ceph_pg_active`, `ceph_pg_clean`, `ceph_pg_io_rate`, `ceph_osd_op_duration_seconds_bucket`, `ceph_osd_status`, `ceph_osd_up`, `ceph_osd_in`, `ceph_mon_command_latency_seconds_bucket`, `ceph_cluster_capacity_bytes`, `ceph_cluster_used_bytes`, `ceph_pool_replication`, `ceph_pool_usage_bytes`, `ceph_objectstore_io`, `ceph_scrub_running`, `ceph_deep_scrub_running`, `ceph_client_io_total`, `ceph_rbd_mirror_daemon_status` |
| **Collection** | `ceph-exporter` Prometheus metrics endpoint (`/metrics`); native `ceph` CLI (`ceph status`, `ceph health detail`, `ceph osd tree`, `ceph pg stat`, `ceph df`); Rook-Ceph CRDs (`CephCluster`, `CephObjectStore`, `CephBlockPool`); `ceph-mgr` module Prometheus endpoint; OSD disk S.M.A.R.T. attributes; RGW Swift/HTTP metrics |
| **Dashboards** | MON quorum and health status; OSD up/in/out status per host; PG state distribution (active+clean, degraded, scrubbing, recovery); pool usage and replication factor; I/O latency and throughput per pool; scrub and deep-scrub progress and duration; client I/O rates and error counts; RGW bucket and usage metrics |
| **Alerts** | `CephPoolDegraded` (ceph_pg_degraded > 0), `CephPoolFull` (ceph_cluster_used_bytes / ceph_cluster_capacity_bytes > 0.95), `OSDDown` (ceph_osd_up == 0), `OSDOut` (ceph_osd_in == 0), `SlowOps` (ceph_osd_op_duration_seconds_bucket{pct="99"} > threshold), `PGRecoveryStalled` (recovery progressing for > 2h), `DeepScrubStalled` (deep-scrub running for > 8h), `CEPHClientIoError` (ceph_client_io_errors_total > 0), `RGWError` (ceph_rbd_mirror_daemon_status == "error") |
| **SLI/SLO** | Availability SLO: 99.9% over 30d (ceph_health_status == 0); PG degraded rate SLO: < 1% over 30d (ceph_pg_degraded / ceph_pg_total < 0.01); capacity SLO: < 90% used over 30d (ceph_cluster_used_bytes / ceph_cluster_capacity_bytes < 0.90); I/O latency SLO: p99 < 50ms over 30d (ceph_osd_op_duration_seconds_bucket{pct="99"}); recovery SLO: recovery completes within 24h for typical PG size; scrub SLO: scrub completes within 8h; client I/O error SLO: 0 errors over 30d |
| **Tuning** | PG count per pool bucket count optimization; OSD disk performance class and cache tiering; network bandwidth per OSD; scrub and deep-scrub parallelism and scheduling; replication factor vs storage efficiency; cache mode (write-back/write-through) for OSDs |
| **Troubleshooting** | `ceph -s` for overall status; `ceph health detail` for specific issues; `ceph osd tree` for topology; `ceph pg ls degraded` for degraded PGs; `ceph pg stat` for PG state summary; `ceph df` for cluster capacity; `ceph osd perf` for OSD performance; `ceph mds dump` for MDS status; `rados -p <pool> -l list` for pool objects; `rados gw` for RGW status |
| **Recovery** | Restart failing OSD if disk healthy: `ceph osd restart <id>`; free disk space or add new OSDs to reduce PG size; increase PG count for the pool (`ceph osd pool set <pg_count>`); optimize stripe width/pool type; run `ceph pg recover <id>` to force recovery; run `ceph pg deep-scrub <id>` for deep cleaning; restore from backup if data loss occurred; rebalance cluster via `ceph osd rebalance`; renew RGW certificates if expired |
| **Dependencies** | MON quorum healthy (>= 2 of 3 MONs up); OSDs available and healthy (`ceph_osd_up == 1`); ceph-exporter scraping metrics from all OSDs and MONs; RGW service healthy if object storage used; Rook-Ceph CRDs healthy if using Rook; OSD disk S.M.A.R.T. no errors reported |

## Validation Commands (independent of Prometheus)

| Check | Command | Expected Output |
|---|---|---|
| Overall cluster health | `ceph -s` | `cluster health OK`; MONs up; OSDs up; PGs active+clean |
| Health detail | `ceph health detail` | Specific issues listed (degraded PGs, down OSDs, etc.) |
| OSD tree | `ceph osd tree` | Hierarchy of MONs, OSDs, and hosts; device paths |
| PG state | `ceph pg ls degraded` | List of degraded PGs; count matches `ceph_pg_degraded` |
| PG stat | `ceph pg stat` | Summary: total PGs, active+clean, degraded, incomplete, scrubbing |
| Cluster capacity | `ceph df` | Total, used, available bytes and object count; usage % calculated |
| OSD performance | `ceph osd perf` | OSD-level I/O rates, latency, and operations per second |
| PG deep-scrub status | `ceph pg deep-scrub map` | Which PGs are being deep-scrubbed; progress percentage |
| MDS status | `ceph mds status` | MDS daemon state; active/passive status |
| RGW health | `radosgw-admin bucket stats` | RGW bucket and usage statistics; TLS cert expiry if applicable |
