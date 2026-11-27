# STATEFUL-WORKLOAD-BACKUP-RESTORE

*مثالی است.*

## STATEFUL-WORKLOAD-BACKUP-RESTORE-1. Velero

 معماری Velero (server، agent، Restic CSI، BSL). object backups K8s، CSI snapshot، app-consistent backup، DB-native vs volume snapshot.

## STATEFUL-WORKLOAD-BACKUP-RESTORE-2. distinctions

 manifest backup ≠ data backup.
 volume snapshot ≠ app-consistent backup.
 replication ≠ backup.
 restoring objects ≠ recoverable app data.

## STATEFUL-WORKLOAD-BACKUP-RESTORE-3. Redis example

 persistence RDB/AOF، backup، recovery، validation.

## STATEFUL-WORKLOAD-BACKUP-RESTORE-4. PVC/PV recovery

 restore ordering، dependency handling، namespace/app-level recovery.

---

*SND 004-P11.5 — STATEFUL-WORKLOAD-BACKUP-RESTORE (illustrative)*
