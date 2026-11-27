<a id="step-21"></a>
## Step 21 — Deployment Model Decision Matrix

**Purpose**: Select the Ceph deployment model (Rook-Ceph in-cluster or cephadm external) based on cluster locality, failure isolation, and multi-cluster consumption requirements, and document the choice for the Phase 3 gate.

**Prerequisites**:
- Kubernetes cluster deployed per Phase 1
- Administrative access to cluster and Ceph host(s)
- Record of RPO/RTO targets from DBRE spec (Section "Reliability Metrics & Guards")
- Internal container registry accessible for required images

**Actions**:
```bash
# 1. Write the deployment model decision matrix for stakeholder review
cat > /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/decision-matrix.md <<'MATRIX'
# Deployment Model Decision Matrix

## Rook-Ceph (in-cluster, operator-managed)
- Storage lives only inside the Kubernetes cluster
- Operator watches CRDs (`CephCluster`, `CephBlockPool`, `CephFilesystem`, `CephObjectStore`)
- Cluster-wide network/CNI failure can affect storage availability
- Native CRDs, CSI driver, PVC lifecycle fully managed inside Kubernetes
- Higher operational overhead — two control loops (Rook operator + ceph)
- Best for: cluster-local storage, simpler estates; no multi-cluster shared capacity

## cephadm (external dedicated hosts, CSI)
- Storage is a separate cluster of dedicated hosts, consumed by Kubernetes via external CSI driver
- `cephadm` bootstrap on dedicated hosts; OSDs, MONs, MGRs, MDS, RGW run as containers managed by the ceph orchestrator
- Storage is independent of the K8s CNI; network fault in K8s cluster does not impact Ceph hosts
- External CSI driver (cephcsi / csi-ceph) deployed as separate component; apps use standard PVCs
- Lower operational overhead — vendor lifecycle (ceph orch) handles daemon placement, upgrades, recovery
- Best for: shared capacity across multiple clusters; serving multiple K8s clusters; large estates with dedicated hardware

## Decision Rule
Choose Rook-Ceph when the storage requirement is *cluster-local* and the team wants a purely Kubernetes-centric lifecycle.
Choose cephadm when storage must survive the loss of the Kubernetes cluster, when serving multiple clusters, or when a dedicated hardware base is already in place.

## Multi-cluster Consumption
- Rook-Ceph: No — each cluster owns its own Rook-Ceph installation
- cephadm: Yes — the same external Ceph cluster can be consumed by many Kubernetes clusters

## Offline Artifact Volume
- Rook-Ceph: High (operator, CRDs, CSI images, Ceph daemon images)
- cephadm: Medium (cephadm bootstrap images, container engine, registry mirror)
MATRIX

# 2. Prompt for and record the selected model
read -p "Enter selected deployment model (rook-ceph/cephadm): " SELECTED_MODEL
if [ "$SELECTED_MODEL" = "rook-ceph" ]; then
  echo "Phase 3 deployment model: rook-ceph (in-cluster)" > /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/PHASE3_MODEL
elif [ "$SELECTED_MODEL" = "cephadm" ]; then
  echo "Phase 3 deployment model: cephadm (external dedicated hosts)" > /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/PHASE3_MODEL
fi
echo "Selected model: $SELECTED_MODEL"
```

**Validation**:
```bash
# Verify the model selection file was created and contains a valid value
SELECTED=$(cat /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/PHASE3_MODEL 2>/dev/null)
if [ "$SELECTED" = "rook-ceph" ] || [ "$SELECTED" = "cephadm" ]; then
  echo "PASS: Deployment model selected — $SELECTED"
else
  echo "FAIL: No valid deployment model selected"
fi
```
# Expected: Output confirms a valid model (rook-ceph or cephadm) is recorded

**Navigation**:
- Previous: Step 20 (anchor `#step-20`)
- Next: Step 22 (anchor `#step-22`)

<a id="step-22"></a>
## Step 22 — Rook-Ceph Deployment: Apply CRDs, Operator, and CephCluster

**Purpose**: Install the Rook operator and apply the CephCluster manifest with explicit storage nodes and devices (`useAllDevices: false`) to establish the in-cluster Ceph cluster.

**Prerequisites**:
- Phase 3 gate completed with deployment model selected (Step 21)
- Kubernetes cluster healthy and authenticated (`kubectl cluster-info` reachable)
- Internal container registry populated with required Ceph/Rook images per `offline-artifacts/artifact-matrix.md`
- Sudo access to cluster nodes for image preparation if needed

**Actions**:
```bash
# 1. Apply CRDs (must be first — CRD validation depends on them being present first)
kubectl apply -f https://github.com/rook/rook/releases/download/1.16.3/crds.yaml

# 2. Apply common components and operator
kubectl apply -f https://github.com/rook/rook/releases/download/1.16.3/common.yaml
kubectl apply -f https://github.com/rook/rook/releases/download/1.16.3/operator.yaml

# 3. Verify operator rollout completes within timeout
kubectl -n rook-ceph rollout status deployment/rook-ceph-operator --timeout=300s
```

**Validation**:
```bash
# 1. Check operator pod is Running
kubectl -n rook-ceph get pods -l app=rook-ceph-operator

# 2. Verify CRDs are installed
kubectl get crds | grep -c ceph.rook.io

# 3. Confirm operator rollout status
kubectl -n rook-ceph get deployment/rook-ceph-operator -o jsonpath='{.status.available}'
```
# Expected: `Available: "true"` from the operator deployment; CRD count > 0; operator pod `Ready`

**Navigation**:
- Previous: Step 21 (anchor `#step-21`)
- Next: Step 23 (anchor `#step-23`)

<a id="step-23"></a>
## Step 23 — Rook-Ceph Pools, StorageClasses, and CSI Validation

**Purpose**: Create the Ceph block/Filesystem/RGW pools, define StorageClasses that provision RBD/CephFS/RGW volumes, and validate end-to-end CSI functionality with a PVC storage test.

**Prerequisites**:
- Rook operator deployed and healthy (Step 22)
- CephCluster manifest applied with explicit storage nodes and devices (Step 22)
- Ceph daemons started and `ceph -s` returns `HEALTH_OK` or acceptable `HEALTH_WARN`

**Actions**:
```bash
# 1. Create the replicated CephBlockPool (replicated size 3, host failure domain)
kubectl -n rook-ceph apply -f - <<'EOF'
apiVersion: rook.io/v1
kind: CephBlockPool
metadata:
  name: replicapool
  namespace: rook-ceph
spec:
  failureDomain: host
  replicated:
    size: 3
EOF

# 2. Create the ceph-rbd StorageClass (default class for RBD block volumes)
kubectl apply -f - <<'EOF'
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
EOF

# 3. Create a test PVC and verify binding, then perform a write test
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

# 4. Wait for PVC to become Bound
kubectl wait --for=condition=Bound pvc/rook-test --timeout=120s

# 5. Run I/O test from a busybox pod
kubectl run rook-test-pod --image=busybox --restart=Never --command -- sh -c "echo 'test write' > /mnt/test && cat /mnt/test"
```

**Validation**:
```bash
# 1. Check cluster health via ceph -s (output must show HEALTH_OK or acceptable HEALTH_WARN)
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s | head -5

# 2. Verify the StorageClass is listed and default
kubectl get storageclass | grep ceph-rbd

# 3. Confirm PVC is Bound
kubectl get pvc rook-test -o jsonpath='{.status.phase}'
```
# Expected: `ceph-rbd` StorageClass listed with `is-default-class` annotation; PVC phase is `Bound`; `ceph -s` shows mon/osd/mgr processes healthy

**Navigation**:
- Previous: Step 22 (anchor `#step-22`)
- Next: Step 24 (anchor `#step-24`)

<a id="step-24"></a>
## Step 24 — cephadm External: Deploy on Dedicated Hosts Outside K8s

**Purpose**: Bootstrap a cephadm-managed Ceph cluster on dedicated hosts outside the Kubernetes cluster, configure OSDs and pools, and deploy the external CSI driver so Kubernetes workloads can consume Ceph storage.

**Prerequisites**:
- Phase 3 gate completed with cephadm model selected (Step 21)
- Internal OCI registry (`harbor.internal`, `nexus.internal`, or self-hosted) mirroring `quay.io/ceph` images reachable from all Ceph hosts
- Engine (Docker or Podman) installed and configured on all Ceph hosts for air‑gap pull from the internal registry
- All Ceph hosts prepared per OS, kernel, time, name resolution, disk, SSH, and network requirements

**Actions**:
```bash
# 1. Install cephadm on the bootstrap host (Oracle Linux example)
dnf install -y cephadm

# 2. Bootstrap the first host (MON) — pass --docker when using Docker; omit for Podman
cephadm --docker bootstrap \
  --mon-ip 10.40.0.11 \
  --cluster-network 10.41.0.0/24 \
  --registry harbor.internal \
  --log-to-file

# 3. Verify bootstrap — ceph -s must return HEALTH_OK
cephadm shell -- ceph -s

# 4. Add each remaining host to the ceph inventory
cephadm shell -- ceph orch host add ceph-mon-2 10.40.0.12
cephadm shell -- ceph orch host add ceph-mon-3 10.40.0.13
cephadm shell -- ceph orch host add ceph-osd-1 10.40.0.14
cephadm shell -- ceph orch host add ceph-osd-2 10.40.0.15
cephadm shell -- ceph orch host add ceph-osd-3 10.40.0.16

# 5. Label hosts by role
cephadm shell -- ceph orch host label add ceph-mon-1 mon
cephadm shell -- ceph orch host label add ceph-mon-2 mon
cephadm shell -- ceph orch host label add ceph-mon-3 mon
cephadm shell -- ceph orch host label add ceph-mgr-1 mgr
cephadm shell -- ceph orch host label add ceph-mgr-2 mgr
cephadm shell -- ceph orch host label add ceph-osd-1 osd
cephadm shell -- ceph orch host label add ceph-osd-2 osd
cephadm shell -- ceph orch host label add ceph-osd-3 osd

# 6. Define OSDs (explicit devices, one OSD per data disk)
cephadm shell -- ceph orch apply osd --all-available-devices
# Or per‑host:
# cephadm shell -- ceph orch apply osd ceph-osd-1 --data-devices /dev/sdb,/dev/sdc --db-devices /dev/nvme1n1

# 7. Create pools (replicated size 3, host failure domain)
cephadm shell -- ceph osd pool create kube-rbd 64 64 repl 3
cephadm shell -- ceph osd pool application enable kube-rbd rbd

# 8. Create CephFS (metadata + data pool)
cephadm shell -- ceph mgr module enable cephfs --force
cephadm shell -- ceph fs new cephfs cephfs_metadata cephfs_data

# 9. Enable RGW and assign instances
cephadm shell -- ceph mgr module enable rgw --force
cephadm shell -- ceph orch apply rgw rgw \
  --placement="2 ceph-rgw-1 ceph-rgw-2" \
  --spec '{"rgw_frontend_port": 8080}'
```

**Validation**:
```bash
# 1. Cluster health must show HEALTH_OK
ceph -s | head -10

# 2. Verify CSI driver pods are Running (cephcsi or csi-ceph namespace)
kubectl get pods -n rook-ceph -l app=ceph-csi

# 3. List StorageClasses created by the external CSI driver
kubectl get storageclass

# 4. PVC test — same as Rook‑Ceph example
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ceph-external-test
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
  storageClassName: ceph-external-rbd
EOF
kubectl wait --for=condition=Bound pvc/ceph-external-test --timeout=120s
```
# Expected: `ceph -s` returns `HEALTH_OK`; CSI driver pods Running; StorageClasses listed; PVC binds successfully

**Navigation**:
- Previous: Step 23 (anchor `#step-23`)
- Next: Step 25 (anchor `#step-25`)

<a id="step-25"></a>
## Step 25 — Adding a Ceph Node: Host Prep, Role Labeling, OSD Provisioning, and Capacity Validation

**Purpose**: Add a new Ceph node to either the Rook-Ceph or cephadm cluster, including host preparation, role labeling, OSD provisioning with explicit devices, CRUSH placement, and capacity validation.

**Prerequisites**:
- Existing Ceph cluster healthy (Step 22 or Step 24)
- New host meets OS, kernel, time, disk, and name-resolution requirements
- Dedicated data disks (XFS ftype=1) and separate NVMe/SATA for OSD DB/WAL available on the new host
- SSH access from bootstrap host to the new host

**Actions (Rook-Ceph path)**:
```bash
# 1. Prepare the new host: OS, kernel, chrony, /etc/hosts consistency, SSH
# (Host preparation steps are model-specific; see prerequisite docs)

# 2. Add the new node entry under CephCluster.spec.storage.nodes with explicit devices
cat > /tmp/newnode.yaml <<'EOF'
apiVersion: rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  namespace: rook-ceph
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v18.2.x
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
  storage:
    useAllNodes: false
    useAllDevices: false
    nodes:
      - name: "node-new"
        devices:
          - name: "sdb"
            config:
              osdsPerDevice: "1"
EOF

# 3. Apply the updated CephCluster manifest — Rook operator creates the OSD pod
kubectl -n rook-ceph patch cephcluster/rook-ceph -p "$(cat /tmp/newnode.yaml)" --type=merge

# 4. Verify the new OSD is up and in
kubectl -n rook-ceph get pods
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s | grep -E 'osd|PG'
```

**Actions (cephadm path)**:
```bash
# 1. Prepare the new host: install engine (Docker/Podman), add to /etc/hosts, synchronize time via chrony

# 2. Add the host to cephadm inventory and label it for OSD role
cephadm shell -- ceph orch host add <new-host-fqdn> <new-host-ip>
cephadm shell -- ceph orch host label add <new-host-fqdn> osd

# 3. Add data device(s) for OSD provisioning on the new host
cephadm shell -- ceph orch apply osd <new-host-fqdn> --data-devices /dev/sdb --db-devices /dev/nvme1n1

# 4. Verify the new OSD appears in the cluster tree
ceph osd tree | grep <new-osd-id>
```

**Validation**:
```bash
# 1. ceph -s must show the new OSD up and in, with PGs active+clean
ceph -s | grep -E 'osd|used|pgs'

# 2. ceph osd df must reflect the new disk capacity
ceph osd df

# 3. ceph osd pool stats must show updated pool size
ceph osd pool stats kube-rbd
```
# Expected: `ceph -s` shows new OSD ID `up` and `in`; `ceph osd df` includes the new disk size; pool stats reflect updated capacity

**Navigation**:
- Previous: Step 24 (anchor `#step-24`)
- Next: Step 26 (anchor `#step-26`)

<a id="step-26"></a>
## Step 26 — Removing a Ceph Node: Health Check, Capacity Headroom, OSD Evacuation, and Safe Removal

**Purpose**: Remove a Ceph node from the cluster with a validated health check, capacity headroom estimate, OSD evacuation (cephadm) or OSD removal (Rook-Ceph), CRUSH map updates, and post-removal validation to ensure no data loss or split-brain.

**Prerequisites**:
- Existing Ceph cluster healthy (`ceph -s` shows `HEALTH_OK` or at most `HEALTH_WARN`)
- Capacity headroom: at least one full OSD's worth of raw capacity free after evacuation/removal
- No PGs stuck in `unclean` or `degraded` state
- For cephadm: OSDs marked `out` and data redistributed; for Rook-Ceph: node patched out of `spec.storage.nodes`

**Actions (cephadm path)**:
```bash
# 1. Pre-removal health check
ceph -s
ceph osd df
ceph pg stat

# 2. Estimate capacity headroom — ensure at least one OSD's worth of raw capacity is free
# If insufficient, rebalance pools first: ceph osd pool rebalance <pool>

# 3. Mark the OSD as out (stop accepting new writes, begin moving PGs off)
ceph osd out <osd-id>

# 4. Wait for the OSD to become inactive and all PGs to become active+clean
watch ceph -s  # watch pg_degraded and pg_acting counts

# 5. Remove the OSD from the map (irreversible — reclaims the OSD ID)
ceph osd remove <osd-id>

# 6. Remove the host from cephadm inventory
cephadm shell -- ceph orch host rm <host-fqdn>
```

**Actions (Rook-Ceph path)**:
```bash
# 1. Pre-removal health check
ceph -s
ceph osd df
ceph pg stat

# 2. Patch the CephCluster to remove the node from spec.storage.nodes (operator will gracefully stop the OSD pod and rebalance PGs)
kubectl -n rook-ceph patch cephcluster/rook-ceph \
  -p '{"spec":{"storage":{"nodes":[{"name":"<old-node>"},"devices":[{"name":"<device>"}]}}}}' \
  --type=merge

# 3. Verify the operator has stopped the OSD pod and rebalanced PGs
kubectl -n rook-ceph get pods
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s
```

**Validation**:
```bash
# 1. ceph -s must show HEALTH_OK, no degraded PGs
ceph -s | grep -E 'HEALTH|pgs'

# 2. ceph osd df must reflect the removed OSD(s) and updated capacity
ceph osd df

# 3. ceph pg stat must show all PGs active+clean
ceph pg stat | grep -i 'stuck\|degraded'

# 4. For cephadm: host removed from inventory
cephadm shell -- ceph orch host ls | grep -c <host-fqdn>
```
# Expected: `HEALTH_OK` or acceptable `HEALTH_WARN`; `ceph osd df` shows reduced raw capacity with removed OSD(s) accounted for; `ceph pg stat` shows all PGs `active+clean`; host no longer in cephadm inventory (if cephadm path)

**Navigation**:
- Previous: Step 25 (anchor `#step-25`)
- Next: Step 27 (anchor `#step-27`)

<a id="step-27"></a>
## Step 27 — Replacing Ceph Disks/OSDs: Failed Disk Identification, out vs destroy, Backfill Monitoring, and Device Replacement

**Purpose**: Identify a failed Ceph disk/OSD, mark it `out`, replace the physical device, and bring the new OSD online while monitoring backfill progress and verifying CRUSH placement. Includes rollback procedures if the replacement fails part-way through.

**Prerequisites**:
- Existing Ceph cluster healthy; the failed OSD is identified as `down` or `out` in `ceph osd dump`
- Physical replacement disk available (same model or larger capacity)
- For cephadm: engine (Docker/Podman) access to the host; for Rook-Ceph: SSH access to the node

**Actions (cephadm path — out → destroy → replace)**:
```bash
# 1. Failed disk identification
# Check OSD map for down/out OSDs and correlate with physical disk
ceph osd dump | grep -E 'osd\.\d+.*down|out'
cephadm shell -- ceph orch device ls

# 2. Physical inspection: check SMART, logs, and link status
smartctl -a /dev/sdb  # if the device is /dev/sdb

# 3. Mark the failed OSD as out (standard replacement; safe, reversible)
ceph osd out <osd-id>

# 4. Verify PGs are active+clean on remaining OSDs before proceeding
watch ceph -s  # monitor pg_degraded and pg_acting counts

# 5. Physically replace the failed disk (or attach a new NVMe/SATA disk)
# 6. Wipe any residual disk signature (cephadm formats on apply, but clean start helps)
wipefs -a /dev/newdisk

# 7. Add the new device and bring the OSD back online
cephadm shell -- ceph orch host add <host> <ip>
cephadm shell -- ceph orch host label add <host> osd
cephadm shell -- ceph orch apply osd <host> --data-devices /dev/newdisk --db-devices /dev/nvme1n1

# 8. Monitor backfill progress until all PGs are active+clean
watch ceph -s
ceph osd stat
```

**Actions (Rook-Ceph path — out → add node entry → apply → remove old)**:
```bash
# 1. Failed disk identification (same as cephadm)
ceph osd dump | grep -E 'osd\.\d+.*down|out'

# 2. Mark the OSD as out (standard replacement; safe, reversible)
ceph osd out <osd-id>

# 3. Wait for PGs to become active+clean on remaining OSDs
watch ceph -s

# 4. Add the new device entry under CephCluster.spec.storage.nodes
cat > /tmp/newnode.yaml <<'EOF'
- name: "node-new"
  devices:
    - name: "sdb"
      config:
        osdsPerDevice: "1"
EOF

# 5. Apply the updated CephCluster manifest — operator creates the OSD pod on the new node
kubectl -n rook-ceph patch cephcluster/rook-ceph -p "$(cat /tmp/newnode.yaml)" --type=merge

# 6. Wait for the new OSD to become up and in, and for PGs to re-balance
kubectl -n rook-ceph get pods
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s

# 7. Optionally remove the old node from the nodes list after the new OSD is healthy
kubectl -n rook-ceph patch cephcluster/rook-ceph -p '{"spec":{"storage":{"nodes":[{"name":"<old-node>"}]}}}' --type=merge -o yaml | grep -A5 storage
```

**Validation**:
```bash
# 1. ceph -s must show HEALTH_OK or only expected HEALTH_WARN (brief pg_degraded while backfill finishes)
ceph -s | head -5

# 2. ceph osd df must reflect the new disk size and updated raw capacity
ceph osd df

# 3. ceph pg stat must show all PGs active+clean, no backfill or recovery in progress (or backfill finished with no errors)
ceph pg stat | grep -i 'stuck\|degraded\|backfill'

# 4. No ceph osd warnings about missing devices or CRUSH map inconsistencies
ceph crash ls
```
# Expected: `ceph -s` shows `HEALTH_OK`; `ceph osd df` includes the new disk size; `ceph pg stat` shows all PGs `active+clean`; no CRUSH map inconsistencies

**Rollback (if replacement fails part-way through)**:
```bash
# 1. If the new OSD is out but not destroy, bring it back in: ceph osd in <osd-id>
# 2. If the disk was destroyed but the physical disk is still present, re-add via ceph orch apply osd (cephadm) or by re-creating the node entry (Rook-Ceph) and running ceph osd pool rebalance
# 3. If data integrity is suspect, restore from the last verified backup before proceeding
```
# Expected: Rollback steps documented; if executed, cluster returns to last known‑good state

**Navigation**:
- Previous: Step 26 (anchor `#step-26`)
- Next: Step 28 (anchor `#step-28`)

<a id="step-28"></a>
## Step 28 — Rook-Ceph Operator Lifecycle: Upgrade Sequence, K8s Node Labels, and OSD Scheduling

**Purpose**: Manage the Rook-Ceph operator lifecycle including upgrade sequencing (Rook operator → Ceph daemon image), K8s node labeling for OSD scheduling, and affinity/node‑selector rules so OSD pods land on dedicated storage nodes.

**Prerequisites**:
- Rook-Ceph cluster healthy (Step 22 or Step 25)
- New Ceph/Rook operator images available in the internal container registry
- K8s nodes labeled for storage role exist and are Ready

**Actions**:
```bash
# 1. Upgrade the Rook operator — pull new operator image and rolling restart
kubectl set image deployment/rook-ceph-operator rook-ceph-operator=<new-operator-tag> -n rook-ceph

# 2. Upgrade Ceph daemon images — change the cephVersion.image in CephCluster; operator orchestrates mon → mgr → osd → mds → rgw order
kubectl patch cephcluster/rook-ceph -p '{"spec":{"cephVersion":{"image":"quay.io/ceph/ceph:v18.3.0"}}}' -n rook-ceph

# 3. Verify the upgrade sequence completes — operator must support the target Ceph version
kubectl -n rook-ceph get pods | grep -E 'rook-ceph-operator|rook-ceph-mon|rook-ceph-osd'
# Critical: Never set a Ceph image version that the installed Rook release does not support — consult Rook release notes first.

# 4. Label K8s storage nodes so the operator knows where OSD pods may land
kubectl label node node1 node-role.kubernetes.io/storage=osd
kubectl label node node2 node-role.kubernetes.io/storage=osd
kubectl label node node3 node-role.kubernetes.io/storage=osd

# 5. Verify OSD pod scheduling — OSD pods have priorityClassNames: system-node-critical and node‑selector derived from CephCluster.spec.storage.nodes
kubectl -n rook-ceph get pods -l app=rook-ceph-osd
```

**Validation**:
```bash
# 1. Operator rollout status after image update
kubectl -n rook-ceph rollout status deployment/rook-ceph-operator --timeout=300s

# 2. Ceph cluster health after Ceph image upgrade
kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph -s | head -5

# 3. OSD pods are Running on the expected storage nodes
kubectl -n rook-ceph get pods -l app=rook-ceph-osd -o wide | grep -E 'NODE_NAME|READY'
```
# Expected: Operator rollout completes; `ceph -s` shows HEALTH_OK after upgrade; OSD pods Running on labeled storage nodes

**Navigation**:
- Previous: Step 27 (anchor `#step-27`)
- Next: Step 29 (anchor `#step-29`)

<a id="step-29"></a>
## Step 29 — K8s Node Drain Implications and K8s↔Ceph Node Lifecycle Relationship

**Purpose**: Document the K8s node drain procedures when OSDs are present, and convert the K8s node lifecycle ↔ Ceph node lifecycle relationship from a reference table into explicit procedural steps so that node maintenance cannot induce PG degradation or data loss.

**Prerequisites**:
- Ceph cluster healthy (`ceph -s` shows `HEALTH_OK` or acceptable `HEALTH_WARN`)
- For Rook-Ceph: OSDs are explicitly `out` before drain; for cephadm: `ceph osd out <osd-id>` completed and PGs redistributed
- K8s node is schedulable (not marked Unschedulable) unless drain is intentional

**Actions (K8s node drain when OSDs are present)**:
```bash
# 1. (Rook-Ceph) Explicitly evacuate OSDs off the node before draining
#    The operator will automatically move OSDs, but it is safer to explicit:
ceph osd out <osd-id>  # for each OSD on the node being drained

# 2. Verify all OSDs on the node are `out` and the pod is terminated
kubectl -n rook-ceph get pods | grep <node-name>
# All OSD pods on the node should show `Terminated` or `Completed`

# 3. Drain the K8s node (force if OSDs already evacuated)
kubectl drain <node-name> --ignore-daemonsets --delete-empty-data

# 4. (cephadm path) Same pattern: `ceph osd out <osd-id>` → wait for inactive → `kubectl drain <node>`

# 5. After maintenance, re‑add the node:
#   - Rook-Ceph: re‑apply the CephCluster with the node re‑added to spec.storage.nodes
#   - cephadm: `cephadm shell -- ceph orch host add <fqdn> <ip>` + relabel + `ceph orch apply osd`

# 6. Verify the node returns to Ready status and OSDs come back in
kubectl get nodes <node-name>
ceph -s | grep -E 'osd|PG'
```

**Actions (K8s↔Ceph node lifecycle relationship — converted from reference table to steps)**:
```bash
# K8s action                    → Ceph impact                    → Required Ceph step

# Add K8s node                  → New node is unknown to Ceph; no OSDs on it yet
#   → Add entry to CephCluster.spec.storage.nodes (Rook)
#   → Or: ceph orch host add (cephadm)
#   → Then add devices and OSDs

# Remove K8s node               → If the node runs OSDs, those OSDs must be out and removed first
#   → ceph osd out <id> → ceph osd remove <id> (cephadm)
#   → Or: patch CephCluster to remove node (Rook)
#   → Only then can the K8s node be drained and deleted

# Upgrade K8s OS / reboot       → OSD processes depend on the underlying disk
#   → Use ceph osd out <osd-id> before the reboot
#   → The OSD will come back in when the host returns

# Node taint/add‑toleration     → OSD pods may be repelled if the taint is not tolerated
#   → Ensure OSD pods have the matching toleration
#   → Or use node-role.kubernetes.io/storage=: taint to isolate storage nodes
```

**Validation**:
```bash
# 1. Before drain: all OSDs on the node are out, pods terminated, ceph -s shows HEALTH_OK
ceph -s | head -3

# 2. After drain and maintenance: node is Ready, OSDs are back in
kubectl get nodes <node-name> | grep Ready
ceph -s | grep -E 'osd|PG'

# 3. PGs are all active+clean after the node return
ceph pg stat | grep -i 'active+clean'
```
# Expected: Node drain completes without PG degradation; after node return, `ceph -s` shows HEALTH_OK and all PGs active+clean; tainted nodes tolerate OSD pods

**Navigation**:
- Previous: Step 28 (anchor `#step-28`)
- Next: Step 30 (anchor `#step-30`)

<a id="step-30"></a>
## Step 30 — Storage Validation Exit Criteria and Rollback Procedures

**Purpose**: Define the exit criteria for the storage lifecycle phase, including measured RPO/RTO verification, validated restore drills, and documented rollback procedures that the DBRE and platform architect must sign off before the phase is closed.

**Prerequisites**:
- All previous steps (21‑29) completed and reviewed
- Ceph cluster healthy (`ceph -s` shows `HEALTH_OK`)
- Entry criteria from each step verified (deployment model selected, operator deployed, pools/SCs created, nodes add/remove/replace exercised)
- DBRE and platform architect available for sign‑off

**Actions**:
```bash
# 1. Record measured RTO from the most recent automated restore drill
#    (RTO target: <= 30 min; record actual measured time)
MEASURED_RTO=$(cephadm shell -- ceph tell mon.* 'pack get backup_rto' 2>/dev/null || echo "measure from drill log")
echo "Measured RTO: $MEASURED_RTO minutes"

# 2. Record measured RPO from the most recent backup restore point
#    (RPO target: <= 1 min continuous WAL archiving)
MEASURED_RPO=$(kubectl -n rook-ceph exec deploy/rook-ceph-operator -- ceph tell mon.* 'pack get backup_rpo' 2>/dev/null || echo "measure from backup log")
echo "Measured RPO: $MEASURED_RPO minutes"

# 3. Validate exit criteria — all of the following must pass:
#    a. ceph -s shows HEALTH_OK
ceph -s | grep 'HEALTH_OK' > /dev/null 2>&1

#    b. All PGs are active+clean
ceph pg stat | grep -q 'active+clean' && echo "PGs healthy"

#    c. All seven sub-sections (Steps 21‑30) are complete and reviewed
test -f /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/PHASE3_MODEL && echo "Model selected" || echo "Model not selected"

#    d. Rollback procedures documented for each operation (add/remove/replace OSD, drain, upgrade)
test -f /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/ROLLBACK_PROCEDURES.md && echo "Rollback docs exist" || echo "Rollback docs missing"

#    e. DBRE and platform architect sign‑off recorded
read -p "DBRE sign-off (yes/no): " DBRE_SIGNOFF
read -p "Platform architect sign-off (yes/no): " ARCH_SIGNOFF
if [ "$DBRE_SIGNOFF" = "yes" ] && [ "$ARCH_SIGNOFF" = "yes" ]; then
  echo "Phase 3 sign-off complete"
  echo "DBRE: $DBRE_SIGNOFF, Architect: $ARCH_SIGNOFF" >> /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/PHASE3_SIGNOFF
else
  echo "FAIL: Sign-off required from both DBRE and platform architect"
  exit 1
fi
```

**Validation**:
```bash
# 1. Exit criteria gate — all checks must pass
CEPH_HEALTH=$(ceph -s | grep 'HEALTH_OK' | wc -l)
PG_STATUS=$(ceph pg stat | grep -c 'active+clean')
MODEL_FILE=$(test -f /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/PHASE3_MODEL && echo "present" || echo "missing")
ROLLBACK_FILE=$(test -f /workspace/project/github/public-repository/cloud-native-guide/docs/deploy/ROLLBACK_PROCEDURES.md && echo "present" || echo "missing")

if [ "$CEPH_HEALTH" -ge 1 ] && [ "$PG_STATUS" -gt 0 ] && [ "$MODEL_FILE" = "present" ] && [ "$ROLLBACK_FILE" = "present" ]; then
  echo "PASS: All exit criteria met — Phase 3 ready for sign-off"
else
  echo "FAIL: One or more exit criteria not met"
  echo "  ceph -s HEALTH_OK: $CEPH_HEALTH"
  echo "  PG active+clean: $PG_STATUS"
  echo "  Model selection: $MODEL_FILE"
  echo "  Rollback procedures: $ROLLBACK_FILE"
fi
```
# Expected: All exit criteria pass (ceph -s HEALTH_OK, all PGs active+clean, model selection file present, rollback procedures present, both sign-offs recorded); gate outputs "PASS: All exit criteria met — Phase 3 ready for sign-off"

**Navigation**:
- Previous: Step 29 (anchor `#step-29`)
- Next: (anchor `#step-30-end`)

---

*End of Phase 3 — Ceph & Rook-Ceph Storage Lifecycle (Steps 21‑30)*
