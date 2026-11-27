# Backup & Recovery Procedure

## Purpose

Documented backup and recovery process for the Ceph cluster managed by Rook.

## RPO and RTO

- **RPO:** `<= 1 minute` — continuous WAL archiving enables point-in-time recovery.
- **RTO:** `<= 30 minutes` — measured from failure detection to cluster `HEALTH_OK` with data restored.

## Backup Strategy

- Continuous WAL/binlog archiving to a durable store.
- Periodic base backups (physical) for fast full restore.
- Cross-region copy for disaster recovery.

## Restore Verification

- Automated scheduled restore tests against a throwaway instance.
- Measured RTO recorded; alert if restore fails or exceeds the RTO budget.
- Integrity checks (row counts, checksums, smoke query set) performed after restore.

## Related Procedures

- [OSD Replacement Procedure](../rook-ceph/osd-replacement-procedure.md)
- [Failover Procedure](failover-procedure.md)
- [OSD Addition Procedure](osd-addition-procedure.md)