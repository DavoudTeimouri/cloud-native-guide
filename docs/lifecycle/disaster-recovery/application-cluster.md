# Application Cluster Disaster Recovery

## A. Purpose and scope

Recovery procedure for application clusters: restore from Velero backup, reattach Ceph CSI volumes, and let Argo CD reconcile workloads.

This is step 4 of the recovery order defined in `lifecycle/disaster-recovery/index.md` — it runs after the management cluster is restored.

## B. Prerequisites

| Prerequisite | Source |
|--------------|--------|
| Management cluster restored | `lifecycle/disaster-recovery/management-cluster.md` |
| Velero installed on application cluster | `lifecycle/backup/backup-and-dr.md` §C |
| Ceph CSI driver installed | `storage/ceph/cephadm-deployment.md` §CSI |
| Object storage (Ceph RGW) available | `storage/ceph/cephadm-deployment.md` §Recovery |

## C. Recovery procedure

### 1. Restore Velero backup

```bash
# List available backups
velero backup get

# Restore the latest full backup
velero restore create app-cluster-restore --from-backup app-cluster-<date>

# Wait for restore to complete
velero restore get app-cluster-restore
```

### 2. Reattach Ceph CSI volumes

PVs restored by Velero reference Ceph RBD/CephFS volumes. The CSI driver must reattach them to the correct nodes.

```bash
# Check PVC status
kubectl get pvc -A

# Check CSI controller logs
kubectl -n rook-ceph get pods -l app=csi-rbd-provisioner
kubectl -n rook-ceph logs -l app=csi-rbd-provisioner

# Verify pods can mount volumes
kubectl get pods -A | grep -i containercreating
```

### 3. Let Argo CD reconcile

Argo CD should automatically detect the restored resources and sync them.

```bash
# Check Argo CD application status
argocd app list

# Force sync if needed
argocd app sync <app-name>

# Verify all resources are Healthy
argocd app get <app-name>
```

## D. Verification

```bash
# All application pods running
kubectl get pods -A | grep -v Running | grep -v Completed

# All PVCs bound
kubectl get pvc -A | grep -v Bound

# Argo CD applications healthy
argocd app list | grep -v Healthy

# Services reachable
kubectl get svc -A
```

## E. Failure scenarios

| Scenario | Effect | Recovery |
|----------|--------|----------|
| PVC not bound after restore | Pod stuck in ContainerCreating | Check Ceph CSI driver, verify pool exists |
| Argo CD sync fails | Resources drift from Git | Check application manifest path, retry sync |
| Velero restore incomplete | Some resources missing | Re-run restore, check backup completeness |
| Ceph pool not mounted | PVCs stuck in Pending | Restore Ceph cluster first (step 5 of overall order) |

## F. Cross-references

- `lifecycle/disaster-recovery/index.md` — Recovery order and scenario index
- `lifecycle/backup/backup-and-dr.md` — Backup mechanics and RPO/RTO
- `storage/ceph/cephadm-deployment.md` — Ceph cluster recovery
- `storage/rook-ceph/rook-ceph.md` — Rook-Ceph deployment
