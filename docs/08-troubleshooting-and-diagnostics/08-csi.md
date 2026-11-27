# 08 · CSI

## Symptoms
- PVC stuck in Pending
- Volume not attaching to node
- Snapshot creation failing
- Volume expansion failing
- CSI driver pod crash-looping

## Possible causes
- CSI driver not installed or not running
- StorageClass not matching available driver
- Insufficient storage capacity
- Node lacks CSI driver plugin
- Secret/credential for storage backend missing or expired

## Diagnostic commands
```bash
# CSI driver
kubectl get pods -n kube-system -l app=csi-cephfs
kubectl get daemonset -n kube-system | grep csi

# PVC/PV
kubectl get pvc,pv
kubectl describe pvc <pvc>
kubectl describe pv <pv>

# StorageClass
kubectl get storageclass
kubectl describe storageclass <sc>

# VolumeSnapshot
kubectl get volumesnapshot
kubectl describe volumesnapshot <vs>
```

## Expected output
- csi driver daemonset: Available, all nodes Ready
- PVC: Bound; PV: Bound/Available
- StorageClass: provisioner set correctly
- VolumeSnapshot: ReadyToUse

## Investigation procedure
1. Check PVC/PV status and events
2. Check StorageClass provisioner matches installed CSI driver
3. Check CSI driver daemonset status on all nodes
4. Check storage backend capacity and health (Ceph RGW/OSD)
5. Verify secret/credential for backend access

## Resolution
- Install/fix CSI driver daemonset
- Create correct StorageClass or update PVC to use it
- Expand storage backend capacity
- Rotate expired credentials/secrets

## Verification
- PVC Bound; PV attached to correct node; snapshot ReadyToUse; volume expansion succeeds

## Prevention
- Monitor CSI driver daemonset health; alert on crash
- Monitor storage capacity; alert at 70%/80%
- Monitor credential expiry; rotate before expiry

## Related
- [06 · Kubernetes Infrastructure (6.10 CSI and Storage Integration)](../06-kubernetes-infrastructure/6.10-csi-and-storage-integration.md)
- [07 · Software-Defined Storage](../07-software-defined-storage/index.md)
