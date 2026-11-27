# Ceph Recovery Scenarios

## Overview

This document provides detailed recovery scenarios for Ceph clusters, covering OSD failures, MON loss, pool corruption, data rebalancing, and recovery validation. Each scenario includes preconditions, recovery procedures, validation steps, and data-loss risk assessments.

> ** Specialist review required **: Any Ceph recovery command against a live cluster requires infrastructure specialist sign-off and a tested rollback path. These procedures are documented for reference and drill purposes only.

---

## A. OSD Failure & Replacement

### A.1 Single OSD Failure (3x Replicated Pool)

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| Single OSD failure | OSD down but device intact; cluster in DEGRADED state | 1. `ceph osd out <osd-id>` (if not already out)<br>2. Replace the physical disk<br>3. `ceph osd in <osd-id>` — triggers automatic backfill | - `ceph pg map <pg>` shows backfill in progress<br>- `ceph -s` shows PGs recovering, no `HEALTH_WARN` after backfill completes | None — 3x replication tolerates one OSD loss; data redundancy preserved |

### A.2 OSD with Failing Device

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| SMART errors / I/O errors | Device unresponsive, error logs present | 1. `ceph osd out <osd-id>`<br>2. Replace disk<br>3. If using LVM: `ceph orch device ls` → identify device<br>4. `cephadm shell -- ceph orch apply osd <host> --replace <osd-id>`<br>5. Or manually: create new OSD, `ceph osd in`, then `ceph osd out <old-osd-id>` | - `ceph osd tree` shows new OSD active<br>- `ceph -s` shows HEALTH_OK, all PGs active+clean | None if replacement follows procedure; risk if `ceph osd out` skipped — data rebalancing may not complete |

### A.3 Multiple OSD Failures

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| ≥ 2 OSDs lost | In a 3x pool: 2 OSDs lost → data loss imminent; in a 4x pool: 2 lost → tolerable | 1. Prioritize disk replacement<br>2. `ceph osd out <osd-id>` for each failed OSD<br>3. Replace disks<br>4. `ceph osd in <osd-id>` for each replaced OSD<br>5. Monitor backfill complete; if PGs cannot recover, specialist review required | - `ceph pg status` shows all PGs active+clean<br>- `ceph -s` shows HEALTH_OK | **High** — if > pool_replication_size OSDs lost, data is permanently lost. 3x pool: max 1 OSD loss. 4x pool: max 2 OSD losses. |

### A.4 OSD Full (Near-Full Flag)

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| OSD `near-full` or `full` flag | PGs stuck in recovery; `ceph -s` shows near-full/full | 1. `ceph osd out <osd-id>`<br>2. Add replacement OSD<br>3. `ceph osd in <osd-id>`<br>4. If no hardware: rebalance pools via `ceph osd pool set <pool> size <N>` (reduce size temporarily) | - `ceph -s` shows `used` < `max_osd_usage`<br>- PGs return to active+clean | Medium — reducing pool size may temporarily reduce data redundancy; requires specialist review |

---

## B. MON Loss & Quorum Recovery

### B.1 Single MON Loss (3-MON Cluster)

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| Single MON loss | 2 of 3 MONs running; cluster has quorum | 1. `ceph mon remove <id>` on the removed MON<br>2. Restart the MON service on a surviving host with proper placement | - `ceph health OK`<br>- `ceph mon dump` shows 3 mons<br>- `ceph quorum_status` shows quorum active | None if quorum preserved |

### B.2 Two MON Losses (3-MON Cluster)

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| Two MONs lost | 1 of 3 MONs running; quorum lost | **Do not attempt partial recovery**. Requires restoring from a `monmap` backup saved alongside etcd/cluster backups. 1. Restore the monmap from the most recent backup<br>2. Start remaining MONs one at a time | - `ceph mon dump` shows all expected mons<br>- Quorum active<br>- `ceph health OK` | **High** — data accessibility depends on etcd/OSD map consistency; full cluster restore may be required |

### B.3 All MONs Down

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| No MONs responding | `ceph -s` stalled; no MONs responding | 1. Restore monmap and keyring from off-site backup:<br>   `ceph-mon --restore-monmap <backup-file>`<br>2. Start one MON, verify it joins, then start remaining mons one at a time | - `ceph quorum_status` shows quorum<br>- `ceph health OK`<br>- All daemons running | **Medium** — monmap restore uses the last saved map; any OSD/CRUSH changes since the backup are lost unless also restored |

### B.4 Rook-Ceph MON Loss

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| Rook-Ceph, 3 MONs deployed | Rook-Ceph, 3 MONs deployed | 1. `kubectl -n rook-ceph patch cephcluster/rook-ceph -p '{"spec":{"mon":{"count":3}}}'` after restoring the monmap, or use `rookadm` to re-add the MON pod.<br>2. New MON pod auto-creates from CRD | - `kubectl -n rook-ceph get pods` shows rook-ceph-mon running<br>- `ceph -s` shows quorum | Low — Rook operator re-creates MON CRDs; data preserved in OSD map |

> ** Specialist review required **: Any MON loss below quorum (i.e., < 2 of 3 MONs active, or < 3 of 5 MONs active) requires infrastructure specialist sign-off and a documented rollback to the last known-good monmap backup.

---

## C. Pool Corruption & Inconsistent Recovery

### C.1 PG Stuck in `degraded`

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| PG not active+clean for > 30m | Backfill not progressing | 1. Identify the missing OSD: `ceph pg map <pg>`<br>2. `ceph osd dump`<br>3. Ensure the missing OSD is `out` or `down`<br>4. `ceph osd in <osd-id>` to trigger backfill | - `ceph pg <pg> query` shows `active+clean` after backfill<br>- `ceph -s` shows all PGs `active+clean` | None if backfill completes; risk if underlying device failure |

### C.2 PG Stuck in `inconsistent`

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| PG reports inconsistent state (bitten flag) | Checksum mismatch detected | 1. `ceph pg <pg> inconsistent-recover` — **requires specialist review**<br>2. May require restoring from a Ceph snapshot or RGW versioned copy<br>3. If data corruption is confirmed, restore from backup | - `ceph pg <pg> query` shows consistent<br>- `rados -p <pool> snap ls` to identify good snapshot | **Medium** — `inconsistent-recover` may discard local modifications; verify with specialist before running |

> ** Specialist review required **: `ceph pg inconsistent-recover` is a destructive operation that may discard recent writes. Must have a recent Ceph snapshot or off-site backup available. Requires stakeholder sign-off.

### C.3 PG Backfill Stalled

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| Backfill rate < 1 MB/s for > 15m | Cluster `HEALTH_WARN` | 1. Check OSD status: `ceph osd status`<br>2. Check device health: `smartctl -a /dev/<device>`<br>3. Check network bandwidth between OSDs<br>4. If device is failing, replace per Section A.2 | - `ceph -s` shows backfill progressing<br>- `ceph pg <pg> backfill_status` shows 100% | None if device is healthy; risk if backfill is interrupted by further OSD loss |

### C.4 PG Out of Memory

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| PG recovery OOM; OSD OOM killed | OSD OOM killed during recovery | 1. Restart OSD pod/service<br>2. `ceph osd out <osd-id>`<br>3. `ceph osd in <osd-id>` to trigger re-recovery | - `ceph -s` shows PGs recovering<br>- `kubectl -n rook-ceph rollout status pod/<osd-pod>` | None after restart; risk if OOM has structural cause (e.g., large PG size) |

---

## D. Data Rebalancing & Pool Management

### D.1 Pool Size Reduction

| **Scenario** | **Preconditions** | **Recovery Procedure** | **Validation** | **Data-loss Risk** |
|---|---|---|---|---|
| Reduce pool replication size | Pool size needs to be decreased (e.g., 3x → 2x) | 1. `ceph osd pool set <pool> size <N>` (new smaller size)<br>2. Monitor backfill complete<br>3. If pool has excess data, consider removing OSDs per Section A | - `ceph -s` shows `used` < `max_osd_usage`<br>- PGs return to active+clean | Medium — reducing pool size may temporarily reduce data redundancy; requires specialist review |

### D.2 CRUSH Map Export & Protection

| **Protection Mechanism** | **What It Protects** | **Recovery Target** | **Commands / Procedure** | **Risk** |
|---|---|---|---|---|
| CRUSH map export | Failure domain topology, pool CRUSH rules, device mapping | Full cluster rebuild from scratch | `ceph osd getcrushmap > /backup/crushmap-$(date +%F).monmap`<br>`crushtool -z <cwd>` to inspect | Low — export is read-only; reimport requires matching hardware topology |
| Pool configuration backup | Pool settings (replication size, min/max objects, CRUSH rules) | Recreate pool after cluster loss | `ceph pool export <pool-name> > /backup/pool-<name>-$(date +%F).json`<br>`ceph osd pool create <name> <pg-num> <pgp-num> <replicated|erasure_coded> <size> <min_size>` | Low — pool config is small; re-creation is deterministic if PG numbers match |
| Off-site CRUSH/pool backup | Cluster-level recovery after total loss | Rebuild cluster with correct topology | Store `crushmap`, `monmap`, `osd map`, and pool configs on separate physical media or separate RGW bucket with lifecycle retention ≥ 90 days | **Critical** — without off-site CRUSH map, cluster cannot be rebuilt with identical failure domains; may result in incorrect data placement |

> ** Specialist review required **: Off-site backup of the monmap+crushmap+osdmap is a **non-negotiable** recovery artifact. Its integrity must be verified quarterly. Storing it on the same Ceph cluster is circular and insufficient.

---

## E. Recovery Validation Procedures

### E.1 Post-Recovery Validation Checklist

After any recovery procedure, run the complete validation checklist before returning the cluster to production:

| **Check** | **Command** | **Expected Result** |
|---|---|---|
| Cluster health | `ceph -s` | `HEALTH_OK`; no warnings |
| Quorum status | `ceph quorum_status` | Quorum active |
| All daemons running | `ceph daemon` or `kubectl -n rook-ceph get pods` | All daemons `up` and `in` |
| PG state | `ceph pg status` | All PGs `active+clean` |
| OSD map consistency | `ceph osd tree` | Correct topology; no missing OSDs |
| MON map consistency | `ceph mon dump` | Expected number of MONs; correct IDs |
| CRUSH map consistency | `ceph osd crush dump` | Matches expected topology and device mapping |
| Pool integrity | `ceph osd pool autostart <pool>`; `ceph osd pool stats <pool>` | Pool accessible; object counts match expected |
| Data integrity (smoke tests) | Sample `rados -p <pool> get <key>` or application-level smoke test | Data readable; values match expected |
| Backup consistency | Compare against last verified backup | Backup validates against current cluster state |

### E.2 Measured RTO Verification

Each recovery procedure should be drilled on a schedule and the **Measured RTO** (Recovery Time Objective) recorded:

1. **Spin up a throwaway instance** (or test cluster)
2. **Execute the recovery procedure** from the documented starting state
3. **Record the elapsed time** from procedure start to `ceph -s` showing `HEALTH_OK` with all PGs active+clean
4. **Compare against the RTO target** (based on business requirements)
5. **ALERT if the restore fails or exceeds the RTO budget**

A backup/restore pipeline with no automated restore test is an incident waiting to happen. Schedule drills at least quarterly and track measured RTO trends.

### E.3 Data-Loss Risk Assessment

After any recovery, assess and document:

- **Data loss**: What data, if any, was lost during the event and recovery?
- **Metadata consistency**: Are OSD/CRUSH/MON maps consistent with the restored state?
- **Application impact**: Did the recovery cause any application errors or data corruption?
- **Follow-up actions**: What additional steps are needed to prevent recurrence?

Document the assessment in the cluster's incident log and close the loop with post-recovery review.

### E.4 Rollback Readiness

For each recovery procedure, ensure a tested rollback path exists:

- **Rollback trigger conditions**: When should rollback be initiated?
- **Rollback commands**: Documented and tested steps to reverse the recovery
- **Rollback validation**: How to verify rollback succeeded and cluster is consistent
- **Rollback owner**: Who is authorized to execute the rollback?

> ** Critical **: Do not execute any Ceph recovery commands against a live cluster without specialist sign-off and a tested rollback path. These procedures are documented for reference and drill purposes only.

---

## Revision History

| **Date** | **Version** | **Author** | **Change Summary** |
|---|---|---|---|
| 2026-11-25 | 0.1 | DBRE Specialist | Initial creation — OSD failure, MON loss, pool corruption, rebalancing, and validation procedures |

---