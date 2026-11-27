# Phase 3 — Ceph & Rook-Ceph Storage Lifecycle

**Purpose**: Document the complete storage lifecycle for Ceph in both deployment models (Rook-Ceph in‑cluster and cephadm external), including node lifecycle operations (add/remove/replace), pool/StorageClass design, and validated operational procedures. This phase is the continuation of the cluster foundation (Phase 1) and management‑layer (Phase 2) guides.

**Entry criteria**:
- Kubernetes cluster deployed per Phase 1 and management layer verified per Phase 2.
- One of the two Ceph deployment models selected and documented (Rook‑Ceph or cephadm external).
- Internal container registry populated with the required Ceph/Rook images per `offline-artifacts/artifact-matrix.md`.
- Administrative access to the cluster and to the Ceph host(s) (SSH, sudo).
- Record of the chosen RPO/RTO targets (Section "Reliability Metrics & Guards" in the DBRE specialist spec).
- For cephadm: internal registry (Harbor/Nexus/self‑hosted OCI) reachable from all Ceph hosts; `cephadm` bootstrap complete.
- For Rook‑Ceph: operator CRDs, operator, and CephCluster manifest applied; `rook-ceph` namespace healthy.

**Exit criteria**:
- All seven sub‑sections are complete and reviewed.
- Validation commands have been run and produce the expected healthy state.
- Rollback steps are documented and tested (where applicable).
- The phase is signed‑off by the Database Reliability Engineer and the platform architect.

---
## 1. Deployment Model Decision Matrix

| Criterion | Rook‑Ceph (in‑cluster, operator‑managed) | cephadm (external dedicated hosts, CSI) |
|---|---|---|
| **Scope** | Storage lives only inside the Kubernetes cluster. | Storage is a separate cluster of dedicated hosts, consumed by Kubernetes via an external CSI driver. |
| **Deployment model** | Operator watches CRDs (`CephCluster`, `CephBlockPool`, `CephFilesystem`, `CephObjectStore`). | `cephadm` bootstrap on dedicated hosts; OSDs, MONs, MGRs, MDS, RGW run as containers managed by the ceph orchestrator. |
| **Failure coupling** | A cluster‑wide network/CNI failure can affect storage availability. | Storage is independent of the K8s CNI; a network fault in the K8s cluster does not impact the Ceph hosts. |
| **K8s integration** | Native CRDs, CSI driver, PVC lifecycle fully managed inside Kubernetes. | External CSI driver (cephcsi / csi‑ceph) deployed as a separate component; apps still use standard PVCs. |
| **Operational overhead** | Higher — two control loops (Rook operator + ceph). Upgrades require Rook → Ceph image sequence. | Lower — vendor lifecycle (ceph orch) handles daemon placement, upgrades, and recovery. |
| **Best for** | Cluster‑local storage, simpler estates; multi‑cluster shared capacity via external Ceph. | Shared capacity across multiple clusters; strict independence from the K8s lifecycle; large estates with dedicated hardware. |
| **Multi‑cluster consumption** | No — each cluster owns its own Rook‑Ceph installation. | Yes — the same external Ceph cluster can be consumed by many Kubernetes clusters. |
| **Offline artifact volume** | High (operator, CRDs, CSI images, Ceph daemon images). | Medium (cephadm bootstrap images, container engine, registry mirror). |
| **Decision rule** | Choose Rook‑Ceph when the storage requirement is *cluster‑local* and the team wants a purely Kubernetes‑centric lifecycle. | Choose cephadm when storage must survive the loss of the Kubernetes cluster, when serving multiple clusters, or when a dedicated hardware base is already in place. |

*Reference: comparison data from `docs/storage/alternatives/storage-alternatives.md`; deployment details from `docs/storage/ceph/cephadm-deployment.md` and `docs/storage/rook-ceph/rook-ceph.md`.*

---
## 2. Rook-Ceph: In‑Cluster Operator‑Managed Lifecycle

### 2.1 Apply CRDs, Operator, and CephCluster

```bash
# 1. Apply CRDs (must be first)
kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/crds.yaml

# 2. Apply common components and operator
kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/common.yaml
kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/operator.yaml

# 3. Verify operator rollout
kubectl -n rook-ceph rollout status deployment/rook-ceph-operator --timeout=300s
```

> **Note**: The Ceph version (`image: quay.io/ceph/ceph:v18.2.x`) must match the pinned Rook release; record the exact version in `compatibility/version-matrix.md`.

### 2.2 CephCluster manifest (explicit nodes, `useAllDevices: false`)

```yaml
apiVersion: rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v18.2.x      # verify against version-matrix.md
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

- `useAllDevices: false` with explicit `nodes` and `devices` is **mandatory** in production. `useAllDevices: true` claims every unmounted disk, including those intended for other purposes.
- Device names (`sdb`, `sdc`, …) must be discovered on each node (`lsblk -d -o NAME,SIZE,TYPE,ROTA,MODEL`) and must not be partitioned or shared with the OS.
- CRUSH failure domain: set `failureDomain: host` in pools (see §2.3). Add rack awareness when the site has racks.

### 2.3 Pools

| Pool | Type | Replication | failureDomain | Example |
|---|---|---|---|---|
| `replicapool` | CephBlockPool | replicated size 3 | `host` | `ceph osd pool create replicapool 64 64 repl 3` |
| `cephfs_metadata` | internal | replicated size 3 | `host` | created automatically by `CephFilesystem` |
| `cephfs_data` | references `replicapool` | — | — | |
| `rgw` | CephObjectStore | replicated size 3 | `host` | created by `CephObjectStore` spec |

**CephBlockPool** (RBD pool for block volumes):

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

**CephFilesystem**:

```yaml
apiVersion: rook.io/v1
kind: CephFilesystem
metadata:
  name: myfs
  namespace: rook-ceph
spec:
  metadataPool:
    replicated:
      size: 3
  dataPool:
    name: replicapool
  metadataServer:
    activeCount: 2
    activeStandby: true
```

**CephObjectStore (RGW)**:

```yaml
apiVersion: rook.io/v1
kind: CephObjectStore
metadata:
  name: my-store
  namespace: rook-ceph
spec:
  storePool:
    name: replicapool
  gateway:
    port: 80
    instances: 2
  hostNetwork:
    enable: false
  security:
    kms:
      connectionDetails:
        vaultBackend: vault
  users:
    - name: "app-user"
      displayName: "Application user"
      capabilities:
        - "buckets=*"
        - "users=*"
```

### 2.4 StorageClasses

| StorageClass | Provisioner | Used for |
|---|---|---|
| `ceph-rbd` | `rook-ceph.cephcsi.com` | RBD block volumes (stateful apps, databases) |
| `cephfs` | `rook-ceph.cephcsi.com` | CephFS shared filesystem |
| `ceph-rgw` | `rook-ceph.cephcsi.com` | S3‑compatible object storage |

**Example `ceph-rbd` StorageClass** (default):

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
  csi.storage.k8s.io/provisioner-secret-name: rook-csi-cephfs-provisioner
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/controller-expand-secret-name: rook-csi-cephfs-provisioner
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-cephfs-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
  csi.storage.k8s.io/fstype: ext4
  csi.storage.k8s.io/pool: replicapool
  csi.storage.k8s.io/clusterID: rook-ceph
```

### 2.5 Validation

```bash
# Cluster health
kubectl -n rook-ceph get pods

# CEPH status via the operator
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s

# List StorageClasses
kubectl get storageclass

# Inspect the CephCluster
kubectl -n rook-ceph get cephcluster -o yaml | head -40

# Function test — create a PVC and a pod
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

# Wait for binding and attach
kubectl wait --for=condition=Bound pvc/rook-test --timeout=120s

# I/O test
kubectl run rook-test-pod --image=busybox --restart=Never --command -- sh -c "echo 'test write' > /mnt/test && cat /mnt/test"
```

### 2.6 Rook-Ceph specifics (operator lifecycle, node placement, drain)

- **Operator lifecycle**: upgrade sequence is Rook operator → Ceph daemon image. Never set a Ceph image version unsupported by the installed Rook release (the most common failure mode).
- **K8s node labels**: label storage nodes (e.g., `node-role.kubernetes.io/storage=``) so that OSD pods land on them. The CephCluster `spec.storage.nodes` names must match the Kubernetes node names.
- **OSD scheduling**: OSD pods have `priorityClassNames: [system-node-critical]` and node selectors derived from the `nodes` list. General worker pods should not conflict.
- **PVC/StorageClass dependencies**: a PVC bound to `ceph-rbd` or `cephfs` implicitly depends on the `replicapool` CephBlockPool and the `myfs` CephFilesystem (if applicable). Deleting the StorageClass does **not** delete the underlying pool; manual cleanup is required.
- **MON placement**: 3 MONs across 3 separate hosts, odd count only. Do not co‑locate MON with the only OSD of a pool.
- **Kubernetes drain implications**: before `kubectl drain <node>`, first `kubectl -n rook-ceph patch cephcluster/rook-ceph -p '{"spec":{"storage":{"nodes":[{"name":"<node>"},"devices":[{"name":"<device>"}]}}'}'` **or** use the Rook `ceph osd out` then `ceph osd remove` flow. Failing to evacuate OSDs first will result in the node getting stuck in `NotReady` and OSDs becoming `down`.
- **Relationship between K8s node lifecycle and Ceph node lifecycle**: each K8s storage node corresponds to one Ceph OSD host. Adding a K8s node requires adding a new entry to `spec.storage.nodes` and its devices; removing a K8s node requires `ceph osd out <osd-id>` → `ceph osd remove <osd-id>` → then the K8s node can be drained and deleted. The phase must be sequenced: Ceph first, K8s second.

*Reference: operator lifecycle and best practices from `docs/storage/rook-ceph/rook-ceph.md`; CRUSH and failure domain from `docs/storage/ceph/crush-rules-documentation.md`; MON placement from `docs/storage/ceph/mon-osd-crush-pools.md`.*

---
## 3. cephadm External: Deploy on Dedicated Hosts Outside K8s

### 3.1 High‑level architecture

```
K8s cluster                    cephadm Ceph cluster (dedicated hosts)
  +-------------------+       +-----------------------------------+
  | CSI driver pod   |------>| MON x3 (10.40.0.x:6789)          |
  | (external)       |       | MGR x2 (active/standby)           |
  +-------------------+       | OSD x N (10.40.0.x:6800-7568)    |
                            | MDS x N (CephFS, optional)        |
                            | RGW x N (S3, optional)            |
                            +-----------------------------------+
```

- The CSI driver runs **inside** the K8s cluster but connects to the external Ceph cluster over the cluster network (e.g., `10.41.0.0/24`).
- Ceph daemons are containers managed by `cephadm` on dedicated hosts; they are **not** part of the K8s etcd or API server.
- The external CSI driver (cephcsi or csi‑ceph) is deployed as a separate Helm chart or static manifest; it pulls the Ceph configuration and keyring from the bootstrap host.

### 3.2 Prerequisites (per the cephadm-deployment.md reference)

- Internal registry (`harbor.internal`, `nexus.internal`, or self‑hosted OCI) mirroring `quay.io/ceph` images.
- All Ceph hosts prepared per §1 of `cephadm-deployment.md` (OS, kernel, time, name resolution, disks, SSH, network).
- Engine (Docker or Podman) installed and configured for air‑gap pull from the internal registry.
- `cephadm` bootstrap on the first host (MON) complete; `ceph -s` returns `HEALTH_OK`.

### 3.3 Bootstrap (first host only)

```bash
# Install cephadm on the bootstrap host (from internal mirror)
dnf install -y cephadm   # Oracle Linux
# apt install -y cephadm   # Ubuntu

# Bootstrap — pass --docker when using Docker; omit for Podman
cephadm --docker bootstrap \
  --mon-ip 10.40.0.11 \
  --cluster-network 10.41.0.0/24 \
  --registry harbor.internal \
  --log-to-file

# Verify
cephadm shell -- ceph -s
cephadm shell -- ceph orch ps
```

### 3.4 Assign roles and add hosts

```bash
# Add each remaining host (ensure engine is installed first)
cephadm shell -- ceph orch host add ceph-mon-2 10.40.0.12
cephadm shell -- ceph orch host add ceph-mon-3 10.40.0.13
cephadm shell -- ceph orch host add ceph-osd-1 10.40.0.14
cephadm shell -- ceph orch host add ceph-osd-2 10.40.0.15
cephadm shell -- ceph orch host add ceph-osd-3 10.40.0.16

# Label hosts by role
cephadm shell -- ceph orch host label add ceph-mon-1 mon
cephadm shell -- ceph orch host label add ceph-mon-2 mon
cephadm shell -- ceph orch host label add ceph-mon-3 mon
cephadm shell -- ceph orch host label add ceph-mgr-1 mgr
cephadm shell -- ceph orch host label add ceph-mgr-2 mgr
cephadm shell -- ceph orch host label add ceph-osd-1 osd
cephadm shell -- ceph orch host label add ceph-osd-2 osd
cephadm shell -- ceph orch host label add ceph-osd-3 osd
cephadm shell -- ceph orch host label add ceph-mds-1 mds
cephadm shell -- ceph orch host label add ceph-mds-2 mds
cephadm shell -- ceph orch host label add ceph-rgw-1 rgw
cephadm shell -- ceph orch host label add ceph-rgw-2 rgw
```

### 3.5 Define OSDs and pools

```bash
# List available devices
cephadm shell -- ceph orch device ls

# Create OSDs (explicit devices, one OSD per data disk)
cephadm shell -- ceph orch apply osd --all-available-devices
# Or per‑host:
cephadm shell -- ceph orch apply osd ceph-osd-1 \
  --data-devices /dev/sdb,/dev/sdc \
  --db-devices /dev/nvme1n1

# Create pools (replicated size 3, host failure domain)
cephadm shell -- ceph osd pool create kube-rbd 64 64 repl 3
cephadm shell -- ceph osd pool application enable kube-rbd rbd

# Create CephFS (metadata + data pool)
cephadm shell -- ceph mgr module enable cephfs --force
cephadm shell -- ceph fs new cephfs cephfs_metadata cephfs_data

# Enable RGW
cephadm shell -- ceph mgr module enable rgw --force
cephadm shell -- ceph orch apply rgw rgw \
  --placement="2 ceph-rgw-1 ceph-rgw-2" \
  --spec '{"rgw_frontend_port": 8080}'
```

### 3.6 StorageClasses (external CSI driver)

The external CSI driver is typically deployed as the `cephcsi` Helm chart; after it's running, create StorageClasses that point at the external cluster FSID:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-external-rbd
provisioner: rbd.csi.ceph.com
parameters:
  clusterID: <fsid-from-`ceph fsid`>
  pool: kube-rbd
  imageFeatures: layering
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: Immediate
```

### 3.7 Validation

```bash
# Cluster health
ceph -s

# Verify CSI driver pods
kubectl -n rook-ceph get pods  # if using rook CSI, otherwise check csi‑ceph namespace

# List StorageClasses
kubectl get storageclass

# PVC test (same as Rook‑Ceph example in §2.5)
```

### 3.8 Adding a cephadm node (future expansion)

1. Prepare the new host per §1.1‑1.6 of `cephadm-deployment.md`.
2. Add the host to the ceph inventory:
   ```bash
   cephadm shell -- ceph orch host add <new-host-fqdn> <ip>
   ```
3. Label the host for its role (mon, osd, mgr, etc.).
4. Add the device(s) for OSD:
   ```bash
   cephadm shell -- ceph orch apply osd <new-host> --data-devices /dev/sdb --db-devices /dev/nvme1n1
   ```
5. Rebalance pools:
   ```bash
   ceph osd pool rebalance kube-rbd
   ```
6. Verify with `ceph -s` and `ceph osd tree`.

### 3.9 Removing a cephadm node

1. `ceph osd out <osd-id>` (wait for OSD to become `out=0`).
2. `ceph osd pool rebalance <pool>` to ensure data is redistributed.
3. `ceph osd remove <osd-id>` (this removes the OSD from the map).
4. Remove the host label and, if decommissioning, shut down the host.
5. MON removal only if the host was a MON: `ceph mon remove <mon-id>` after quorum is healthy.
6. MDS/RGW considerations: follow the same evacuation pattern; ensure the remaining instances meet the minimum count before removing the host.

*All steps are documented in `docs/storage/ceph/cephadm-deployment.md` §F‑J (OSD failure, MON loss, recovery procedures).*

---
## 4. Adding a Ceph Node (both Rook‑Ceph and cephadm)

### 4.1 Host preparation

| Step | Rook‑Ceph | cephadm |
|---|---|---|
| OS and kernel | Oracle Linux 8/9 or Ubuntu 22.04/24.04, XFS `ftype=1`, kernel 5.4+/5.15+, required modules (`br_netfilter`, `nf_conntrack`, `rbd`) | Same as Rook, plus engine (Docker/Podman) installed from internal mirror |
| Time | `chrony` synchronized, at least two internal NTP sources | Same |
| Name resolution | `/etc/hosts` identical on all hosts, or DNS resolving all Ceph hostnames | Same; also ensure `NO_PROXY`/`no_proxy` excludes internal addresses |
| SSH | Passwordless SSH as deploy user from bootstrap host | Same; `cephadm` uses SSH to orchestrate remote daemons |
| Disks | Dedicated data disks, XFS `ftype=1`, separate NVMe for DB/WAL | Same; one OSD daemon per data disk |

### 4.2 Role‑specific steps

#### 4.2.1 Adding a MON

- **Rook‑Ceph**: not usually needed after initial 3‑MON deployment; if adding, edit `CephCluster.spec.mon.count` and apply; the operator will create a new MON pod on a node with the `mon` label.
- **cephadm**:
  ```bash
  cephadm shell -- ceph orch host add <new-mon-host> <ip>
  cephadm shell -- ceph orch host label add <new-mon-host> mon
  cephadm shell -- ceph orch apply mon --placement="3 ceph-mon-1 ceph-mon-2 ceph-mon-3 <new-host>"
  ```
- Quorum is maintained as long as >= 3 MONs are up; losing 2 of 3 still allows recovery.

#### 4.2.2 Adding an OSD

- **Rook‑Ceph**: add a new entry under `CephCluster.spec.storage.nodes` with the node name and device path; apply the CephCluster manifest. Rook will create the OSD pod.
- **cephadm**:
  ```bash
  cephadm shell -- ceph orch host add <new-osd-host> <ip>
  cephadm shell -- ceph orch host label add <new-osd-host> osd
  cephadm shell -- ceph orch apply osd <new-osd-host> --data-devices /dev/sdb --db-devices /dev/nvme1n1
  ```
- Verify: `ceph osd tree` shows the new OSD `up` and `in`.

#### 4.2.3 Adding MDS (CephFS)

- **Rook‑Ceph**: ensure `activeCount: 2` in `CephFilespec`; the operator will place MDS pods on nodes with the `mds` label.
- **cephadm**:
  ```bash
  cephadm shell -- ceph orch host label add <new-mds-host> mds
  cephadm shell -- ceph orch apply mds --placement="2 <label> <label>"
  ```

#### 4.2.4 Adding RGW

- **Rook‑Ceph**: add or adjust `CephObjectStore.spec.gateway.instances`; the operator will scale RGW pods.
- **cephadm**:
  ```bash
  cephadm shell -- ceph orch host label add <new-rgw-host> rgw
  cephadm shell -- ceph orch apply rgw rgw \
    --placement="2 ceph-rgw-1 ceph-rgw-2" \
    --spec '{"rgw_frontend_port": 8080}'
  ```

### 4.3 CRUSH hierarchy and failure domains

- After any node addition, verify the CRUSH map includes the new host:
  ```bash
  ceph crush overview
  ceph osd dump | grep failure_domain
  ```
- Add the new host to the failure domain if the site has racks:
  ```bash
  ceph crash set-failure-domain host <new-host>
  # or, with racks:
  ceph crash add-failure-domain host=<new-host> rack=<new-rack>
  ```

### 4.4 Device discovery

```bash
# On the new host, list block devices
lsblk -d -o NAME,SIZE,TYPE,ROTA,MODEL

# Wipe any stale signatures (cephadm will format, but clean start is safer)
wipefs -a /dev/sdb
```

### 4.5 OSD provisioning

- After the host is labeled and devices are identified, the OSD is created as described in §4.2.2.
- For Rook‑Ceph, the `CephCluster.spec.storage.nodes` list is the single source of truth; the operator watches the API and creates/removes OSDs automatically.
- For cephadm, `ceph orch apply osd` is the command; the orchestrator places the OSD container on the labeled host.

### 4.6 Capacity validation

```bash
# After the new OSD is up
ceph -s   # check `used` and `pg` stats
ceph osd df  # shows per‑OSD usage
ceph osd pool stats kube-rbd  # pool size, used, pgs

# Ensure no PGs are stuck unclean
ceph pg stat
```

If `pg_degraded` or `pg_backfill` appears, wait for backfill to complete before proceeding to the next operation.

*Reference: host preparation and device discovery from `docs/storage/ceph/cephadm-deployment.md` §1; CRUSH and failure domain from `docs/storage/ceph/crush-rules-documentation.md`; Rook node addition from `docs/storage/rook-ceph/rook-ceph.md` §E‑H.*

---
## 5. Removing a Ceph Node (both Rook‑Ceph and cephadm)

### 5.1 Pre‑removal health check

```bash
ceph -s        # must show HEALTH_OK or at most HEALTH_WARN
ceph osd df    # verify capacity headroom: at least one OSD's worth of free space after evacuation
ceph pg stat   # no `stuck unclean` or `degraded` PGs
```

### 5.2 Capacity headroom estimate

- Ensure the cluster has at least **one full OSD's worth of raw capacity** free after the node's data is redistributed. For a 3‑replica pool with N OSDs, removing one OSD reduces usable capacity by ~1/N of the raw total; plan accordingly.
- If free space is insufficient, consider rebalancing first: `ceph osd pool rebalance <pool>`.

### 5.3 OSD evacuation (cephadm) / OSD removal (Rook‑Ceph)

#### cephadm

```bash
# 1. Mark the OSD as out (stop accepting new writes, start moving data out)
ceph osd out <osd-id>

# 2. Wait for the OSD to become inactive and all PGs to become active+clean
watch ceph -s   # watch `pg_degraded` and `pg_acting` counts

# 3. Remove the OSD from the map (irreversible)
ceph osd remove <osd-id>

# 4. Optional: delete the host from cephadm inventory
cephadm shell -- ceph orch host rm <host-fqdn>
```

#### Rook‑Ceph

```bash
# 1. Patch the CephCluster to remove the node from spec.storage.nodes
kubectl -n rook-ceph patch cephcluster/rook-ceph \
  -p '{"spec":{"storage":{"nodes":[{"name":"<old-node>"},"devices":[{"name":"<device>"}]}}}}' \
  --type=merge   # or edit the YAML directly and apply

# 2. The operator will gracefully stop the OSD pod and rebalance PGs.
# 3. Verify:
kubectl -n rook-ceph get pods
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s
```

### 5.4 MON removal

- Only remove a MON host if the cluster still has >= 3 MONs and quorum is maintained, **or** if you are deliberately reducing the MON count (requires careful steps).
- **Reducing from 3 to 2**: first step down one MON, then `ceph mon remove <id>`; the remaining 2 form a quorum only if `mon_allow_2_mon` is set (not recommended). Prefer keeping 3 MONs.
- **cephadm**:
  ```bash
  ceph mon remove <mon-id>
  # Verify quorum
  ceph quorum_status
  ```
- **Rook‑Ceph**: edit `CephCluster.spec.mon.count` downward and apply; the operator will shut down the excess MON pod.

### 5.5 MDS and RGW considerations

- **MDS**: before removing the host, ensure `activeCount` ≤ remaining MDS instances. If removing the last MDS, CephFS goes read‑only; plan a maintenance window.
- **RGW**: ensure `instances` ≤ remaining RGW nodes. If removing an RGW node, drain its data first:
  ```bash
  ceph osd out <rgw-osd-id>
  # Then remove the RGW CR/OBJ store instance
  ```

### 5.6 Host removal (underlying machine)

- After all Ceph daemons on the host are `out` and `removed`, the host can be powered off or decommissioned.
- For cephadm: `cephadm shell -- ceph orch host rm <host-fqdn>` removes the host from the inventory and cleans up any remaining references.
- For Rook‑Ceph: simply delete the node from the K8s cluster; the operator will have already removed the OSD pods.

### 5.7 Post‑removal validation

```bash
ceph -s                # HEALTH_OK, no degraded PGs
ceph osd df            # capacity reflects the removed OSD(s)
ceph pg stat           # all PGs active+clean
kubectl get nodes      # the K8s node is gone (or Ready if only Ceph removed)
```

If any PG remains `degraded` or `unclean`, investigate missing OSD, CRUSH map mismatch, or insufficient capacity.

*Reference: removal procedures from `docs/storage/ceph/cephadm-deployment.md` §J (Recovery procedures); Rook OSD addition/removal from `docs/storage/rook-ceph/rook-ceph.md` §H‑I.*

---
## 6. Replacing Ceph Disks/OSDs (both models)

### 6.1 Failed disk identification

```bash
# Check OSDmap for failed/out OSDs
ceph osd dump | grep -E 'osd\.\d+.*down|out'

# Smart error check (cephadm)
cephadm shell -- ceph orch device ls

# Physical inspection: check SMART, logs, and link status
smartctl -a /dev/sdb  # if the device is /dev/sdb
```

### 6.2 `out` vs `destroy` semantics

| Action | Effect | When to use |
|---|---|---|
| `ceph osd out <id>` | Marks OSD as `out`, begins moving PGs off it. OSD stays in the map, can be `in` again. | Standard replacement; safe, reversible. |
| `ceph osd destroy <id>` | Permanently removes OSD from the map, reclaims its ID, and starts backfill immediately. | Disk is physically gone and will never be re‑added; use after `out` and data redistribution. |

**Procedure**: always `out` first, verify PGs are `active+clean` on remaining OSDs, then `destroy` if the disk is dead.

### 6.3 Backfill monitoring

After `out` → disk replacement → new OSD brought up:

```bash
# Watch backfill progress
watch ceph -s

# Check backfill status per OSD
ceph osd stat

# Verify no stuck PGs
ceph pg stat | grep -i 'stuck\|degraded\|backfill'
```

Backfill time depends on cluster size, network bandwidth, and I/O load. For a 3‑host, 9‑OSD cluster replacing one OSD, expect 30‑90 minutes under typical 10 GbE replication.

### 6.4 Device replacement (cephadm)

1. Physically replace the failed disk (or attach a new NVMe/SATA disk).
2. Wipe any residual signature (cephadm formats on apply, but a clean start helps):
   ```bash
   wipefs -a /dev/newdisk
   ```
3. Label the new host (if not already) and add the device:
   ```bash
   cephadm shell -- ceph orch host add <host> <ip>
   cephadm shell -- ceph orch host label add <host> osd
   cephadm shell -- ceph orch apply osd <host> --data-devices /dev/newdisk --db-devices /dev/nvme1n1
   ```
4. Verify the new OSD appears in `ceph osd tree` and `ceph -s`.
5. Run `ceph osd pool rebalance <pool>` if re‑balancing is needed.

### 6.5 Device replacement (Rook‑Ceph)

1. Add the new device entry under `CephCluster.spec.storage.nodes`:
   ```yaml
   - name: "node-new"
     devices:
       - name: "sdb"
         config:
           osdsPerDevice: "1"
   ```
2. Apply the CephCluster manifest; the operator creates the OSD pod on the new node.
3. Wait for the OSD to become `up` and `in`, and for PGs to re‑balance.
4. Optionally remove the old node from the `nodes` list after the new OSD is healthy.

### 6.6 CRUSH placement verification

```bash
# After the new OSD is up, confirm its CRUSH device entry
ceph osd dump | grep "<osd-id>"

# Check the CRUSH map for the new device
ceph crash ls

# Verify the failure domain is correct
ceph osd info <osd-id> | grep failure_domain
```

If the CRUSH map needs updating (e.g., new host added to a different rack), use `ceph crash add-failure-domain` or `ceph osd crush move` as needed.

### 6.7 Exit criteria

- `ceph -s` shows `HEALTH_OK` or only expected `HEALTH_WARN` (e.g., a brief `pg_degraded` while backfill finishes).
- `ceph osd df` reflects the new disk size and the updated raw capacity.
- `ceph pg stat` shows all PGs `active+clean`, no `backfill` or `recovery` in progress (or backfill finished with no errors).
- No `ceph osd` warnings about missing devices or CRUSH map inconsistencies.

### 6.8 Rollback

If the replacement fails part‑way through:

1. If the new OSD is `out` but not `destroy`, you can `ceph osd in <osd-id>` to bring it back into the cluster.
2. If the disk was `destroyed` but the physical disk is still present, you can re‑add it via `ceph orch apply osd` (cephadm) or by re‑creating the node entry (Rook‑Ceph) and running `ceph osd pool rebalance`.
3. If data integrity is suspect (e.g., backfill errors), restore from the last verified backup before proceeding.

*Reference: OSD replacement workflow from `docs/storage/ceph/cephadm-deployment.md` §I (Recovery procedures); Rook OSD lifecycle from `docs/storage/rook-ceph/rook-ceph.md` §H (Operations).*

---
## 7. Rook-Ceph: Operator Lifecycle, Node Placement, and K8s Integration

### 7.1 Operator lifecycle

| Phase | Action | Command / Note |
|---|---|---|
| **Install** | Apply CRDs → common → operator | `kubectl apply -f crds.yaml && kubectl apply -f common.yaml && kubectl apply -f operator.yaml` |
| **Initial CephCluster creation** | Define `cephVersion.image`, storage nodes, pools, services | Edit `cephcluster.yaml` and `kubectl apply -f cephcluster.yaml` |
| **Upgrade Rook operator** | Pull new operator image, rolling restart | `kubectl set image deployment/rook-ceph-operator rook-ceph-operator=<new-tag> -n rook-ceph` |
| **Upgrade Ceph daemon images** | Change `cephVersion.image` in CephCluster; operator orchestrates mon → mgr → osd → mds → rgw order | `kubectl patch cephcluster/rook-ceph -p '{"spec":{"cephVersion":{"image":"quay.io/ceph/ceph:v18.3.0"}}}' -n rook-ceph` |
| **Upgrade CSI driver** (if required) | Update CSI DaemonSet/Deployment image; consult Rook release notes | Often automatic via operator; manual if pinned version mismatch |

**Critical**: Never set a Ceph image version that the installed Rook release does not support. The Rook release notes list the supported Ceph version — this is the single most common cause of a broken Rook upgrade.

### 7.2 K8s node labels and OSD scheduling

- **Label storage nodes** so the operator knows where OSD pods may land:
  ```bash
  kubectl label node node1 node-role.kubernetes.io/storage=osd
  kubectl label node node2 node-role.kubernetes.io/storage=osd
  kubectl label node node3 node-role.kubernetes.io/storage=osd
  ```
- The `CephCluster.spec.storage.nodes` list uses **Kubernetes node names** as the `name` field. The operator maps each entry to a pod with a node selector matching that name.
- OSD pods have `priorityClassNames: [system-node-critical]` and `affinity`/`nodeSelector` derived from the `nodes` list. General workloads should not conflict.
- If a storage node is also a general worker, use **taints and tolerations** to keep OSD pods off unless explicitly desired.

### 7.3 PVC and StorageClass dependencies

| Resource | Dependency | Cleanup note |
|---|---|---|
| PVC bound to `ceph-rbd` | `replicapool` CephBlockPool + `client.csi-rbd` keyring | Deleting the PVC removes the RBD image; the pool persists. |
| PVC bound to `cephfs` | `myfs` CephFilesystem + MDS pods | Deleting the PVC unmounts the share; the filesystem and MDS remain. |
| StorageClass `ceph-rbd` | `replicapool` pool, CSI provisioner secret | Deleting the SC does **not** delete the pool or the underlying images. |
| StorageClass `ceph-rgw` | `my-store` CephObjectStore + RGW gateway | Deleting the SC leaves the RGW running; objects must be cleaned separately. |

**Best practice**: document the dependency chain in the platform runbook; before deleting a StorageClass, run a dry‑run to confirm no in‑use PVCs remain.

### 7.4 MON placement

- **3 MONs across 3 separate hosts** is the default and safest configuration.
- Do **not** co‑locate a MON with the only OSD of a pool (per §1.1 of `cephadm-deployment.md`).
- In Rook‑Ceph, the operator places MON pods on hosts with the `mon` label; ensure exactly 3 such hosts exist and that they are not also OSD hosts (unless co‑located per the allowed rules).

### 7.5 Kubernetes drain implications when OSDs are present

Before draining a K8s node that runs Ceph OSD pods:

1. **Evacuate OSDs** (Rook): the operator will automatically move OSDs off the node when the node is marked unschedulable, but it is safer to explicitly `ceph osd out <osd-id>` first.
2. **For cephadm**: `ceph osd out <osd-id>` → wait for `inactive` → then `kubectl drain <node>`.
3. **Verify** all OSDs on the node are `out` and the pod is terminated before draining.
4. **After maintenance**, re‑add the node: for Rook‑Ceph, re‑apply the CephCluster with the node re‑added to `spec.storage.nodes`; for cephadm, `cephadm shell -- ceph orch host add` and relabel.

Failure to evacuate OSDs first can result in the node getting stuck in `NotReady`, OSDs going `down`, and PGs entering a `degraded` state.

### 7.6 Relationship between K8s node lifecycle and Ceph node lifecycle

| K8s action | Ceph impact | Required Ceph step |
|---|---|---|
| **Add K8s node** | New node is unknown to Ceph; no OSDs on it yet. | Add entry to `CephCluster.spec.storage.nodes` (Rook) **or** `ceph orch host add` (cephadm); then add devices and OSDs. |
| **Remove K8s node** | If the node runs OSDs, those OSDs must be `out` and `removed` first; otherwise the node drain will fail and OSDs will go `down`. | `ceph osd out <id>` → `ceph osd remove <id>` (cephadm) or patch `CephCluster` to remove the node (Rook). |
| **Upgrade K8s OS / reboot** | OSD processes depend on the underlying disk; a reboot without `ceph osd out` can cause PGs to become `degraded`. | Use `ceph osd out <osd-id>` before the reboot; the OSD will come back `in` when the host returns. |
| **Node taint/add‑toleration** | OSD pods may be repelled if the taint is not tolerated. | Ensure OSD pods have the matching toleration, or use `node-role.kubernetes.io/storage=:` taint to isolate storage nodes. |

### 7.7 Entry criteria for this section

- The Rook‑Ceph or cephadm cluster is healthy (`ceph -s` / `kubectl -n rook-ceph get pods`).
- The decision matrix (Section 1) has been documented and signed off.
- For Rook‑Ceph: the `CephCluster` manifest is applied and all CRDs are installed.
- For cephadm: the bootstrap is complete, hosts are labeled, and OSDs are created.

### 7.8 Ordered steps (summary)

1. **Select deployment model** (Section 1) and document.
2. **Apply operator / bootstrap** per the chosen model.
3. **Define storage nodes, devices, pools, Filesystem, RGW, StorageClasses**.
4. **Validate** with `ceph -s`, `kubectl get storageclass`, PVC test (Sections 2.5, 3.7).
5. **Add/remove/replace nodes** using the procedures in Sections 4‑6, always verifying health after each step.
6. **Drain/K8s node maintenance** only after OSDs are evacuated (Section 7.5).
7. **Upgrade path**: Rook operator → Ceph image → CSI driver (Section 7.1).
8. **Rollback**: if any step fails, revert to the last known‑good CephCluster/cephadm state and re‑run the failed step; keep backups of the `ceph` config and keyring.

### 7.9 Exit criteria for the phase

- All seven sub‑sections are complete and reviewed.
- Validation commands produce the expected healthy state (`HEALTH_OK`, all PGs `active+clean`).
- Node lifecycle (add/remove/replace) has been exercised at least once in a non‑production context or with approval.
- Rollback procedures are documented and the team is familiar with them.
- The DBRE and platform architect sign off that the storage lifecycle meets the RPO/RTO targets and the disaster‑recovery drills requirement.

*Reference: operator lifecycle and best practices from `docs/storage/rook-ceph/rook-ceph.md`; cephadm bootstrap and host management from `docs/storage/ceph/cephadm-deployment.md`; CRUSH and failure domain from `docs/storage/ceph/crush-rules-documentation.md`; MON/MDS/RGW placement from `docs/storage/ceph/mon-osd-crush-pools.md`; storage alternatives comparison from `docs/storage/alternatives/storage-alternatives.md`; offline artifact matrix from `docs/offline-artifacts/artifact-matrix.md` and `docs/offline-artifacts/nexus-deployment.md`.*

---
## Change Log

| Date | Change | Author |
|---|---|---|
| 2026‑11‑27 | Initial creation of Phase 3 storage lifecycle guide | DBRE specialist / Hermes subagent |

---
*End of Phase 3 — Ceph & Rook-Ceph Storage Lifecycle*
