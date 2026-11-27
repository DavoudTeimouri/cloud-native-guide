# 08 · Rook-Ceph

## Symptoms
- Rook operator pod not running
- CephCluster stuck in Creating/Updating
- PVC not binding to Ceph RBD/CephFS
- OSD not provisioning on node
- CSI driver not working

## Possible causes
- Rook operator not running or crash-looping
- CephCluster spec invalid or incompatible version
- StorageClass not matching Rook pool
- Node lacks required labels/tolerations for OSD
- CSI driver not deployed or misconfigured

## Diagnostic commands
```bash
# Rook operator
kubectl get pods -n rook-ceph
kubectl get cephcluster -n rook-ceph
kubectl describe cephcluster <name> -n rook-ceph

# Storage
kubectl get storageclass
kubectl get pvc,pv
kubectl describe pvc <pvc>

# CSI
kubectl get pods -n rook-ceph -l app=csi
kubectl get csidriver
```

## Expected output
- rook-operator: Running
- CephCluster: Created/Ready
- PVC: Bound
- CSI driver: installed and healthy

## Investigation procedure
1. Check Rook operator pod status
2. Check CephCluster status and events
3. Check StorageClass provisioner matches Rook CSI
4. Check PVC events for provisioning errors
5. Check CSI driver pods and CSIDriver objects

## Resolution
- Restart Rook operator; fix CephCluster spec
- Create correct StorageClass or update PVC
- Deploy/fix CSI driver
- Add node labels/tolerations for OSD placement

## Verification
- CephCluster Created/Ready; PVC Bound; CSI driver healthy; volumes provisioning

## Prevention
- Monitor Rook operator health; alert on crash
- Monitor CephCluster status; alert on non-Ready
- Monitor storage capacity; alert at threshold

## Related
- [07 · Software-Defined Storage (7.5 Rook-Ceph)](../07-software-defined-storage/7.4-independent-ceph.md)
- [06 · Kubernetes Infrastructure (6.7 Storage Integration)](../06-kubernetes-infrastructure/6.8-cluster-storage-integration.md)
