# Section 12: Backup Validation & Recovery Drills

## Repeatable Test Program

A backup job that completes successfully does not guarantee recoverability. A repeatable test program verifies that backups can actually be restored and that the application data is intact.

### Test Program Phases

| Phase | Description | Success Criteria |
|---|---|---|
| **Job success verification** | Backup job completes without errors; status is `completed` or `ready`. | `velero backup get` shows `STATUS=Completed`; etcd snapshot `snapshot status` passes. |
| **Integrity verification** | Snapshot metadata and data blocks are intact; no corruption. | `etcdctl snapshot status` returns valid MOD-REV, INDEX, DB SIZE. Volume snapshot checksum matches expected. |
| **Restore into isolated env** | Restore is performed into a separate namespace/cluster, not production. | Restored resources are in a dedicated test namespace; original production remains untouched. |
| **App-level consistency checks** | Application-specific data is validated after restore. | Row counts match; checksums verified; smoke queries return expected values. |
| **Timing measurement** | Actual RTO is measured from snapshot start to validated restore. | RTO recorded; compared against target (e.g., RTO <= 30 min). |
| **Data loss measurement** | Amount of data lost (if any) is quantified against RPO. | Data loss = 0 if RPO <= target; otherwise, quantify and report. |
| **Periodic drills** | Test program runs on a scheduled cadence. | Drill frequency met (e.g., quarterly for app restore, annually for full DR). |
| **Evidence / audit records** | Every drill produces a written record. | Drill report stored in documentation; remediation items tracked to closure. |
| **Remediation tracking** | Failures or gaps found in drills are tracked and closed. | All open remediation items from prior drills are resolved before next drill. |

### Do NOT Assert Backup Valid Just Because Job Succeeded

A `velero backup get` status of `Completed` only means the backup artifacts were uploaded to object storage. It does not mean:
- The etcd snapshot is restorable.
- The volume snapshots are app-consistent.
- The application data is intact after restore.
- The RTO/RPO targets are met.

Always perform the full test program before marking a backup as valid.

## Test Matrix

| Component | Backup Mechanism | Frequency | Retention | Restore Test | Validation Criteria | Dependencies |
|---|---|---|---|---|---|---|
| **etcd** | `etcdctl snapshot save` | Every 4–6h + pre-change | 72h on-site / 30d off-site | Restore from latest + oldest retained snapshot | `etcdctl snapshot status` passes; cluster joins; `kubectl get nodes` Ready | etcdctl version matches etcd major version; sufficient disk space in /var/lib/etcd |
| **K8s objects** | Velero manifest backup | Daily (schedule) | 30d | Restore to isolated namespace; `kubectl get all -A` succeeds | All expected objects present; no crashloop pods; RBAC grants access | Velero server reachable; backup storage accessible |
| **PVC / volumes** | CSI snapshot (driver-dependent) | Daily + pre-change | 72h on-site / 30d off-site | Restore PVC to new cluster/namespace; application starts | PVC bound; filesystem mounts; app data matches pre-snapshot checksum | CSI driver supports snapshot; snapshot API available in storage class |
| **Database (PostgreSQL)** | `pg_dump` + WAL archival | Daily dump; continuous WAL | 30d dumps / 72h WAL | Restore dump into fresh DB; run smoke queries | Row counts match; data checksums verify; no missing WAL segments | PostgreSQL backup recovery model = full; WAL files archived to object storage |
| **Database (MySQL/Percona)** | `mysqldump` + binary log | Daily dump; continuous binlog | 30d dumps / 72h binlog | Restore dump into fresh instance; verify data integrity | Row counts match; primary key checksums; stored procedures functional | MySQL binary log enabled; archive log path writable |
| **Redis** | RDB file + Velero volume snapshot | Pre-RDB save + daily Velero | 30d RDB / 72h Velero | Restart Redis from restored RDB; KEYS * matches | Key space count matches; GET for known keys returns expected values | Redis `save` or `bgfsave` completed; RDB file not corrupted |
| **Ceph RGW / object store** | Ceph snapshot + replication | Daily | 30d | Restore bucket from snapshot; upload/download test | Object count matches; checksum of sample objects verified | Ceph cluster quorum available; snapshot supported by RGW |

### Test Matrix — Dependency Notes

- **etcd → All K8s components**: etcd backup must complete before any cluster-level restore. Without a valid etcd snapshot, cluster state is ambiguous.
- **API server → Velero server**: Velero backup/restore operations require the Kubernetes API server to be running. If the control plane is down, Velero cannot be invoked until the API server is restored (via etcd restore first).
- **CSI driver → Storage class**: Volume snapshots require a storage class with snapshot support. Without the correct SC, `velero backup create` will skip or fail on PVCs.
- **Database archival → WAL retention**: DB dumps are only valid if WAL/archive logs are retained for point-in-time recovery. Without archived WAL, the backup is a consistent point-in-time snapshot only, not PITR.

## Periodic Drill Program

### Drill Cadence

| Drill Type | Frequency | Scope | Success Threshold |
|---|---|---|---|
| ** etcd restore drill** | Every 6 months | Restore etcd from snapshot into isolated environment; verify cluster state. | RTO <= target (e.g., 30 min); etcd health green; kubectl access restored. |
| **App-level restore drill** | Quarterly | Restore K8s objects + volume snapshots into test namespace; run app smoke tests. | All services start; data consistency checks pass; RTO measured. |
| **Full DR drill** | Annually | Complete cluster loss: provision new cluster, install Velero/etcd, restore from backups. | Cluster operational; all namespaces and apps restored; RTO/RPO met. |
| **Database PITR drill** | Annually | Restore DB dump to target timestamp; verify data up to that point. | RPO met; data loss = 0; application functional. |

### Drill Execution Flow

1. **Schedule the drill** in advance — communicate to all stakeholders (on-call, SRE, app teams).
2. **Snapshot the current state** (optional): take a pre-drill etcd snapshot in case the drill needs to be rolled back.
3. **Execute the restore** following the documented procedure for the component.
4. **Run validation checks** from the test matrix (job success, integrity, app-level consistency).
5. **Measure and record RTO** (from snapshot start to validated restore) and RPO (data loss quantified).
6. **Document findings**: what worked, what failed, what surprised you.
7. **Create remediation items** for every failure or gap. Track to closure before the next drill.
8. **Update runbooks** based on what the drill revealed.

### Evidence & Audit Records

After each drill, store the following evidence:

- Drill date and duration (RTO measured).
- Backup snapshot used (name, timestamp, integrity check result).
- Restoration commands output (trimmed to relevant sections).
- Validation results (checks passed/failed, smoke query results).
- Data loss measurement (RPO result).
- Remediation items created (IDs, descriptions, owners, due dates).
- Runbook updates made.

Keep these records in a persistent location (documentation repo, Confluence, or similar). They are the source for trend analysis and compliance audits.

### Remediation Tracking

| Field | Description |
|---|---|
| **ID** | Unique identifier for the remediation item (e.g., `REM-2026-11-23-001`). |
| **Description** | What failed or what gap was found. |
| **Root Cause** | Why it failed (e.g., "snapshot compression failed", "CSI driver version mismatch", "etcd snapshot corrupt"). |
| **Owner** | Team or individual responsible for fixing. |
| **Due Date** | When the fix must be completed by. |
| **Status** | Open, In Progress, Resolved, Verified. |
| **Verification** | How the fix was verified (e.g., "ran etcd restore drill after fix, RTO met"). |

> **Close the loop**: No remediation item from a drill should remain open across two consecutive drills of the same type. If a problem cannot be fixed before the next drill, document the risk acceptance and schedule a fix timeline.

## Validation Criteria Checklist

Use this checklist after every restore test. If any item fails, the backup is not valid and remediation is required.

### etcd Restore Validation

- [ ] `etcdctl snapshot status <snapshot>.db` returns valid MOD-REV, INDEX, DB SIZE.
- [ ] `ETCDCTL_API=3 etcdctl endpoint health --cluster` returns all members healthy.
- [ ] `kubectl get nodes` returns all nodes Ready.
- [ ] API server responds to `kubectl get all -A`.
- [ ] etcd member list shows only expected members (no stale members).
- [ ] RTO measured from snapshot start to validated restore <= target.

### Application Restore Validation

- [ ] All expected K8s objects created (deployments, services, ConfigMaps, etc.).
- [ ] No pods in `CrashLoopBackOff` or `Error` state.
- [ ] Application-specific data checks pass (row counts, checksums, smoke queries).
- [ ] PVCs are bound and filesystems mounted.
- [ ] Service ports are accessible (internal or external as applicable).
- [ ] RTO measured from snapshot start to validated restore <= target.

### Data Loss Verification

- [ ] Compare pre-snapshot data state (if available) with post-restore state.
- [ ] Quantify any missing data; report RPO compliance.
- [ ] If data loss > 0, file an incident and record in the drill evidence.

---
*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*