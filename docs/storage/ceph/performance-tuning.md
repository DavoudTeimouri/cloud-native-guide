# Ceph Performance Tuning

[Previous step](cephadm-deployment.md) | [Next step](../rook-ceph/rook-ceph.md)

## A. Purpose and scope

Document Ceph performance tuning levers: OSD parameters, pool settings, CRUSH configuration, cache tiers, and monitoring dashboards. Every change should be validated in a staging environment before applying to production.

## B. OSD tuning

### B.1 BlueStore tuning

| Parameter | Default | Recommended range | Impact |
|---|---|---|---|
| `bluestore_cache_size` | Auto (RAM × 5%) | `0.3–0.5 × RAM` per OSD | Controls read/write cache size; too large starves the OS, too small increases disk I/O |
| `bluestore_scrub_period` | `3600` (seconds) | `3600–86400` | Scrub frequency; lower to detect corruption sooner, higher reduces I/O load |
| `bluestore_leaf_size` | Auto (filesystem block) | `4096` or `65536` | Affects small-file throughput; larger leaf size reduces metadata operations |
| `bluestore_compaction_interval` | `3600` (seconds) | `86400–604800` (daily–weekly) | Periodic LSM compaction; too frequent wastes CPU, too rare causes read amplification |
| `bluestore_compaction_stall_threshold` | `20` (percent) | `10–30` | Stalls compaction if WAL exceeds this percent; lower = more aggressive compaction |

### B.2 OSD process sizing

- One OSD daemon per data disk; each daemon reserves ~4 GiB cache plus the BlueStore DB/WAL working set.
- Host with 8 OSDs needs ~32 GiB for OSD processes alone, plus OS overhead.
- Do not oversubscribe RAM per host beyond 75% utilization; reduce OSDs per host before reducing vCPU.

### B.3 OSD startup flags (if needed)

```bash
# Increase priority for interactive workloads
ceph osd set_priority <osd-id> 1.0

# Throttle OSD disk I/O (bytes per second per OSD)
ceph osd max_bytes_per_sec <osd-id> <bytes>

# Throttle OSD operation rate (ops per second per OSD)
ceph osd max_ops_per_sec <osd-id> <ops>
```

## C. Pool configuration

### C.1 Replicated pool PG count

Rule of thumb (approximate, tune from `ceph pg calc`):

```
total_pgs = (num_osd × 100) / pool_replica_count
```

Round up to the nearest power of 2 per pool.

**Example:** 9 OSDs across 3 hosts, 3-replica pool → `(9 × 100) / 3 = 300` → round to 512 PGs.

A small 3-host site needs only ~512–1024 PGs total across all pools. Adding pools without reducing PG count per pool multiplies PG count and increases MON/OSD memory.

### C.2 Pool parameters for performance

```bash
# Create a pool with tuned settings
ceph osd pool create <pool-name> <pg-num> <pgp-num> [erasure|replicated]

# Set a maximum size (in bytes) to prevent unbounded growth
ceph osd pool set <pool-name> max_size <n>

# Set target size (how many copies/fragments to store)
ceph osd pool set <pool-name> size <n>

# Enable/affinity PGs to specific OSDs for QoS isolation
ceph osd pool set <pool-name> target_size <n>

# Control PG autobalancing
ceph osd set no_autobalancer   # disable
ceph osd unset no_autobalancer # enable

# Set hit/set for anti-affinity (distribute PGs across failure domains)
ceph osd pool set <pool-name> hit_set_type <type>
```

### C.3 Pool monitoring signals

| Signal | Normal range | Alert threshold |
|---|---|---|
| `ceph_pool_bytes_used` | Monotonically increasing | Sudden > 80% of pool quota |
| `ceph_pg_degraded` | 0 | Any value > 0 |
| `ceph_pg_incomplete` | 0 | Any value > 0 |
| `ceph_osd_op` ops/sec | Workload-dependent | Sudden spike > 2× baseline |
| `ceph_osd_commit_latency_ms` | < 50 ms | > 200 ms sustained |
| `ceph_osd_queue_depth` | < 50 | > 200 |

## D. CRUSH rules

### D.1 Default CRUSH ruleset

The default `host` ruleset is adequate for most sites. It uses failure domains defined by label:

- `host` (physical server)
- `rack` (when racks are present)
- `row` (optional)
- `pdu` (optional)
- `root` (the cluster root)

### D.2 Creating a custom CRUSH ruleset

```bash
# List existing rulesets
ceph osd crush rule ls

# Show the default host ruleset
ceph osd crush rule dump host

# Create a ruleset with rack awareness
ceph osd crush rule create replicate rack <name> <k> <m>
# Example: 3-replica across racks
ceph osd crush rule create replicate my-replicated 3 0

# Create a ruleset with erasure coding
ceph osd crush rule create erasure <name> <k> <m>
# Example: 4+2 EC
ceph osd crush rule create erasure my-ec 4 2

# Assign a pool to use a specific ruleset
ceph osd pool set <pool-name> crush_rule <rule-name>
```

### D.3 Tuning CRUSH bucket weights

- Weights should reflect relative capacity of each bucket.
- Use `ceph osd crush reweight <bucket> <new-weight>` to adjust incrementally.
- After reweighting, run `ceph osd rebalance` to redistribute PGs.

### D.4 CRUSH misplacement detection

```bash
# Check for misplaced objects
ceph osd misplaced_pg sum

# Check for acting outside of failure domain
ceph osd crushed map
```

## E. Cache tiers (Read/Write)

### E.1 BlueStore cache tiering

Ceph automatically uses the OSD SSD/NVMe as a read/write cache (the "BlueStore cache"). No separate tiering configuration is needed for most workloads.

### E.2 Explicit device class tiering

If using different device classes (e.g., SSD + HDD), define device classes and assign OSDs:

```bash
# Device classes
ceph osd device class add ssd
ceph osd device class add hdd

# Assign a device class when creating OSD (via cephadm or manually)
# Then use CRUSH rules to stripe across classes
```

### E.3 Write-back cache with BBU

If using write-back SSD with Battery-Backed Write cache:

```bash
# Enable write-back for an OSD
ceph osd set slow_key <osd-id>  # disables sync write until cache is flushed

# Configure cache tier retention
ceph osd pool set <pool-name> write_cache_size <size>
```

### E.4 Cache tier performance signals

| Signal | Normal | Alert |
|---|---|---|
| `ceph_osd_cache_read_hit_ratio` | > 0.9 | < 0.7 |
| `ceph_osd_cache_write_backlog` | 0 | > 1000 entries |
| `ceph_osd_cache_size` | Configurable | Exceeds OSD memory limit |

## F. Performance monitoring

### F.1 Key Prometheus metrics

| Metric | What it measures | Alert condition |
|---|---|---|
| `ceph_health_status` | Overall cluster health | Any value other than 0 (HEALTH_OK) |
| `ceph_osd_up` | OSD daemon availability | Any value < number of OSDs |
| `ceph_pg_degraded` | PGs not fully active | Any value > 0 |
| `ceph_pg_incomplete` | PGs not fully recovered | Any value > 0 |
| `ceph_pool_bytes_used` | Pool capacity usage | > 80% of quota |
| `ceph_osd_commit_latency_ms` | OSD commit latency | > 200 ms sustained |
| `ceph_osd_queue_depth` | Pending ops per OSD | > 200 |
| `ceph_mon_election_duration_sec` | MON election time | > 15 seconds |
| `ceph_mon_sync_lag_sec` | MON clock sync lag | > 5 seconds |

### F.2 Alerting rules (Prometheus example)

```yaml
groups:
- name: ceph-performance
  rules:
  - alert: CephClusterDegraded
    expr: ceph_pg_degraded > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Ceph cluster has degraded PGs"
      description: "PG degradation detected: {{ $value }} PGs degraded"

  - alert: CephOSDCommitLatencyHigh
    expr: histogram_quantile(0.99, sum(rate(ceph_osd_commit_latency_ms_bucket[5m])) by (le)) > 200
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High OSD commit latency"
      description: "99th percentile commit latency > 200ms over 5m"

  - alert: CephPoolCapacityHigh
    expr: (ceph_pool_bytes_used / ceph_pool_bytes_total) > 0.8
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Ceph pool capacity usage high"
      description: "Pool usage at {{ $value | humanize }} over 10m"
```

### F.3 Dashboard view (Grafana)

Panel groups to include:

1. **Cluster health**: `ceph_health_status` single value
2. **PG state**: `ceph_pg_state` histogram (active, clean, recovering, etc.)
3. **IOPS per OSD**: `rate(ceph_osd_ops[1m])` per OSD, aggregated
4. **Latency per OSD**: `histogram_quantile(0.95, sum(rate(ceph_osd_commit_latency_ms_bucket[5m])) by (le))` per OSD
5. **Cache hit ratio**: `ceph_osd_cache_read_hit_ratio` per OSD
6. **Pool usage**: `ceph_pool_bytes_used` / `ceph_pool_bytes_total` per pool

## G. Tuning workflow

1. **Measure baseline**: Run `ceph -s` and record PG count, OSD health, pool usage, latency.
2. **One change at a time**: Apply a single tuning parameter; wait at least one full OSD interval (typically 30m–2h) before measuring.
3. **Validate in staging**: Apply changes to a staging cluster first; compare metrics against production baseline.
4. **Rollback plan**: Before changing CRUSH rules or pool PG count, document the revert command and expected impact.
5. **Re-measure after cluster stabilization**: PGs need time to rebalance after any configuration change; wait for `active+clean` with `undersized=0`.

## H. Common anti-patterns

| Anti-pattern | Consequence | Fix |
|---|---|---|
| Too many PGs per pool | MON/OSD memory pressure, slow PG operations | Reduce PG count; recalculate with `ceph pg calc` |
| Too few PGs per pool | Uneven distribution, hot spots, slow rebalancing | Increase PG count; recalculate with `ceph pg calc` |
| `max_bytes_per_sec` too low | Throttles legitimate traffic, slows backups | Raise or remove limit |
| `size` > `max_size` on replicated pool | Writes rejected unexpectedly | Ensure `max_size >= size` |
| CRUSH rule change without rebalancing | PGs act on wrong OSDs, data distribution incorrect | Run `ceph osd rebalance` after rule change |
| Disabling scrub entirely | Corruption goes undetected longer | Keep default scrub period; reduce if needed |
| Over-provisioning cache size | RAM starvation, OS instability | Cap at 50% of host RAM; monitor host metrics |

[Previous step](cephadm-deployment.md) | [Next step](../rook-ceph/rook-ceph.md)