# Storage Troubleshooting

## Common Issues

### PVC Stuck in Pending

**Symptoms**: PVC remains in `Pending` state.

**Likely Causes**:
- No StorageClass available
- StorageClass provisioner not running
- Insufficient capacity
- VolumeBindingMode mismatch
- Node affinity/selector mismatch

**Diagnosis**:
```bash
kubectl describe pvc <pvc-name> -n <namespace>
kubectl get storageclass
kubectl get pv
kubectl describe sc <storageclass-name>
```

**Resolution**:
- Install/verify provisioner (Rook-Ceph CSI, etc.)
- Check capacity and reclaim space
- Verify VolumeBindingMode matches topology
- Check node selectors/affinity

### PVC Stuck in Terminating

**Symptoms**: PVC stuck in `Terminating` state with finalizers.

**Likely Causes**:
- Pod still using the PVC
- Volume still mounted
- Finalizer blocking deletion

**Diagnosis**:
```bash
kubectl describe pvc <pvc-name> -n <namespace>
kubectl get pods -A -o wide | grep <pvc-name>
kubectl get pv <pv-name>
```

**Resolution**:
```bash
# Remove finalizer if safe
kubectl patch pvc <pvc-name> -n <namespace> -p '{"metadata":{"finalizers":null}}' --type=merge

# Force delete PV if needed
kubectl patch pv <pv-name> -p '{"metadata":{"finalizers":null}}' --type=merge
```

### PVC Not Binding to PV

**Symptoms**: PVC and PV both exist but not bound.

**Likely Causes**:
- Label/annotation mismatch
- StorageClassName mismatch
- AccessModes incompatible
- VolumeMode incompatible

**Diagnosis**:
```bash
kubectl get pvc -A
kubectl get pv -A
kubectl describe pvc <pvc> -n <ns>
kubectl describe pv <pv>
```

**Resolution**:
- Match StorageClassName exactly
- Ensure AccessModes compatible (RWO vs RWX)
- Match VolumeMode (Filesystem vs Block)
- Check labels/annotations

### Ceph RBD Issues

**Symptoms**: RBD volumes not mounting, IO errors.

**Likely Causes**:
- Ceph cluster unhealthy
- RBD image not mapped
- Keyring/secret missing
- CephFS kernel module not loaded

**Diagnosis**:
```bash
ceph -s
ceph osd pool ls
rbd ls <pool>
ceph health detail
kubectl logs -n rook-ceph -l app=rook-ceph-operator
```

**Resolution**:
- Fix Ceph health issues
- Verify keyring/secret exists in namespace
- Load Ceph kernel modules: `modprobe rbd`

### CSI Driver Issues

**Symptoms**: Volume attachment/mount fails.

**Likely Causes**:
- CSI driver pods not ready
- Node plugin not running
- Node registration failed
- VolumeAttributesClass mismatch

**Diagnosis**:
```bash
kubectl get pods -n <csi-namespace>
kubectl get csinode
kubectl get csidriver
kubectl describe csinode <node>
```

**Resolution**:
- Restart CSI driver pods
- Re-register node: `kubectl delete csinode <node>`
- Verify VolumeAttributesClass if used

---

*Status: DRAFT | Owner: Storage Team | Last reviewed: 2026-11-23*