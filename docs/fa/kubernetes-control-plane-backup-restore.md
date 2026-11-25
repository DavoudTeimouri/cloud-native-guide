# K8S-CONTROL-PLANE-BACKUP-RESTORE

*مثالی است — هیچ polymerization به یک Cluster زنده اعمال نمی‌شود.*

## K8S-CONTROL-PLANE-BACKUP-RESTORE-1. etcd snapshot strategy

- snapshot هر ۴–۶ ساعت + pre-change trigger.
- `etcdctl snapshot save` برای point-in-time quiesced snapshot.
- integrity: `etcdctl snapshot status`.
- encryption و secure storage.
- retention و off-cluster/off-site copies.
- K8s PKI و certificate recovery.

## K8S-CONTROL-PLANE-BACKUP-RESTORE-2. Recovery ordering

 stop etcd → clear data → restore from snapshot → start etcd → join nodes → restart control-plane components.

## K8S-CONTROL-PLANE-BACKUP-RESTORE-3. Commands illustrative

```bash
# snapshot status
etcdctl snapshot status /backup/etcd-snapshot.db --write-out=table
# restore
etcdctl snapshot restore /backup/etcd-snapshot.db --data-dir=/var/lib/etcd-restore
```

## K8S-CONTROL-PLANE-BACKUP-RESTORE-4. Warnings

 restoration etcd به existing/partially recovered cluster بدون clear کردن data-dir خطرناک است — mixed data باعث inconsistency و split-brain می‌شود.
 هیچ polymerization به یک Cluster زنده انجام ندهید.

---

*SND 004-P11.5 — K8S-CONTROL-PLANE-BACKUP-RESTORE (illustrative)*
