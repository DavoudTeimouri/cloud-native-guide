# PVC Lifecycle

## A. Purpose and scope

Document PVC lifecycle: provisioning, binding, mounting, resizing, snapshotting, deletion, migration.

Cross-references `storage/storageclass-design.md`, `storage/ceph/cephadm-deployment.md`, `storage/rook-ceph/rook-ceph.md`.

## B. PVC lifecycle states

| State | Description | Next action |
|-------|-------------|-------------|
| Pending | PVC created, waiting for PV | StorageClass provisioning |
| Bound | PVC bound to PV | Pod can mount |
| Available | PV available but unbound | Waiting for PVC |
| Released | PVC deleted, PV released | Reclaim or delete |
| Failed | Provisioning failed | Investigate error |

## C. Provisioning and binding

```yaml
# PVC example
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

Binding mode `WaitForFirstConsumer` defers binding until a pod uses the PVC.

## D. Mounting

```yaml
# Pod referencing PVC
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

## E. Resizing

```bash
# Expand PVC
kubectl patch pvc app-pvc -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'

# Verify expansion
kubectl get pvc app-pvc
```

File system resize happens automatically when the pod restarts.

## F. Snapshotting

```yaml
# VolumeSnapshot example
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: app-pvc-snapshot
spec:
  volumeSnapshotClassName: ceph-rbd-snapshot
  source:
    persistentVolumeClaimName: app-pvc
```

## G. Deletion and migration

```bash
# Delete PVC
kubectl delete pvc app-pvc

# PVC deletion reclaims PV based on storageClass reclaimPolicy
# Delete = PV deleted, Retain = PV kept for manual cleanup
```

## H. Cross-references

- `storage/storageclass-design.md` — StorageClass design
- `storage/ceph/cephadm-deployment.md` — Ceph deployment
- `storage/rook-ceph/rook-ceph.md` — Rook-Ceph operator
- `lifecycle/disaster-recovery/application-cluster.md` — Application recovery
