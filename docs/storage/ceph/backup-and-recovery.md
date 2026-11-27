# Ceph Backup and Recovery

## Snapshot Strategies

Ceph provides **cluster‑aware snapshots** that capture the state of a pool or the whole cluster at a point in time. Snapshots are copy‑on‑write, inexpensive to create, and can be used as the foundation for backups, rollbacks, or disaster‑recovery drills.

| Aspect | Recommendation |
|--------|----------------|
| **Scope** | Snap individual pools (`ceph osd pool snapshot <pool> <name>`) or the entire cluster (`ceph snapshot create <name>`). |
| **Frequency** | Align with your RPO. For critical workloads, create snapshots every 5‑15 minutes; for less critical, hourly or daily. |
| **Retention** | Use a lifecycle script that retains the last N snapshots and prunes older ones (`ceph osd pool snapshot <pool> rm <name>`). |
| **Automation** | Deploy a cron job or operator that snapshots pools, pushes the snapshot metadata to an external object store (e.g., Ceph RGW) for long‑term retention. |
| **Verification** | After each snapshot, run `ceph osd snapshot ls <pool> <name>` and confirm the `size_max` and `size_used` values are as expected. |

### Example: Automated weekly snapshot script (bash)

```bash
#!/usr/bin/env bash
POOLS="data metadata logs"
for POOL in $POOLS; do
  NAME="$(date +%Y%m%d-%H%M%S)"
  ceph osd pool snapshot "$POOL" "$NAME"
  # Optional: upload to RGW for off‑cluster retention
  # rclone copy ceph://$POOL/. s3://backups/ceph/$POOL/$NAME \
    --include "*.json" --fast-list
done
```

## OSD Replacement

When an OSD fails or reaches end‑of‑life, Ceph’s self‑healing mechanism replaces it with minimal disruption.

1. **Mark the OSD out** – `ceph osd out <osd_id>` (or use the dashboard/CRUSH map edit).
2. **Remove the OSD** – `ceph osd purge <osd_id> --yw` (the `--yw` flag waits for the OSD to become inactive).
3. **Add the new OSD** – physically install, enable, and join it to the cluster (`ceph osd create <id>` then `ceph osd crush add‑osd <new_id> <host> <device>`).
4. **Re‑balance** – Ceph will automatically re‑assign placement groups; monitor with `ceph pg stat` and `ceph pg <pg_id> query`.
5. **Verify health** – `ceph health detail` should show no `PEMBALANCE` or `UNAVAIL` warnings after the re‑balance completes.

### Checklist

- [ ] OSD is marked out and drained.
- [ ] New OSD appears in `ceph osd tree`.
- [ ] PGs are re‑distributed evenly (`ceph pg stat` shows balanced).
- [ ] No `recoveries` or `activating` PGs remain after 2× the normal PG activation time.

## Pool Recovery

Recovering a pool may be needed after accidental deletion, corruption, or a catastrophic OSD loss. Ceph’s pool recovery leverages existing PG data and, if needed, snapshots.

### Steps

1. **Identify the missing pool** – `ceph osd pool ls`.
2. **Create an empty pool with the same type** – `ceph osd pool create <pool> <pg_num> <type>` (e.g., `replicated` or `erasure_coded`).
3. **Restore from snapshot (if available)** –
   ```bash
   ceph osd pool snapshot <pool> <name>
   rbd export‑snapshot <pool>/<obj> <snapshot> <dest>   # for RBD pools
   ```
   Or use `ceph osd pool set <pool> snapshot <name> restore` to point the new pool at the snapshot’s data.
4. **Verify data integrity** – run `ceph tell pool/<pool> injectfiles` or compare checksums.
5. **Re‑balance** – ensure the pool’s PGs are fully recovered (`ceph pg stat` shows `active+clean`).

### When snapshots are not available

- Use **CRUSH map** adjustments to recover from an OSD failure; Ceph will rebuild from remaining replicas.
- For erasure‑coded pools, Ceff can rebuild using XOR parity; monitor `ceph osd pool meta <pool>` for `erasure_code_profile`.

## Disaster Recovery (DR) Procedures

DR in Ceph typically means recovering from a full site loss or a prolonged cluster outage. The primary mechanisms are **cross‑cluster replication** and **snapshot‑based restoration**.

### 1. Cross‑cluster RGW replication (recommended for RPO ≤ 1 min)

- Configure **Ceph RGW bucket replication** to a remote cluster (`ceph rbd mirror pool target` or RGW replication rules).
- Periodically verify the remote replica (`ceph rbd mirror status <pool>/<obj>`).
- Failover procedure:
  1. Promote the remote cluster as the primary (`ceph rbd mirror promote <pool>/<obj>`).
  2. Update DNS / endpoint to point to the restored cluster.
  3. Re‑establish replication in the opposite direction once the original site is repaired.

### 2. Snapshot‑based restoration (RPO depends on snapshot frequency)

- Ensure a recent snapshot exists (`ceph osd pool snapshot ls <pool>`).
- Create a new pool from the snapshot:
  ```bash
  ceph osd pool clone <pool>@<name> <new_pool>
  ```
- Migrate applications to use `<new_pool>`.
- Verify application data and application‑level consistency (database dumps, log checks, etc.).

### 3. Full cluster restart after loss

- Re‑install failed nodes, add new OSDs, and allow the cluster to recover (`ceph health` → `HEALTH_OK`).
- Once the cluster is healthy, restore any missing pools from the most recent cross‑cluster snapshot or external backup.

### DR Run‑book checklist

- [ ] Snapshot taken < RPO ago.
- [ ] Remote replica verified healthy.
- [ ] Failover test performed in a staging environment.
- [ ] DNS / client config updated and validated.
- [ ] Post‑failover data consistency checks passed.
- [ ] Original cluster re‑integrated and re‑synced.

## Validation Steps

Regular validation ensures that snapshots, OSD replacements, and DR procedures actually work. Include these checks in your SRE routine.

| Validation | Command / Action | Expected Outcome |
|------------|------------------|------------------|
| **Snapshot list** | `ceph osd pool snapshot <pool> ls` | Lists all snapshots with timestamps; no errors. |
| **Snapshot integrity** | `ceph osd snapshot ls <pool> <name> --format json` | JSON includes `size_used`, `size_max`; values match pool usage. |
| **OSD health** | `ceph health detail` | No `INACTIVE`, `UNDER‑REPLICATED`, or `PEMBALANCING` warnings. |
| **PG consistency** | `ceph pg stat` | All PGs `active+clean`, recovery count = 0. |
| **Pool recreation from snapshot** | `ceph osd pool clone <pool>@<name> <new_pool>` then `rbd ls <new_pool>` | New pool contains the same objects as the snapshot. |
| **RGW replication status** | `ceph rbd mirror status <pool>/<obj>` (or RGW `ceph rgw replication ls`) | Remote mirror is `synced` or `up‑to‑date`. |
| **DR drill – promote remote** | Promote remote cluster, switch client endpoint, run application smoke test | Application functions without data loss; RPO/RTO met. |
| **Checksum verification** (optional) | `ceph osd calc check <pool> <object>` | Matches stored checksum; no silent corruption. |

### Automated validation pipeline (example cron)

```cron
0 * * * * /usr/local/bin/ceph-snapshot-validate.sh >> /var/log/ceph/validate.log 2>&1
0 3 * * 0 /usr/local/bin/ceph-dr-drill.sh >> /var/log/ceph/dr-drill.log 2>&1
```

The scripts should exit non‑zero and send an alert (e.g., PagerDuty, Slack) if any check fails, ensuring that a broken backup or unrehearsed failover is caught long before an incident.

---

*This document is intended to be kept under version control alongside the rest of the cloud‑native guide. Update it whenever Ceph version, topology, or RPO/RTO targets change.*
