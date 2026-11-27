# Backup and Recovery Troubleshooting

## Symptoms

- etcd snapshot fails
- Backup not created at expected time
- Restore fails: "snapshot not found" or "corrupt snapshot"
- PV backup fails (Velero/rook-ceph)
- Disaster recovery runbook steps fail

## Likely causes

- etcd not reachable for snapshot
- Backup storage (S3/NFS) not mounted or unreachable
- Snapshot corrupted or incomplete
- Velero not installed or misconfigured
- Rook-Ceph cluster unhealthy

## Diagnostic commands

```bash
# Check etcd snapshot
ls -la /var/lib/etcd/snapshot/
etcdctl snapshot status <snapshot.db>

# Check backup storage
aws s3 ls s3://<backup-bucket>/
# or
mount | grep <backup-mount>

# Check Velero
kubectl -n velero get pods
kubectl -n velero get backup
kubectl -n velero logs -l app=velero

# Check Rook-Ceph
kubectl -n rook-ceph get pods
kubectl -n rook-ceph get cephcluster
ceph health
ceph osd status

# Check backup schedule
kubectl -n velero get schedule
```

## Expected healthy state

- etcd snapshots: recent, valid, not corrupt
- Backup storage: reachable, writable
- Velero: Running, backups completing
- Rook-Ceph: HEALTH_OK
- Backup schedules: enabled, last backup recent

## Remediation

- Fix etcd connectivity for snapshots
- Fix backup storage connectivity/credentials
- Create new etcd snapshot if old one is corrupt
- Fix Velero configuration: `velero backup create <name>`
- Fix Rook-Ceph cluster: replace failed OSDs, rebalance

## Risks

- Restoring from corrupt snapshot causes data loss
- Overwriting current data with old backup loses recent changes
- Deleting old backups removes rollback options

## Verification

```bash
etcdctl snapshot status <snapshot.db>
kubectl -n velero get backup
kubectl -n rook-ceph get cephcluster
ceph health
ls -la /var/lib/etcd/snapshot/```
