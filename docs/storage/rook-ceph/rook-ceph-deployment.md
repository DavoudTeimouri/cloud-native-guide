# Rook-Ceph Deployment

## A. Prerequisites

- Kubernetes cluster with >= 3 nodes for monitor quorum
- At least 3 nodes with unmounted disks for OSDs (use explicit device lists, never `useAllDevices: true`)
- Node labels for storage scheduling (e.g., `rook/ceph-osd: "true"`)
- Available CPU/Memory for Rook operator and Ceph daemons
- Offline artifact matrix verified (`compatibility/version-matrix.md`)

## B. Operator Installation

```bash
# 1. Apply CRDs first — they must be applied before the operator
kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/crds.yaml

# 2. Apply common.yaml (RBAC, CRDs, csi driver)
kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/common.yaml

# 3. Apply the operator
kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/operator.yaml

# 4. Verify operator rollout
kubectl -n rook-ceph rollout status deployment/rook-ceph-operator --timeout=300s
```

**Important**: Record the Rook version and supported Ceph image tag in `compatibility/version-matrix.md`. Never set a Ceph image version that the installed Rook release does not support.

## C. CephCluster Creation

```yaml
apiVersion: rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v18.2.x    # VERIFY against pinned Rook release
  dataDirHostPath: /var/lib/rook
  mon:
    count: 3
    allowMultiplePerNode: false
  mgr:
    count: 2
    modules:
      - name: rook
        enabled: true
      - name: pg_autoscaler
        enabled: true
      - name: rook-cephfs
        enabled: true
      - name: rook-rgw
        enabled: true
  dashboard:
    enabled: true
    ssl: true
  network:
    provider: host
    # Or use a dedicated StorageClass for the public/cluster network
  storage:
    useAllNodes: false
    useAllDevices: false
    nodes:
      - name: "node1"
        devices:
          - name: "sdb"
            config:
              osdsPerDevice: "1"
      - name: "node2"
        devices:
          - name: "sdb"
            config:
              osdsPerDevice: "1"
      - name: "node3"
        devices:
          - name: "sdb"
            config:
              osdsPerDevice: "1"
  resources:
    osd:
      requests:
        cpu: "2"
        memory: 4Gi
  priorityClassNames: [system-node-critical]
```

**Mandatory production rules**:
- `useAllDevices: false` with explicit `devices` — never let Rook claim every unmounted disk
- `failureDomain: host` for all replicated pools (plus rack awareness where applicable)
- Node labels so OSD pods land on storage nodes
- `priorityClassNames: [system-node-critical]` for OSD and monitor pods

## D. Storage Class Configuration

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-rbd
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: rook-ceph.cephcsi.com
allowVolumeExpansion: true
reclaimPolicy: Delete
volumeBindingMode: Immediate
parameters:
  csi.storage.k8s.io/provisioner-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/controller-expand-secret-name: rook-csi-rbd-provisioner
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-rbd-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
  csi.storage.k8s.io/fstype: ext4
  csi.storage.k8s.io/pool: replicapool
  csi.storage.k8s.io/clusterID: rook-ceph
```

CephFS StorageClass is the same with `provisioner: rook-ceph.cephcsi.com` and `csi.storage.k8s.io/fstype: ext4` pointing at the filesystem name.

**Default bucket claim**: The `is-default-class: "true"` annotation makes this the default StorageClass for PVCs without explicit `storageClassName`.

## E. Pool Management

```yaml
apiVersion: rook.io/v1
kind: CephBlockPool
metadata:
  name: replicapool
  namespace: rook-ceph
spec:
  failureDomain: host
  replicated:
    size: 3
  crushRoot: "my-root"
  deviceClass: ssd
  parameters:
    targetSizeRatio: 0.5
```

**Pool operations**:

| Task | Procedure |
|---|---|
| Add an OSD | Add the node to `spec.storage.nodes`, apply — Rook creates the OSD automatically |
| Replace a failed OSD | OSD pod goes `Crashed`; replace the disk, then remove the OSD from the node list and re-apply |
| Scale a pool | Edit `CephBlockPool.spec.replicated.size`, apply — data rebalances automatically |
| Expand a pool | Edit `spec.parameters.targetSizeRatio` upward, apply — OSDs rebalance |
| Enable snapshots | CSI snapshotter deployed by default; create `VolumeSnapshot` objects |
| Back up | Velero with CSI snapshot integration, or `rbd export` to object store |

## F. OSD Tuning

Key OSD parameters to tune via `CephCluster.spec.storage.osd.config` or device-level config:

| Parameter | Recommended | Impact |
|---|---|---|
| `osd_max_backfills` | `2` | Control parallelism of backfill/recovery |
| `osd_max_bulk_operations` | `4` | Limit bulk data operations per OSD |
| `osd_scrub_interval` | `3600` (seconds) | Tune scrub frequency |
| `osd_deep_scrub_interval` | `86400` (seconds) | Tune deep scrub frequency |
| `osd_pool_default_min_size` | `2` | Minimum size for new pools |
| `osd_pool_default_size` | `3` | Default replication size |
| `osd_cache_size` | `0.5` (fraction of RAM) | OSD cache size for read/write caching |
| `osd_max_write_size` | `4` (MB) | Max write packet size |

**Example OSD config in CephCluster**:

```yaml
spec:
  storage:
    osd:
      config:
        osd_max_backfills: "2"
        osd_deep_scrub_interval: "86400"
        osd_pool_default_min_size: "2"
```

## G. Monitoring Integration

Rook deploys Prometheus and Grafana automatically. Key series:

| Series | Description |
|---|---|
| `ceph_cluster_status` | Overall cluster health (up/down, health status) |
| `ceph_osd_status` | Individual OSD state |
| `ceph_pg_status` | Placement group state, acting/up copies |
| `ceph_mon_io` | I/O operations per second |
| `ceph_disk_io_total` | Per-disk I/O metrics |
| `ceph_objectstore_gateway_requests_total` | RGW request count |
| `rook_ceph_health_status` | Rook operator-reported health |

**Grafana dashboards** are available out-of-the-box. Recommended alerts:

- Replication lag beyond threshold (promote only sync replicas)
- OSD down beyond RTO window
- PG stuck in `undersized` or `degraded` state
- CSI provisioner failures
- Monitor quorum loss

**Custom alert example** (YAML for PrometheusRule):

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ceph-alerts
  namespace: rook-ceph
spec:
  groups:
  - name: ceph.rules
    rules:
    - alert: CephClusterDegraded
      expr: ceph_cluster_status{job="ceph"} != "HEALTH_OK"
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Ceph cluster is not healthy"
        description: "Ceph cluster {{ $labels.cluster }} has been degraded for more than 5 minutes."
    - alert: CephOSDDown
      expr: ceph_osd_status{job="ceph"} == "out"
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Ceph OSD is down"
        description: "OSD {{ $labels.osd }} has been down for more than 10 minutes."
```

## H. Validation

```bash
# Check operator status
kubectl -n rook-ceph get pods
kubectl -n rook-ceph rollout status deployment/rook-ceph-operator --timeout=300s

# Check cluster health
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s

# Check storage classes
kubectl get storageclass

# Function test — create a PVC and workload
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rook-test
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
  storageClassName: ceph-rbd
EOF

# Verify CSI provisioner created the PV
kubectl get pvc -n <namespace>
kubectl get pv -n <namespace>
```