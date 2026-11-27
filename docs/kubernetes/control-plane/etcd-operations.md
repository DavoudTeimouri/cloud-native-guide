# etcd Operations

## A. Purpose and scope

Document etcd operational procedures for production Kubernetes clusters: backup, restore, snapshot management, compaction, defragmentation, and member management. etcd stores all Kubernetes cluster state. Operational proficiency with etcd is essential for reliability and recovery.

Cross-references `kubernetes/control-plane/index.md` §Backup, `kubernetes/control-plane/etcd-backup.md` §Backup procedure, `kubernetes/control-plane/etcd-restore.md` §Restore procedure, `lifecycle/backup/backup-and-dr.md` §etcd.

## B. Snapshot management

### 1. Etcd snapshot workflow

Take snapshots regularly. The backup procedure (`etcd-backup.md`) defines frequency and retention, but the operational snapshot commands are documented here.

**Take a snapshot on one etcd member (control-plane node):**

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd/snapshot-$(date +%F-%H%M).db
```

**Verify a snapshot:**

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  snapshot status /var/lib/etcd/snapshot-$(date +%F-%H%M).db \
  --write-out=table
```

Expected output shows `health: "true"`.

### 2. Snapshot retention

- Keep at least 7 daily snapshots
- Keep 4 weekly snapshots (Sundays)
- Keep 1 monthly snapshot (1st of month)
- Rotate and prune old snapshots per the retention policy in `lifecycle/backup/backup-and-dr.md`

**Prune old snapshots:**

```bash
# Keep 7 daily snapshots
ls -t /backups/etcd/*.db | tail -n +8 | xargs rm

# Keep 4 weekly snapshots (Sundays)
# Keep 1 monthly snapshot (1st of month)
```

## C. Compaction

### 1. Why compaction matters

etcd retains all revision history in the WAL (Write-Ahead Log). Without compaction, the WAL grows unboundedly, consuming disk space and degrading performance. Compaction prunes the WAL up to a specified revision.

### 2. Trigger compaction after snapshot

Always compaction after taking a snapshot to keep the WAL small:

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  compaction <revision>
```

Use the latest snapshot revision or a known good revision:

```bash
# After snapshot, get the revision from snapshot status output
# Then compact up to that revision
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  compaction $(etcdctl snapshot status /var/lib/etcd/snapshot-$(date +%F-%H%M).db \
    --write-out=json | python3 -c "import sys,json; print(json.load(sys.stdin)['revision'])")
```

### 3. Compaction best practices

- Run compaction after every snapshot
- Do not compact to revisions that lose needed history
- Monitor disk usage of the WAL directory (`/var/lib/etcd/member/wal/`)
- If disk is filling up, compaction is behind — increase snapshot frequency

## D. Defragmentation

### 1. Why defragmentation matters

Compaction frees logical space in the WAL, but the physical database file may still be sparse or bloated. Defragmentation rewrites the database, reclaiming physical disk space and improving performance.

### 2. Defragmentation workflow

Run defragmentation during a maintenance window when etcd is healthy and under low load:

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  defrag
```

### 3. Defragmentation best practices

- Run on one member at a time
- Do NOT run during a snapshot or compaction
- Monitor disk space before and after
- After defragmentation, verify member health:

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster
```

- Verify member list:

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list
```

### 4. Automated defragmentation

Consider scheduling defragmentation weekly or monthly as part of routine toil reduction, especially for clusters with high write throughput.

## E. Member management

### 1. Add a member

```bash
etcdctl member add <member-name> \
  --peer-urls=https://<member-ip>:2380 \
  --member-zone=<zone> \
  --member-site=<site> \
  --member-role=learner \
  --initial-advertise-peer-urls=https://<member-ip>:2380
```

Verify:

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list
```

### 2. Remove a member

**Step 1:** Remove the member from the cluster:

```bash
etcdctl member remove <member-id>
```

**Step 2:** Remove the etcd static pod manifest from the node (if applicable):

```bash
rm /etc/kubernetes/manifests/etcd.yaml
# Wait for the pod to terminate
sleep 30
```

**Step 3:** Rejoin the cluster (if using Kubespray inventory update):

```bash
# Update the inventory to exclude the removed member
# Re-run Kubespray to redeploy etcd without the member
```

Verify quorum after removal:

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster
```

### 3. Move a member to a new node

1. Add the new node as an etcd member
2. Remove the old member
3. Verify the cluster operates with the new member before deleting the old node

### 4. Member list verification

Regularly verify the member count matches the control-plane inventory:

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list
```

A member count shorter than the inventory indicates a lost member that must be replaced before the next failure.

## F. Cross-references

- `kubernetes/control-plane/index.md` — Control plane and etcd overview
- `kubernetes/control-plane/etcd-backup.md` — Snapshot and backup procedure
- `kubernetes/control-plane/etcd-restore.md` — Restore procedure
- `lifecycle/backup/backup-and-dr.md` — Backup policy, RPO/RTO, retention
- `lifecycle/disaster-recovery/index.md` — etcd quorum lost recovery
- `architecture/03-failure-domains.md` — Control-plane node placement
