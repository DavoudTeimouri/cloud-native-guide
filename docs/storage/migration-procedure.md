# Storage Migration Procedure

## A. Purpose and scope

Document storage migration patterns: PVC migration between StorageClasses, pool migration, and data evacuation. Cross-references `storage/storageclass-design.md`, `storage/pvc-lifecycle.md`, `storage/ceph/cephadm-deployment.md`, `storage/rook-ceph/rook-ceph.md`.

## B. PVC Migration Between StorageClasses

Migrating a PVC from one StorageClass to another requires data copy, not just a label change. The safest approach is online copy using `kubectl cp` or a CSI migration tool.

### 1. Create the target PVC in the new StorageClass

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-pvc-new
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ceph-rbd-fast
  resources:
    requests:
      storage: 50Gi
```

### 2. Copy data from the old PVC to the new PVC

```bash
# Get the pod name that owns the old PVC
POD_NAME=$(kubectl get pods -l app=myapp -o name | head -1)

# Copy data out of the old PVC and into the new one
kubectl cp ${POD_NAME}:/data ./
kubectl cp ./ ${POD_NAME}:/data
```

### 3. Update the application to use the new PVC

Either:
- Recreate the pod with the new PVC selector
- Update the Deployment to reference `app-pvc-new`
- Swap PVC names in the volume definition

### 4. Delete the old PVC (after confirming data is accessible in the new PVC)

```bash
kubectl delete pvc app-pvc-old
```

**Important**: The PV from the old PVC remains in the cluster (reclaimPolicy determines if it's deleted or retained). Monitor PV reclamation.

**Alternative: RBD migration** (Ceph RBD-specific)

For Ceph RBD volumes, you can migrate using `rbd migrate`:

```bash
# On a host with ceph-cli installed
rbd migrate <pool>/<image> <target-pool>/<image> --flags incremental
```

## C. Pool Migration

Pool migration moves data between Ceph pools (e.g., from a HDD pool to an SSD pool, or from a replicated pool to an erasure-coded pool). This is an online operation via `ceph osd pool move`.

### 1. Prepare the source and target pools

Ensure the target pool exists and has sufficient capacity:

```bash
# Create target pool (replicated, size 3)
ceph osd pool create target-pool 64 64 replicated
ceph osd pool application enable target-pool rbd

# Or create erasure-coded pool
ceph osd pool create target-pool 64 64 erasure
```

### 2. Start the pool migration

```bash
# Move all PGs from source-pool to target-pool
ceph osd pool move source-pool target-pool --max 64
```

The `--max` flag sets the maximum number of PGs to move per iteration. Monitor progress:

```bash
# Check migration status
ceph osd pool migrate source-pool

# When the report shows 0/0, migration is complete
ceph osd pool stats source-pool target-pool
```

### 3. Verify migration completed

```bash
# Confirm source pool is empty
ceph osd pool pgmap source-pool | grep -c "active+clean"

# Confirm target pool has all data
ceph osd pool pgmap target-pool | grep -c "active+clean"
```

### 4. Delete the source pool (after verification)

```bash
ceph osd pool delete source-pool source-pool --yes-i-really-delete
```

**Important**: Pool migration rebalances data across OSDs. Monitor `ceph -s` for `HEALTH_WARN` about backfill or undersized PGs during the migration window.

## D. Data Evacuation

Data evacuation moves data off a specific OSD or node (e.g., for hardware maintenance). This uses `ceph osd drain` with strategic PG movement.

### 1. Mark the OSD for evacuation

```bash
# Allow new PGs to be placed elsewhere before draining
ceph osd set noout

# Optionally, reduce the PG count on the target OSD
ceph osd out <osd-id>
```

### 2. Move PGs off the OSD

```bash
# Begin moving PGs off the OSD
ceph osd rebalance

# Monitor rebalance progress
ceph osd pool rebalance <pool-name>

# Or use pagrab to manually grab specific PGs
ceph osd pagrab -n <pg-id>
```

### 3. Verify data is relocated

```bash
# Check OSD usage before and after
ceph osd df <osd-id>  # before
ceph osd df <osd-id>  # after — size should decrease

# Confirm PGs are no longer on this OSD
ceph osd dump | grep <osd-id>
```

### 4. Remove the OSD from the cluster

```bash
# After data is confirmed moved, shut down the OSD
systemctl stop ceph-osd@<osd-id>
systemctl disable ceph-osd@<osd-id>

# Remove the OSD from the Ceph map
ceph osd pool remove <pool> <osd-id> --yes-i-really-delete

# If replacing the disk, wipe and re-add the device
wipefs -a /dev/<device>
cephadm shell -- ceph orch apply osd <host> --data-devices /dev/<device>
```

**Important**: Always `ceph osd set noout` before and `ceph osd set noout` after evacuation to prevent cluster rebalancing from counteracting your moves. Monitor `ceph -s` for `HEALTH_OK` before proceeding with hardware changes.

## E. Cross-references

- `storage/storageclass-design.md` — StorageClass design (RBD vs CephFS, replication, compression, encryption, snapshot class, PVC binding modes)
- `storage/pvc-lifecycle.md` — PVC lifecycle: provisioning, binding, mounting, resizing, snapshotting, deletion, migration
- `storage/ceph/cephadm-deployment.md` — Ceph deployment via cephadm (preparation, OSDs, pools, monitoring)
- `storage/rook-ceph/rook-ceph.md` — Rook-Ceph operator (CRDs, installation, pools, filesystems, object store)
- `lifecycle/disaster-recovery/application-cluster.md` — Application recovery during storage incidents
