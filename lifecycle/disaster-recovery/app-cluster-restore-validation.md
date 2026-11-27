# Application Cluster Restore Validation

## A. Purpose and scope

Validation procedure for application cluster restore from Velero backup: verify PVC reattachment, workload reconciliation, and data integrity. This is step 4 of the recovery order defined in `lifecycle/disaster-recovery/index.md` — it runs after the management cluster is restored and Velero restore has been initiated.

## B. Prerequisites

| Prerequisite | Source |
|---|---|
| Management cluster restored | `lifecycle/disaster-recovery/management-cluster.md` §A |
| Velero restore completed | `lifecycle/disaster-recovery/application-cluster.md` §C.1 |
| PVCs visible in Velero restore output | `lifecycle/backup/backup-and-dr.md` §C |
| Ceph CSI driver healthy | `storage/ceph/cephadm-deployment.md` §CSI |
| Object storage (Ceph RGW) available | `storage/ceph/cephadm-deployment.md` §Recovery |

## C. Validation procedure

### 1. Verify Velero restore completion

```bash
# Check restore status and timing
velero restore get -o wide

# Verify all namespaces were restored
velero restore get --log-level=debug

# Check resource-level restore status
velero resource get --restore=<restore-name> --all-namespaces
```

### 2. PVC reattachment verification

PVs restored by Velero reference Ceph RBD/CephFS volumes. The CSI driver must reattach them to the correct nodes.

```bash
# Check PVC status across all namespaces
kubectl get pvc -A

# Identify PVCs not yet bound
kubectl get pvc -A | grep -v Bound | grep -v NAME

# Check CSI controller logs for attachment events
kubectl -n rook-ceph get pods -l app=csi-rbd-provisioner
kubectl -n rook-ceph logs -l app=csi-rbd-provisioner | grep -i attach

# Verify node volume bindings
kubectl get nodes -o wide
```

### 3. Workload verification

Argo CD should automatically detect the restored resources and sync them to the desired state.

```bash
# Check Argo CD application status
argocd app list

# Force sync any drifted applications
argocd app sync <app-name>

# Verify all resources are Healthy
argocd app get <app-name>

# Check pod status across all namespaces
kubectl get pods -A
```

### 4. Data integrity checks

Run smoke queries to verify data was not corrupted during restore.

```bash
# Example: check row counts in key tables
kubectl exec -it <pod> -- psql -U postgres -c 'SELECT count(*) FROM orders;'

# Example: verify checksums if available
velero backup describe <backup-name> --details | grep -i checksum

# Test application-level connectivity
kubectl -n <namespace> get svc <service-name>
```

### 5. Final validation checklist

| Check | Expected | Command |
|---|---|---|
| All pods Running | No pods in Error/CrashLoop | `kubectl get pods -A | grep -v Running | grep -v Completed` |
| All PVCs Bound | All PVCs show Bound | `kubectl get pvc -A | grep -v Bound` |
| Argo CD applications Healthy | All apps show Healthy | `argocd app list | grep -v Healthy` |
| Services reachable | Services have external IPs/hosts | `kubectl get svc -A` |
| Data integrity verified | Smoke queries pass | Application-specific checks |

## D. Failure scenarios

| Scenario | Effect | Recovery |
|---|---|---|
| PVC not bound after Velero restore | Pod stuck in ContainerCreating | Check Ceph CSI driver logs, verify pool exists, re-trigger CSI reattach |
| Argo CD sync fails | Resources drift from Git | Check application manifest path, retry `argocd app sync`, verify source repos |
| Velero restore incomplete | Some resources missing | Re-run restore from the same backup, check backup completeness |
| Ceph pool not mounted | PVCs stuck in Pending | Restore Ceph cluster first (step 5 of overall recovery order) |
| Data checksum mismatch | Potential data corruption | Restore from older backup, compare with last known-good state |

## E. Cross-references

- `lifecycle/disaster-recovery/index.md` — Recovery order and scenario index
- `lifecycle/disaster-recovery/application-cluster.md` — Full application cluster DR procedure
- `lifecycle/disaster-recovery/management-cluster.md` — Management cluster restore prerequisite
- `lifecycle/backup/backup-and-dr.md` — Backup mechanics, RPO/RTO, Velero configuration
- `storage/ceph/cephadm-deployment.md` — Ceph cluster recovery and CSI driver
- `storage/rook-ceph/rook-ceph.md` — Rook-Ceph deployment details
- `secrets-management/vault/recovery/restore.md` — Vault unseal required for platform auth
- `management-cluster/rancher/rancher.md` — Rancher cluster restoration order