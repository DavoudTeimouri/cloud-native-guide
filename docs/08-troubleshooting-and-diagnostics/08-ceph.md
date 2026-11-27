# Ceph

## Symptoms
- Ceph health HEALTH_ERR/WARN
- OSD down or out
- MON quorum lost
- PG degraded/undersized/misplaced
- Capacity above threshold (70%/80%)
- RBD/CEPHFS not mounting

## Possible causes
- OSD disk failure or full
- MON network partition or member down
- PG rebalancing or backfill in progress
- Network partition between OSD nodes
- CephFS MDS failure

## Diagnostic commands
```bash
# Cluster health
ceph -s
ceph health detail
ceph osd stat
ceph osd df
ceph pg stat

# MON/OSD
ceph mon stat
ceph osd tree
ceph osd dump | head -50

# Logs
ceph log last 100
journalctl -u ceph-* -n 50
```

## Expected output
- ceph -s: HEALTH_OK
- osd stat: all OSDs up and in
- pg stat: active+clean
- osd tree: all nodes/OSDs up

## Investigation procedure
1. Run ceph -s; identify health state and affected components
2. Check osd tree; identify down/out OSDs
3. Check pg stat; identify degraded/undersized PGs
4. Check mon stat; identify quorum status
5. Check logs for error messages

## Resolution
- Replace failed disk/OSD; wait for rebalance
- Restore MON quorum; replace failed MON
- Wait for rebalance to complete; tune backfill rate if needed
- Fix network partition between OSD nodes

## Verification
- ceph -s: HEALTH_OK; all OSDs up/in; PGs active+clean

## Prevention
- Monitor Ceph health; alert on HEALTH_ERR/WARN
- Monitor OSD health; alert on down/out
- Monitor capacity; alert at 70%/80%
- Monitor PG state; alert on degraded/undersized

## Related
- [Software-Defined Storage](../07-software-defined-storage/index.md)
- [SDS (7.6 Monitoring and Logging)](../07-software-defined-storage/7.6-monitoring-and-logging.md)
