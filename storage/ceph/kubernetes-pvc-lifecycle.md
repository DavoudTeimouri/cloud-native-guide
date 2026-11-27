# Kubernetes PVC Lifecycle with Rook-Ceph

*Documentation of Rook-Ceph Kubernetes integration: StorageClass configuration, PVC lifecycle, snapshot/restore, volume expansion, and troubleshooting PVC binding issues.*

---

## StorageClass Configuration

Rook-Ceph creates default StorageClasses when the operator is deployed. The primary StorageClasses are:

- `ceph-rbd-standard` — RBD (RADOS Block Device) for block volumes.
- `cephfs-standard` — CephFS for file-system volumes.
- `cephfs-csi-standard` — CSI plugin for CephFS (newer deployments).

### Example StorageClass (RBD)

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
provisioner: rook/ceph
parameters:
  cluster: rook-ceph
  pool: rbd
  user: admin
  userId: admin
  fsType: ext4
  volumeBindingMode: Immediate
```

*See [`storage/storageclass-design.md`] for overarching StorageClass design guidelines.*

---

## PVC Lifecycle States

| State      | Description                              | Next action                              |
|------------|------------------------------------------|------------------------------------------|
| **Pending**   | PVC created, waiting for PV               | StorageClass provisioning                |
| **Bound**     | PVC bound to PV                           | Pod can mount the volume                 |
| **Available** | PV available but unbound                  | Waiting for a PVC to bind                |
| **Released**  | PVC deleted, PV released                  | Reclaim or delete the PV                 |
| **Failed**    | Provisioning failed                       | Investigate error messages               |

*Cross-reference: [PVC Lifecycle](#pvc-lifecycle-states) in `storage/pvc-lifecycle.md`.*

---

## Provisioning and Binding

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ceph-rbd-standard
  resources:
    requests:
      storage: 50Gi
```

*Binding mode `WaitForFirstConsumer` defers binding until a pod uses the PVC.*

---

## Mounting

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: app
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: app-pvc
```

---

## Snapshot and Restore

### VolumeSnapshot

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: app-pvc-snapshot
spec:
  volumeSnapshotClassName: ceph-rbd-snapshot
  source:
    persistentVolumeClaimName: app-pvc
```

### Restoring from a Snapshot

1. Create a PVC from the snapshot:

   ```bash
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: app-pvc-restored
   spec:
     storageClassName: ceph-rbd-standard
     dataSource:
       name: app-pvc-snapshot
       kind: VolumeSnapshot
       apiGroup: snapshot.storage.k8s.io
     resources:
       requests:
         storage: 50Gi
   ```

2. Mount the restored PVC in a pod.

*Cross-reference: VolumeSnapshot classes are defined in [`storage/ceph/cephadm-deployment.md`].*

---

## Volume Expansion

Rook-Ceph supports online PVC expansion. After increasing the PVC request, the underlying Ceph OSD pool is resized and the file system is grown on pod restart.

```bash
# Patch the PVC to request more storage
kubectl patch pvc app-pvc -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'

# Verify the PVC size
kubectl get pvc app-pvc
```

*File system resize happens automatically when the pod restarts, or you can manually resize inside the pod (e.g., `resize2fs /dev/...`).*

---

## Troubleshooting PVC Binding Issues

| Symptom                              | Likely Cause                              | Resolution                                                                      |
|--------------------------------------|-------------------------------------------|----------------------------------------------------------------------------------|
| PVC stays **Pending**                | No available PV, wrong storageClassName   | Check `StorageClass` provisioner, ensure Ceph cluster is healthy, pool exists.   |
| PVC **Pending** with `FailedBinding` | Insufficient resources, cluster not ready | Verify Rook-Ceph operator is running, OSDs are healthy, pool has quota.         |
| PVC binds but I/O errors              | Wrong `fsType` or mount options           | Check PV `capacity` and `fsType` match the actual filesystem.                   |
| PVC **Pending** `VolumeExpansion` not allowed | Expansion feature gate disabled      | Enable `allowVolumeExpansion: true` in the StorageClass.                         |

### Commands for diagnosis

```bash
# Describe the PVC to see events
kubectl describe pvc app-pvc

# Describe the underlying PV
kubectl describe pv <pv-name>

# Check Rook-Ceph cluster health
kubectl -n rook-ceph get cluster rook-ceph -o yaml

# Check storage class parameters
kubectl get storageclass ceph-rbd-standard -o yaml
```

*For deeper debugging, consult [`storage/ceph/failure-recovery.md`] and the Rook-Ceph documentation.*

---

## Cross-references

- `storage/storageclass-design.md` — StorageClass design guidelines.
- `storage/ceph/cephadm-deployment.md` — Ceph deployment and snapshot classes.
- `storage/rook-ceph/rook-ceph.md` — Rook-Ceph operator concepts.
- `storage/pvc-lifecycle.md` — General PVC lifecycle (states, resizing, deletion).
- `lifecycle/disaster-recovery/application-cluster.md` — Application‑level recovery procedures.
