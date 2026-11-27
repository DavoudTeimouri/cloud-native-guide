# OSD Replacement Procedure

## Overview

This procedure covers the replacement of a failed or failing ObjectStore Daemon (OSD) in a Rook-Ceph cluster. Follow these steps in order to replace an OSD with minimal disruption and ensure data integrity.

---

## A. OSD Failure Detection

| Signal | Check | Action |
|---|---|---|
| OSD out of cluster | `kubectl -n rook-ceph get pods` — look for `osd-<id>` pods with `CrashLoopBackOff` or `Error` | Confirm the OSD is unrecoverable before removal |
| OSD OSD report | `ceph osd tree` — note the OSD marked `out` or `down` | Record the OSD ID (`<id>`) for the remaining steps |
| OSD heartbeats | `ceph osd status` — verify the OSD is `down` and no heartbeat in the last `mon osd heartbeat interval` (default 10s) | If the OSD is only temporarily down, wait; otherwise proceed to removal |
| PG state | `ceph pg ls <pg-id>` — check for PGs stuck in `underscrub`, `backfill`, or `peering` | Resolve any stuck PGs before starting replacement to avoid cascading delays |

**Detection workflow:**

1. Identify the failing OSD ID from Kubernetes events or Ceph status.
2. Verify the OSD is truly `down` (not transient) with `ceph osd status`.
3. Record the OSD number for the removal step.

---

## B. OSD Removal

> **Warning:** Removing an OSD triggers data rebalancing. Ensure the cluster has sufficient capacity (at least `size + 1` OSDs) before proceeding.

```bash
# 1. Mark the OSD out (ceph will stop serving new writes to it)
ceph osd out <osd-id>

# 2. Confirm the OSD is out
ceph osd tree | grep "<osd-id>"

# 3. Remove the OSD completely (purges data, removes the OSD from the cluster map)
ceph osd remove <osd-id>

# 4. Confirm the OSD is removed from the tree
ceph osd tree
```

**Post-removal verification:**

- `ceph osd df` — confirm usable size has decreased by one OSD
- `ceph health` — should report `HEALTH_OK` or only `HEALTH_WARN` about rebalancing
- Check that no PGs are stuck in `uneven` distribution

---

## C. New OSD Provisioning

> **Requirements:** A new block device (or partition) of equal or greater capacity than the removed OSD must be available on a node that can join the Ceph cluster.

```bash
# 1. Label the node where the new OSD will run (optional, if using node-specific constraints)
kubectl label node <node-name> failure-domain.beta.kubernetes.io/zone=<zone>

# 2. Create the OSD — Rook operator will auto-detect the new device and create the OSD
#    Identify the new device path (e.g., /dev/sdb, /dev/sdc, etc.)
#    Apply the Ceph OSD via kubectl or the Rook API

# Using kubectl with a specific device:
kubectl -n rook-ceph create ceph-osd /dev/<device-path> \
  --device-size=<size-GB> \
  --label="osd-id=<new-osd-id>"

# Or via the Rook CR if the operator auto-assigns:
# The operator will provision the OSD and mark it as `in` automatically.

# 3. Confirm the new OSD is recognized
ceph osd tree

# 4. Confirm the OSD is `in` and `up`
ceph osd status
```

**If the operator does not auto-provision:**

- Ensure the node has the correct `ceph-osd` annotations and the device is raw/block (not partitioned).
- Restart the Rook operator if the OSD does not appear within 2 minutes.

---

## D. Data Rebalancing

After the new OSD is `in`, Ceph will automatically rebalance data across the cluster. Monitor this process.

```bash
# 1. Check rebalancing status
ceph pg ls_detail | grep -E "state.*rebalancing|state.*scrub|state.*backfill"

# 2. Monitor progress per PG
ceph pg stat

# 3. Track the rebalancing percentage
ceph tell osd.* state  # shows overall cluster state

# 4. Optional: pause/resume rebalancing if needed
ceph osd rebalance pause
ceph osd rebalance resume

# 5. Verify rebalancing completes
ceph pg ls_detail | grep -E "state.*active+clean"
```

**Recovery goals during rebalancing:**

- **RPO:** `<= 1 minute` — WAL archiving ensures point-in-time recovery; rebalancing does not affect point-in-time recovery.
- **RTO:** `<= 30 minutes` — measured from OSD removal to cluster `HEALTH_OK` with all PGs `active+clean`.

**If rebalancing stalls:**

- Check for disk full (`ceph osd df`), network issues, or PG stuck in `underscrub`.
- Use `ceph pg <pg-id> debug reclaim` or `ceph pg <pg-id> debug scrub` for diagnosis.
- If necessary, `ceph osd rebalance pause` and investigate, then resume.

---

## E. Verification of Cluster Health After Replacement

```bash
# 1. Overall cluster health
ceph health
# Expected: HEALTH_OK

# 2. OSD map completeness
ceph osd tree
# Expected: new OSD shows `in/up`, old OSD is gone

# 3. PG state — all should be active+clean
ceph pg stat
# Expected: X PGs, Y active+clean, 0 stuck

# 4. Data integrity — sample checks across RBD/CephFS/RGW
rbd info --cluster rook-ceph  # verify RBD pools
ceph fs status --cluster rook-ceph  # verify CephFS

# 5. OSD utilization — ensure no single OSD is overloaded
ceph osd df

# 6. Run a quick integrity check (optional but recommended)
ceph pg scrub  # or let the scrubs run on their schedule

# 7. Confirm the cluster report is clean after a stabilization window (5–10 min)
ceph health detail
# Expected: no warnings about missing OSDs, no PGs in recovery or backfill
```

**Post-verification checklist:**

- [ ] `ceph health` returns `HEALTH_OK`
- [ ] All PGs are `active+clean`
- [ ] No OSD shows `out` or `removing`
- [ ] Cluster `osd df` reflects the new OSD capacity
- [ ] No PGs in `underscrub`, `recovery`, or `backfill` after 10 minutes
- [ ] RBD pool, CephFS, and RGW services are functional (smoke test PVCs/RBDs)

---

## F. Rollback (if replacement fails)

If the new OSD cannot be brought `in/up` or rebalancing causes data loss:

1. `ceph osd rebalance pause` — stop further data movement.
2. If the new OSD was just created and is `out`, `ceph osd rm <new-osd-id>` to remove it.
3. Re-add the original OSD if the device is still available:
   - `ceph osd create /dev/<original-device>` — returns a new OSD ID.
   - `ceph osd in <osd-id>` to bring it back online.
4. `ceph osd tree` — verify the original OSD is back in the map.
5. Monitor `ceph health` until `HEALTH_OK`.

> **Note:** Rollback is fastest if the original OSD device was not securely wiped. If the device was physically removed, a full cluster rebalance from remaining OSDs will occur.

---

## G. Related Procedures

- [Backup & Recovery Strategy](../../storage/ceph/backup-recovery-procedure.md) — validated restore drills
- [Failover Topology](../../storage/ceph/failover-procedure.md) — automated failover with fencing
- [OSD Addition Without Replacement](../../storage/ceph/osd-addition-procedure.md) — adding a new OSD to grow capacity