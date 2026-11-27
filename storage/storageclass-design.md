# StorageClass Design

## A. Purpose and scope

Document StorageClass design: RBD vs CephFS, replication, compression, encryption, snapshot class, PVC binding modes.

Cross-references `storage/ceph/cephadm-deployment.md`, `storage/rook-ceph/rook-ceph.md`.

## B. StorageClass profiles

| Profile | Backend | Use case | Replication | Compression |
|---------|---------|----------|-------------|-------------|
| ceph-rbd-standard | Ceph RBD | General block storage | 3 replicas | None |
| ceph-rbd-fast | Ceph RBD | High-performance block | 2 replicas | None |
| ceph-cephfs-standard | Ceph CephFS | Shared filesystem | 3 replicas | None |
| ceph-cephfs-compressed | Ceph CephFS | Shared filesystem with compression | 3 replicas | LZ4 |

## C. StorageClass examples

### RBD standard

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-rbd-standard
provisioner: ceph.com/csi
parameters:
  pool: replicapool
  storageCluster: my-cluster
  csi.storage.k8s.io/provisioner-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/controller-expand-secret-name: rook-csi-rbd-controller
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-rbd-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
  csi.storage.k8s.io/fstype: ext4
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

### CephFS compressed

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-cephfs-compressed
provisioner: ceph.com/csi
parameters:
  pool: myfs
  storageCluster: my-cluster
  csi.storage.k8s.io/provisioner-secret-name: rook-csi-cephfs-provisioner
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/controller-expand-secret-name: rook-csi-cephfs-controller
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-cephfs-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
  fsName: myfs
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
mountOptions:
  - compress=lz4
```

## D. PVC binding modes

| Mode | Description | Use case |
|------|-------------|----------|
| Immediate | PVC bound immediately on creation | Most applications |
| WaitForFirstConsumer | PVC bound when pod scheduled | StatefulSets, multi-AZ |

StorageClass default binding mode is `WaitForFirstConsumer` for shared filesystems and `Immediate` for RBD block storage.

## E. Cross-references

- `storage/ceph/cephadm-deployment.md` — Ceph deployment
- `storage/rook-ceph/rook-ceph.md` — Rook-Ceph operator
- `storage/pvc-lifecycle.md` — PVC lifecycle
