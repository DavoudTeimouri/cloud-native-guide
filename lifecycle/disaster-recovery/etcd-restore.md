# etcd Restore Procedure

## A. Backup

etcd snapshots are **separate from Velero**. Velero does not back up etcd, and a cluster restore without an etcd snapshot restores workloads onto a control plane with no cluster state.

### Snapshot cadence

```bash
# Take a tiled snapshot and save it with a date-stamped filename
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd/snapshot-$(date +%F).db
```

### Off-site copy

```bash
# Copy the snapshot off the node to object storage (e.g., Ceph RGW, S3)
gsutil cp /var/lib/etcd/snapshot-$(date +%F).db gs://etcd-backups/snapshot-$(date +%F).db
# Or with AWS CLI
aws s3 cp /var/lib/etcd/snapshot-$(date +%F).db s3://etcd-backups/snapshot-$(date +%F).db
```

### Retention policy

| Metric | Target | Method |
|---|---|---|
| RPO | ≤ 1 min | Continuous WAL archiving via `etcdctl snapshot save` cadence |
| RTO | ≤ 30 min | Measured by actual restore drill (see §C) |
| Retention | 7 days rolling + 30 days archived | Rotate snapshots off-node daily; keep 7 local, rest off-site |

---

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

If adding a node rather than recovering a lost one:

1. Deploy the new control-plane node with kubespray etcd role.
2. Place the snapshot file at `/var/lib/etcd/snapshot-*.db` on the new node.
3. Start etcd — it will automatically join the existing cluster if `initial-cluster` is configured.
4. Verify with `etcdctl member list` and `etcdctl endpoint health --cluster`.

---

## C. Snapshot Verification

A snapshot is useless until it has been verified. Verify **before** you need it — ideally as part of a scheduled drill.

### Check snapshot integrity

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot status /var/lib/etcd/snapshot-2026-11-25.db
```

Expected output:

```
snapshot 2026-11-25-rev12345
endpoint http://127.0.0.1:2379
revision 12345
version 3.5.5
cluster-id 1234567890
state latest
atom compaction index 12300
```

**All fields must be present and `state` must be `latest`.** If `state` is `truncated` or the command fails, the snapshot is corrupted and you must fall back to an older one.

### Automated restore verification (scheduled drill)

1. Spin up a **throwaway control-plane node** (or use an existing offline node).
2. Restore the latest snapshot to its `/var/lib/etcd`.
3. Start etcd and wait for it to reach `healthy` in `etcdctl endpoint health --cluster`.
4. Run a **smoke query**: `kubectl get nodes` and `kubectl get pods -A` — they should fail or show reduced state because the node is isolated, but etcd itself must be reachable.
5. **Record the measured RTO** from snapshot save to verified healthy member.
6. **Alert if the restore fails or exceeds the RTO budget** (30 min). A backup pipeline with no automated restore test is an incident waiting to happen.

---

## D. Quorum Recovery

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

---

## E. Cross-references

- `kubernetes/control-plane/index.md` — etcd backup, validation, and failure scenarios
- `lifecycle/backup/backup-and-dr.md` — backup policy, RPO/RTO, Velero (note: Velero does not cover etcd)
- `architecture/03-failure-domains.md` — control-plane failure domain distribution
- `decisions/ADR-0002-*` and `decisions/ADR-0003-*` — etcd cluster sizing and placement decisions
- `storage/ceph/cephadm-deployment.md` — off-site backup storage configuration
