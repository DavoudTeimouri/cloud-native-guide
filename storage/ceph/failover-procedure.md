# Failover Procedure

## Purpose

Documented automated failover process for the Ceph cluster managed by Rook.

## Failover Topology

- **Primary:** The write-active OSD node.
- **Sync Replicas:** Replicas that acknowledge writes before ACK to the app (quorum-based, no data loss on failover).
- **Async Replicas:** Read-scaling only; NOT a failover target when lagging.
- **Cross-Region Replica:** DR target; survives a full region loss.

## Automated Failover

- Health checks + consensus decide the primary is gone (avoid split-brain via quorum/fencing).
- Promote the MOST CURRENT sync replica (never a lagging async one).
- Repoint the app through a stable endpoint (VIP / service discovery / proxy).
- Fence the old primary so it can't accept writes and split-brain.

## Drill Requirements

- Failover drilled on a schedule until it is a non-event.
- Record measured RTO; verify no data loss or split-brain after drill.
- Document runbook from what actually happened during the drill.

## Related Procedures

- [Backup & Recovery Procedure](backup-recovery-procedure.md)
- [OSD Replacement Procedure](../rook-ceph/osd-replacement-procedure.md)
- [OSD Addition Procedure](osd-addition-procedure.md)