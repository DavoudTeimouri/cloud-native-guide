# 11 · Backup Verification & Recovery Testing

## Purpose and scope
Backup verification, recovery testing, Velero restore drills, etcd snapshot restore.

## Steps
1. Schedule regular restore drills (monthly application, quarterly full environment)
2. Restore Velero backup into scratch namespace
3. Restore etcd snapshot onto control-plane node
4. Verify data integrity and application functionality
5. Record RTO/RPO; compare against targets

## Implementation
```bash
# Velero restore drill
velero restore create <restore> --from-backup <backup>
velero restore get <restore>
kubectl get pods -n <restored-namespace>

# etcd snapshot restore
etcdctl snapshot restore /var/lib/etcd/snapshot-<date>.db \
  --data-dir /var/lib/etcd-new
# Verify on new control-plane node
etcdctl endpoint health --cluster \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt
```

## Validation
- Restored pods Running; data intact
- etcd healthy after snapshot restore
- RTO/RPO measured and recorded; within targets

## Related
- [06 · Kubernetes Infrastructure (6.17 Validation and Acceptance Testing)](../06-kubernetes-infrastructure/6.17-validation-and-acceptance-testing.md)
- [07 · Software-Defined Storage (7.7 Maintenance and Data Protection)](../07-software-defined-storage/7.7-maintenance-and-data-protection.md)
- [08 · Troubleshooting (08-ha-and-failover.md)](../08-troubleshooting-and-diagnostics/08-ha-and-failover.md)
