# Auto-Test Ceph Performance Tuning Procedures

This document covers automated testing procedures for Ceph performance tuning, including OSD tuning, pool configuration, CRUSH rules, and cache tiers. Intended for integration into CI/CD pipelines and operational verification.

## A. OSD Tuning Tests

### 1. BlueStore Parameter Validation

```bash
# Verify bluestore_cache_size is within recommended range
ceph osd dump | grep bluestore_cache_size

# Validate scrub period is set appropriately
ceph osd dump | grep bluestore_scrub_period

# Check compaction interval settings
ceph osd dump | grep bluestore_compaction_interval
```

**Expected:** All OSDs report parameters within recommended ranges (see performance-tuning.md for defaults).

### 2. OSD Process Sizing Validation

```bash
# Check OSD count and per-host distribution
ceph osd dump | grep "osd.\|host"

# Verify no OSD RAM oversubscription
# One OSD daemon per data disk; each reserves ~4 GiB cache plus DB/WAL working set
# Host with 8 OSDs needs ~32 GiB for OSD processes alone
```

**Expected:** OSD count matches hardware; per-host RAM utilization below 75%.

### 3. OSD Startup Flag Tests

```bash
# Set priority for interactive workloads
ceph osd set_priority <osd-id> 1.0

# Throttle OSD disk I/O (bytes per second per OSD)
ceph osd max_bytes_per_sec <osd-id> <bytes>

# Throttle OSD operation rate (ops per second per OSD)
ceph osd max_ops_per_sec <osd-id> <ops>
```

**Expected:** Throttle values do not reduce observed throughput below baseline; priority changes take effect without restart.

## C. Pool Configuration Tests

### 1. PG Count Calculation Validation

```bash
# Calculate recommended PG count per pool
# total_pgs = (num_osd × 100) / pool_replica_count
# Round up to nearest power of 2 per pool

# Example: 9 OSDs, 3-replica pool
echo "scale=0; (9 * 100) / 3" | bc
# → 300 → round to 512

# Validate with ceph pg calc
ceph pg calc
```

**Expected:** PG count is a power of 2 and matches `ceph pg calc` output.

### 2. Pool Parameter Setting Tests

```bash
# Create pool with tuned settings
ceph osd pool create <pool-name> <pg-num> <pgp-num> replicated

# Set maximum size to prevent unbounded growth
ceph osd pool set <pool-name> max_size <n>

# Verify size <= max_size
ceph osd pool get <pool-name> | grep -E "size|max_size"
```

**Expected:** `size` ≤ `max_size`; pool operates within quotas.

### 3. Pool Monitoring Signal Tests

```bash
# Monitor pool bytes used
ceph osd pool stats <pool-name> | grep bytes_used

# Check PG degradation
ceph pg stat | grep decommission

# Monitor OSD operation rate
ceph osd stat | grep ops
```

**Expected:** `ceph_pool_bytes_used` within normal range; `ceph_pg_degraded` = 0; `ceph_osd_op` ops/sec within baseline.

## D. CRUSH Rules Tests

### 1. CRUSH Ruleset Validation

```bash
# List existing rulesets
ceph osd crush rule ls

# Show default host ruleset
ceph osd crush rule dump host

# Verify custom ruleset is assigned to pool
ceph osd pool get <pool-name> | grep crush_rule
```

**Expected:** Rulesets exist; pool uses intended ruleset; no misplacement from rule changes.

### 2. CRUSH Reweight and Rebalance Tests

```bash
# Reweight a CRUSH bucket
ceph osd crush reweight <bucket> <new-weight>

# Run rebalance after rule change
ceph osd rebalance

# Verify PG distribution is correct
ceph osd tree | grep -E "pg|root"
```

**Expected:** PGs redistribute correctly; no data distribution anomalies after reweighting.

### 3. Misplacement Detection Tests

```bash
# Check for misplaced objects
ceph osd misplaced_pg sum

# Check for crushed (misconfigured) PGs
ceph osd crushed map
```

**Expected:** `ceph osd misplaced_pg sum` = 0; `ceph osd crushed map` shows no entries.

## E. Cache Tier Tests

### 1. BlueStore Cache Hit Ratio Tests

```bash
# Check cache read hit ratio per OSD
ceph osd stat

# Verify read hit ratio > 0.9
# (Collect via Prometheus: ceph_osd_cache_read_hit_ratio)
```

**Expected:** Cache read hit ratio > 0.9 across OSDs; if < 0.7, investigate cache size.

### 2. Write-Back Cache Tests

```bash
# Enable write-back for OSD with BBU
ceph osd set slow_key <osd-id>  # disables sync write until cache is flushed

# Configure cache tier retention
ceph osd pool set <pool-name> write_cache_size <size>
```

**Expected:** Write-back enabled without data loss; cache size within OSD memory limits.

## F. End-to-End Automated Test Suite

### 1. Full Performance Test Script

```bash
#!/bin/bash
# Auto-test: Ceph performance tuning validation

set -e

echo "=== Ceph Performance Auto-Test ==="

# Pre-check: cluster health
if [ "$(ceph health -q)" != "HEALTH_OK" ]; then
    echo "FAIL: Cluster not HEALTH_OK"
    exit 1
fi

# Check OSD status
OSD_COUNT=$(ceph osd stat | grep -oP 'osd.\d+' | wc -l)
echo "OSD count: $OSD_COUNT"

# Validate PG count per pool
for pool in $(ceph osd pool ls); do
    PGs=$(ceph osd pool get $pool pgp | grep -oP '\d+')
    echo "Pool $pool PGP: $PGs"
done

# Check CRUSH ruleset misplacement
MISPLACED=$(ceph osd misplaced_pg sum)
if [ "$MISPLACED" -ne 0 ]; then
    echo "FAIL: $MISPLACED misplaced PGs"
    exit 1
fi

# Check cache hit ratios (via Prometheus if available)
if command -v prometheus-cli &>/dev/null; then
    RATIO=$(prometheus-cli "ceph_osd_cache_read_hit_ratio" | awk '{print $2}')
    if (( $(echo "$RATIO < 0.7" | bc -l) )); then
        echo "FAIL: Cache hit ratio $RATIO < 0.7"
        exit 1
    fi
fi

echo "=== All auto-tests passed ==="
```
