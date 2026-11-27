# Ceph OSD Health Monitoring Procedures

## OSD Status Checks

### Check Individual OSD Status
```bash
# Check a specific OSD
ceph osd status

# Detailed status for a specific OSD number
ceph osd info osd.<ID>

# Show OSD map with weights and utilization
ceph osd dump
```

### Common OSD Health Commands
```bash
# OSD map - shows all OSDs and their state
ceph osd dump

# Query specific OSD status
ceph osd stat

# List OSDs in weight order
ceph osd tree

# Show OSD usage and utilization
ceph osd df
```

### OSD Health Flags
- `up` - OSD is running and responsive
- `in` - OSD is part of the cluster
- `out` - OSD is marked out (for migration)
- `full` - OSD is above the `osd_max_full_ratio` threshold
- `nearfull` - OSD is near the full threshold
- `slow` - OSD is responding slowly
- `pause` - OSD is paused

## PG (Placement Group) Health

### Check PG States
```bash
# Overall PG map
ceph pg map <pg_name>

# All PG states summary
ceph pg stat

# Detailed PG information
ceph pg dump

# PGs by state
ceph pg dump_stuck

# Count PGs in each state
ceph pg stat | grep -E "active|unclean|degraded|offline"
```

### Common PG Health Issues
- **Active PGs**: Normal operating state
- **Unclean PGs**: Some OSDs holding PG data are down - requires attention
- **Degraded PGs**: Some OSDs are missing - data protection is reduced
- **Stuck PGs**: PGs not transitioning as expected - may need intervention

### PG Recovery
```bash
# Check if recovery is in progress
ceph pg <pg_id> query

# Force recovery start for a PG
ceph pg <pg_id> mark_unfound_lost

# Monitor recovery progress
ceph -w

# Check OSDmap for recovery status
ceph osd map <pool> <obj>
```

## Cluster Health

### Basic Cluster Health Check
```bash
# Overall cluster health status
ceph health

# Detailed cluster health
ceph health detail

# Cluster summary with services
ceph status
```

### Monitor Cluster Operations
```bash
# Watch cluster events in real-time
ceph -w

# Show cluster map information
ceph osd dump

# Monitor MDS, MON, and MGR services
ceph mds stat
ceph mon stat
ceph mgr stat
```

### Cluster Health Indicators
- `HEALTH_OK` - All systems nominal
- `HEALTH_WARN` - Warning conditions exist
- `HEALTH_ERR` - Error conditions exist
- `HEALTH_MAX` - Multiple error conditions

## Recovery Procedures

### OSD Recovery

```bash
# Mark an OSD as out before removal/maintenance
ceph osd out osd.<ID>

# Remove an OSD from the cluster
ceph osd remove osd.<ID>

# Add a new OSD to the cluster
ceph osd create

# Start an OSD
ceph osd start osd.<ID>

# Stop an OSD
ceph osd stop osd.<ID>
```

### PG Recovery

```bash
# Check recovery status
ceph pg <pg_id> query

# Monitor overall recovery
ceph status | grep -i recover

# Check PGs waiting for recovery
ceph pg dump | grep -E "stale|stuck"

# Accelerate recovery (if needed)
ceph osd set slow_pg_threshold <seconds>

# Balance PGs across OSDs
ceph osd reweight osd.<ID> <value>
```

### Cluster Rebalancing

```bash
# Rebalance PGs after OSD changes
ceph osd rebalance

# Set rebalance threshold
ceph osd set recheck_interval <seconds>

# Monitor rebalance progress
ceph -w | grep -E "rebalance|mov"
```

### Data Integrity Checks

```bash
# Run OSD data consistency checks
ceph osd scrub osd.<ID>

# Deep scrub (more thorough, slower)
ceph osd deep_scrub osd.<ID>

# Check OSD integrity
ceph osd tree | grep -i osd.<ID>

# Verify object completeness
ceph osd dump | grep "min_osd_ratio"
```

## Automated Monitoring Scripts

### Basic Health Check Script
```bash
#!/bin/bash
# Ceph health monitoring basic script

STATUS=$(ceph health 2>&1)
if [ "$STATUS" = "HEALTH_OK" ]; then
    echo "[$(date)] Ceph cluster: HEALTH_OK" >> /var/log/ceph-health.log
else
    echo "[$(date)] Ceph cluster: $STATUS" >> /var/log/ceph-health.log
    ceph health detail >> /var/log/ceph-health.log
fi

# Check OSD status
ceph osd stat >> /var/log/ceph-health.log

# Check PG status
ceph pg stat >> /var/log/ceph-health.log

# Check for any stuck PGs
STUCK=$(ceph pg dump_stuck 2>/dev/null | wc -l)
if [ "$STUCK" -gt 0 ]; then
    echo "WARNING: $STUCK stuck PGs found" >> /var/log/ceph-health.log
fi
```

### Schedule with cron
```bash
# Add to crontab for hourly health checks
0 * * * * /usr/local/bin/ceph-health-check.sh >> /var/log/ceph-health.log 2>&1
```

## Alert Conditions

### Critical Alerts
- `HEALTH_ERR` in cluster health
- Any OSD down (`up` flag missing)
- Degraded PGs (`degraded` count > 0)
- Unclean PGs (`unclean` count > 0)
- OSDs above full ratio (`full` flag)
- Stuck PGs not recovering

### Warning Alerts
- OSDs near full ratio (`nearfull` flag)
- Slow responding OSDs (`slow` flag)
- PGs approaching backfill limits
- Monitors out of quorum

## Troubleshooting Guide

### Common Issues and Resolutions

1. **OSD marked down**
   - Check physical connectivity
   - Verify OSD process is running: `systemctl status ceph-osd@<ID>`
   - Check device availability and mount status
   - Restart OSD if needed: `ceph osd start osd.<ID>`

2. **PGs in degraded state**
   - Verify which OSDs are down
   - Check for storage capacity issues
   - Monitor recovery progress with `ceph -w`
   - Add back missing OSDs or replace hardware

3. **PGs stuck in recovery**
   - Check OSD logs for I/O errors
   - Verify cluster has sufficient resources (CPU, memory, network)
   - Consider increasing `osd_max_backfills` if PGs are stuck due to too many concurrent operations
   - Check for network partitions or latency issues

4. **Cluster near full**
   - Add new OSDs to the cluster
   - Rebalance PGs to distribute data
   - Check `osd_full_ratio` and `osd_max_full_ratio` settings