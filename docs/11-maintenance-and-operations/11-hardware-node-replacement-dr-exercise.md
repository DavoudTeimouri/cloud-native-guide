# Hardware Maintenance, Node Replacement, DR Exercise

## Purpose and scope
Hardware maintenance, node replacement, DR exercises, RTO/RPO measurement.

## Hardware maintenance
- Schedule maintenance window; notify stakeholders
- Drain node: kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
- Perform hardware maintenance (disk replacement, firmware, etc.)
- Uncordon node: kubectl uncordon <node>
- Verify node Ready; pods rescheduled

## Node replacement
- Drain and cordon failed node
- Replace hardware/provision new VM
- Apply OS baseline; join to cluster (Kubespray)
- Verify node Ready; workloads rescheduled
- Remove old node from cluster/inventory

## DR exercise
- Quarterly: restore one application from Velero backup into scratch namespace
- Annually: rebuild entire environment from documented order, offline; pass acceptance tests
- Annually: restore Vault from snapshot; unseal with offline shares
- Every drill records measured RTO; compares to declared target
- Failed drill = finding, not formality

## Implementation
```bash
# Drain node
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data

# Replace node
kubectl delete node <node>
# Provision new node; apply OS baseline; join via Kubespray
kubectl get nodes <new-node>

# DR drill
velero restore create <restore> --from-backup <backup>
etcdctl snapshot restore <snapshot> --data-dir /var/lib/etcd-new
```

## Validation
- Replacement node Ready; workloads rescheduled
- DR drill completed; RTO measured; within target
- Acceptance tests pass after restore

## Related
- [Troubleshooting (08-ha-and-failover.md)](../08-troubleshooting-and-diagnostics/08-ha-and-failover.md)
- [Upgrade & Lifecycle (10-08 Air-Gapped Upgrade)](../10-upgrade-and-lifecycle-management/10-08-air-gapped-upgrade.md)
