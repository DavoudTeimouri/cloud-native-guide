# etcd Backup and Restore

etcd snapshots are **separate from Velero**. Velero does not back up etcd, and a cluster restore without an etcd snapshot restores workloads onto a control plane with no cluster state.

## A. Snapshot Procedures

### Snapshot cadence

etcd snapshots must be taken on a regular schedule independent of Velero. The etcd `snapshot save` command is a single-node, online, copy-on-write operation with minimal cluster impact.

```bash
# Take a tiled snapshot and save it with a date-stamped filename
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd/snapshot-$(date +%F).db
```

| Metric | Target | Method |
|---|---|---|
| Snapshot interval | Every 5 minutes | Cron job on control-plane nodes |
| WAL archival | Continuous | `etcdctl snapshot save` cadence |
| RPO | ≤ 1 min | Continuous WAL archiving |
| Snapshot retention on-node | 7 most recent | Local disk `/var/lib/etcd/` |
| Off-site copy frequency | Daily | Push from on-node to object storage |

### Off-site backup storage

Each etcd snapshot must be copied to off-site storage within the same cadence. A backup on the same cluster does not survive a full region loss.

#### Off-site copy

```bash
# Copy to object storage (e.g., Ceph RGW, S3, GCS)
gsutil cp /var/lib/etcd/snapshot-$(date +%F).db gs://etcd-backups/snapshot-$(date +%F).db

# Or with AWS CLI
aws s3 cp /var/lib/etcd/snapshot-$(date +%F).db s3://etcd-backups/snapshot-$(date +%F).db

# Or with mc (MinIO client)
mc cp /var/lib/etcd/snapshot-$(date +%F).db etcd-backups/snapshot-$(date +%F).db
```

#### Off-site storage layout

```
etcd-backups/
├── snapshot-2026-11-20.db
├── snapshot-2026-11-21.db
├── snapshot-2026-11-22.db
├── snapshot-2026-11-23.db
├── snapshot-2026-11-24.db
├── snapshot-2026-11-25.db
├── snapshot-2026-11-26.db
└── .hashes/          # SHA256 checksums, one per line matching filenames
```

#### Off-site retention policy

| Tier | Retention | Description |
|---|---|---|
| Rolling local | 7 days | 7 most recent snapshots per node |
| Archived off-site | 30 days | Copied from on-node to object storage |
| Long-term archive | 90 days | Copied to cold storage (Glacier/Deepfreeze) |
| Immutable / Compliance | Indefinite | Object-lock or WORM storage for compliance |

#### Off-site copy verification

After each copy, verify integrity:

```bash
# Generate SHA256 on source
sha256sum /var/lib/etcd/snapshot-$(date +%F).db > /tmp/snapshot-$(date +%F).sha256

# Verify on destination
gsutil hash -c gs://etcd-backups/snapshot-$(date +%F).db  # or aws s3api head-object --expected
```

### Backup verification

A snapshot is **useless until it has been verified**. Verify **before** you need it — ideally as part of a scheduled drill.

#### Check snapshot integrity

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot status /var/lib/etcd/snapshot-2026-11-25.db
```

**Expected output:**

```
snapshot 2026-11-25-rev12345
endpoint http://127.0.0.1:2379
revision 12345
version 3.5.5
cluster-id 1234567890
state latest
```

**All fields must be present and `state` must be `latest`.** If `state` is `truncated` or the command fails, the snapshot is corrupted and you must fall back to an older one.

#### Automated restore verification (scheduled drill)

1. Spin up a **throwaway control-plane node** (or use an existing offline node)
2. Restore the latest snapshot to its `/var/lib/etcd`
3. Start etcd and wait for it to reach `healthy` in `etcdctl endpoint health --cluster`
4. Run a **smoke query**: `kubectl get nodes` and `kubectl get pods -A` — etcd itself must be reachable
5. **Record the measured RTO** from snapshot save to verified healthy member
6. **Alert if the restore fails or exceeds the RTO budget** (30 min). A backup pipeline with no automated restore test is an incident waiting to happen.

#### Verification schedule

| Component | Frequency | Declared RPO | Declared RTO |
|---|---|---|---|
| etcd snapshot restore | Quarterly | 24 h | 1 h |
| Velero restore (K8s resources + PVs) | Quarterly | 24 h | 4 h |
| Ceph/RBD restore | Quarterly | 24 h | 4 h |
| Vault raft snapshot restore | Quarterly | 24 h | 1 h |
| Full site rebuild | Annually | 24 h | Depends on scope |

## B. Restore Procedure

Restore etcd from a stored snapshot when quorum is lost or the etcd cluster is otherwise unavailable. **Do not attempt partial writes** before quorum is restored.

### Prerequisites

- A valid snapshot file (.db) from §A that has been verified (`etcdctl snapshot status`)
- Access to a control-plane node with etcd running (or a new node to join)
- The same Kubernetes version and PKI material that was present when the snapshot was taken
- `etcdctl` available on the node (kubespray installs it alongside etcd)

### Restore steps

1. **Stop the etcd member on the target node** (if it is still running):

   ```bash
   kubectl -n kube-system stop etcd-<node>
   # Or via systemctl if etcd is a static pod managed outside kube-system:
   systemctl stop etcd
   ```

2. **Remove the existing etcd data directory** so the member starts fresh:

   ```bash
   rm -rf /var/lib/etcd/*
   ```

3. **Restore the snapshot into the data directory**:

   ```bash
   kubectl -n kube-system exec etcd-<node> -- etcdctl \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key \
     snapshot restore /var/lib/etcd/snapshot-2026-11-25.db \
     --data-dir /var/lib/etcd
   ```

4. **Start the etcd member**:

   ```bash
   kubectl -n kube-system start etcd-<node>
   # Or:
   systemctl start etcd
   ```

5. **Verify the member is healthy and joined to quorum**:

   ```bash
   kubectl -n kube-system exec etcd-<node> -- etcdctl \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key \
     member list
   kubectl -n kube-system exec etcd-<node> -- etcdctl \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key \
     endpoint health --cluster
   ```

6. **Update DNS/load-balancer** if the control-plane VIP points to the restored node, and confirm the API server is serving.

### Etcd restore with a new node (cluster expansion)

1. Deploy the new control-plane node with kubespray etcd role.
2. Place the snapshot file at `/var/lib/etcd/snapshot-*.db` on the new node.
3. Start etcd — it will automatically join the existing cluster if `initial-cluster` is configured.
4. Verify with `etcdctl member list` and `etcdctl endpoint health --cluster`.

## C. Quorum Recovery

etcd quorum is based on the total number of members configured. Losing more than `floor(N/2)` members in an N-member cluster loses quorum entirely.

### Quorum math

| Cluster size | Quorum needed | Members lost before quorum is lost |
|---|---|---|
| 3 nodes | 2 | 1 |
| 5 nodes | 3 | 2 |
| 7 nodes | 4 | 3 |

### Rebuilding quorum after a loss

1. **If at least the quorum number of original members are still running**, etcd continues operating normally — no restore needed. Just rebuild the lost member(s) following the "Etcd restore with a new node" steps in §B.

2. **If quorum is lost** (more than `floor(N/2)` members down), restore from the most recent **verified** snapshot onto a **new** control-plane node (or an online node after its data dir is cleared).

3. **Fencing the old primary**: if the old primary is still running but partitioned, ensure it cannot accept writes. With stacked etcd on control-plane nodes, the Kubernetes API server usually fences etcd automatically via the leadership lease, but explicitly check:

   ```bash
   etcdctl lease disconnect <lease-id>
   ```

   only under guidance from a DBRE or platform specialist.

4. **After the new member joins and etcd reports healthy quorum**, verify API server functionality:

   ```bash
   kubectl get nodes
   kubectl get pods -A
   ```

### Rollback

If the restored member introduces corruption or the wrong data set, you can **remove it from the cluster** and restore an older snapshot:

```bash
# Step 1: etcd member remove (on a remaining healthy member)
etcdctl member remove <member-id> --data-dir /var/lib/etcd

# Step 2: Restore an older snapshot onto the removed member's node
# Follow §B steps, pointing at the older .db file

# Step 3: Re-verify quorum
etcdctl member list
etcdctl endpoint health --cluster
```

## D. RPO / RTO Measurement

### Purpose and scope

Document how to measure actual Recovery Point Objective (RPO) and Recovery Time Objective (RTO) during backup drills, where to record results, and how to compare against declared targets.

### Definitions

| Term | Definition | How to measure |
|---|---|---|
| RPO | Maximum acceptable data loss (time) | Time between last successful backup and failure point |
| RTO | Maximum acceptable downtime (time) | Time from disaster declaration to verified service restoration |

### Measurement procedure

#### 1. Declare the drill

Record the drill start time, scenario, and declared targets:

| Field | Value |
|---|---|
| Drill ID | Unique identifier (e.g., DR-2026-11-26-01) |
| Scenario | e.g., "Single control-plane node lost", "etcd quorum lost", "Full site rebuild" |
| Declared RPO | From `lifecycle/backup/backup-and-dr.md` table |
| Declared RTO | From `lifecycle/backup/backup-and-dr.md` table |
| Declared by | Person authorizing the drill |
| Start time | ISO 8601 timestamp |

#### 2. Execute the recovery procedure

Follow the applicable runbook from `lifecycle/disaster-recovery/index.md`:

| Scenario | Runbook |
|---|---|
| Single control-plane node lost | `kubernetes/control-plane/index.md` §Backup |
| etcd quorum lost | `kubernetes/control-plane/index.md` §Backup |
| Management cluster lost | `lifecycle/disaster-recovery/management-cluster.md` |
| Application cluster lost | `lifecycle/disaster-recovery/application-cluster.md` |
| Vault lost or sealed | `secrets-management/vault/recovery/restore.md` |
| Storage cluster degraded | `storage/ceph/cephadm-deployment.md` §Recovery |
| Full site rebuild | `lifecycle/backup/backup-and-dr.md` §G |

#### 3. Record timestamps

| Event | Timestamp | Notes |
|---|---|---|
| Disaster declared | T0 | Start of the drill |
| Last successful backup | T1 | From backup logs/monitoring |
| Recovery started | T2 | First recovery command executed |
| Service restored | T3 | All health checks pass |
| Verification complete | T4 | Verified with test transactions |

#### 4. Calculate RPO and RTO

| Metric | Formula | Result |
|---|---|---|
| Actual RPO | T0 − T1 | Time since last successful backup |
| Actual RTO | T3 − T0 | Time from declaration to restoration |

#### 5. Compare against declared targets

| Metric | Declared | Actual | Met? |
|---|---|---|---|
| RPO | From backup-and-dr.md | Actual RPO | Yes/No |
| RTO | From backup-and-dr.md | Actual RTO | Yes/No |

#### 6. Record results

Append to `lifecycle/backup/backup-and-dr.md` §G (or a dedicated drill log):

```markdown
## Drill: DR-2026-11-26-01

| Field | Value |
|---|---|
| Scenario | etcd quorum lost |
| Declared RPO | 24 h |
| Declared RTO | 1 h |
| Actual RPO | 6 h |
| Actual RTO | 45 min |
| RPO met | Yes |
| RTO met | Yes |
| Issues | None |
| Next drill | 2026-12-26 |
```

### Drill cadence

| Component | Frequency | Declared RPO | Declared RTO |
|---|---|---|---|
| etcd snapshot restore | Quarterly | 24 h | 1 h |
| Velero restore (K8s resources + PVs) | Quarterly | 24 h | 4 h |
| Ceph/RBD restore | Quarterly | 24 h | 4 h |
| Vault raft snapshot restore | Quarterly | 24 h | 1 h |
| Full site rebuild | Annually | 24 h | Depends on scope |

### Evidence requirements

For each drill, retain:

1. Drill declaration record (scenario, targets, authorizer)
2. Recovery procedure logs (commands executed, output)
3. Timestamp records (T0-T4)
4. Comparison table (declared vs actual)
5. Issues found and corrective actions
6. Sign-off from the person who ran the drill

## E. Drill Procedures

### Daily integrity check (no-cluster-impact)

```bash
# Run on each control-plane node
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot status /var/lib/etcd/snapshot-$(date -1 day +%F).db > /tmp/daily-snapshot-status-$(date +%F).txt

# Check that all snapshots from the last 7 days have `state latest`
if grep -q "state latest" /tmp/daily-snapshot-status-*.txt; then
  echo "All daily snapshots valid"
else
  echo "WARNING: Some snapshots are truncated or corrupted"
  # Alert via existing on-call channel
fi
```

### Weekly restore drill (measured RTO)

1. **Select a snapshot** from 7 days ago (oldest still retained locally)
2. **Spin up a throwaway control-plane node** (or use an existing node in a disconnected state)
3. **Clear the data directory** on the throwaway node: `rm -rf /var/lib/etcd/*`
4. **Restore the snapshot**:

   ```bash
   kubectl -n kube-system exec etcd-<node> -- etcdctl \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key \
     snapshot restore /var/lib/etcd/snapshot-2026-11-19.db \
     --data-dir /var/lib/etcd
   ```

5. **Start etcd**: `kubectl -n kube-system start etcd-<node>`
6. **Wait for healthy quorum**:

   ```bash
   kubectl -n kube-system exec etcd-<node> -- etcdctl member list
   kubectl -n kube-system exec etcd-<node> -- etcdctl endpoint health --cluster
   ```

7. **Record the measured RTO** from snapshot save timestamp to `etcdctl endpoint health --cluster` returning healthy
8. **Run smoke verification**: `kubectl get nodes` and `kubectl get pods -A`
9. **Alert if RTO > 30 min** or restore fails — log the full output for post-drill review
10. **Reset the node** or snapshot it for future drills

### Monthly full-restore drill

1. Select a snapshot from 30 days ago
2. Restore to a **completely fresh** control-plane node (not a reused throwaway)
3. Verify the full API server is serving: `kubectl get nodes`, `kubectl get pods -A`, `kubectl get nodes -o wide`
4. Record RTO and compare against the 30-minute budget
5. If RTO exceeds budget, document the gap and plan infrastructure changes

### Cross-region restore drill (quarterly)

1. Select the most recent off-site snapshot
2. Provision a control-plane node in the disaster-recovery region
3. Copy the off-site snapshot to the DR node's local storage
4. Restore etcd from the snapshot
5. Verify API server functionality from the DR region
6. Test that workloads can start with reduced capacity (the goal is etcd recovery, not full app recovery)
7. Record RTO and verify it meets the target; document any gaps

### Drill reporting

After every restore drill, update this file with:

- Snapshot filename used
- Measured RTO (minutes:seconds)
- Success/failure status
- Any failures and root causes
- Actions to bring RTO within budget

Append to the drill log section at the bottom of this file.

## F. Drill Log (append after each drill)

```markdown
### DR-2026-11-26-01: etcd quorum lost

- **Snapshot used**: snapshot-2026-11-19.db
- **Measured RTO**: 12:34
- **Status**: Success
- **Failures**: None
- **Actions**: None
```
