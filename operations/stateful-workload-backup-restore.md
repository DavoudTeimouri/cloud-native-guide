# Section 5: Stateful Workloads & Persistent Data

## Velero Architecture & Mechanisms

Velero (formerly Heptio Ark) provides cluster-level backup and restore for Kubernetes resources and persistent volumes. It is the standard tool for Kubernetes-native data protection.

### Core Components

| Component | Function |
|---|---|
| **Velero Server** | Stores backup objects, processes backup/restore requests, serves API |
| **Velero Restic CSI Driver** (or native CSI snapshot driver) | Creates volume snapshots at the storage layer |
| **Velero Agent** | Runs on nodes to orchestrate volume snapshots and data moves |
| **Backup Storage Location** | Object storage (S3, GCS, Azure Blob, Ceph RGW) where backup manifests and snapshots are stored |
| **Velero Schedule** | Defines when automated backups run (cron-style) |

### Backup Workflow

1. Velero API receives `velero backup create` request.
2. Velero lists all namespaced cluster-scoped and namespaced resources in the included namespaces.
3. For each PVC with a supported CSI driver, Velero triggers a volume snapshot.
4. Velero uploads the resource manifest (JSON) and volume snapshot metadata to the backup storage location.
5. The backup job completes; status is stored in etcd (Velero server) and reported via `velero backup get`.

### Restore Workflow

1. `velero restore create --from-backup <name>` is issued.
2. Velero downloads the resource manifests and snapshots from backup storage.
3. Velero creates K8s objects (deployments, services, ConfigMaps, etc.) from the manifests.
4. Velero restores PVCs from the volume snapshots (or re-creates PVCs if using backup-only mode without snapshots).
5. Pods are scheduled; applications start with restored data.

> **Critical**: Velero backs up **K8s object definitions**, not application data directly. A manifest backup alone does not guarantee application data recoverability.

## K8s Object Backups vs Data Backups

| Backup Type | What It Captures | Recoverability |
|---|---|---|
| **Manifest backup** (Velero default) | K8s object YAML (Deployments, Services, ConfigMaps, RBAC, etc.) | Recovers object definitions; does NOT recover database data, application state, or files on PVCs unless combined with volume snapshots. |
| **Volume snapshot** (CSI) | Point-in-time copy of block storage behind a PVC | Recovers the filesystem state at snapshot time, but only if the driver and application support crash-consistent or app-consistent snapshots. |
| **Application-native backup** | DB dump, file archive, rsync, etc. | Guarantees application-consistent data; must be restored into the application (separate from K8s object restore). |
| **Replication** (DB replication, CRDT, etc.) | Ongoing data sync between replicas | NOT a backup. A logical error or data corruption propagates instantly; no point-in-time recovery without additional mechanisms. |

> **Rule of thumb**: Assume every backup is invalid until you have restored it into an isolated environment and verified application data integrity. A successful backup job ≠ recoverable data.

## CSI Snapshot Integration

### Supported CSI Drivers

Not all CSI drivers support snapshot identical behavior. Refer to the driver-specific documentation for snapshot capabilities, quiescence, and limitations.

| CSI Driver | Snapshot Support | Quiescence | Notes |
|---|---|---|---|
| **Ceph RBD** | Yes | Optional (freeze/thaw via virtiofs) | `csi-rbd-plugin` supports snapshots; may require `fsfreeze` for app consistency. |
| **Ceph FS** | Yes | N/A | Snapshots are copy-on-write; multiple snapshots can degrade performance. |
| **EBS (AWS)** | Yes | Yes (builtin) | AWS EBS-create-snapshot handles freeze/thaw internally. |
| **GPD (GCE PD)** | Yes | Yes (builtin) | Similar to EBS; integrated with GCE guest filesystem. |
| **Azure Disk** | Yes | Yes (builtin) | Azure snapshot agent handles quiescence. |
| **NetApp Trident** | Yes | Optional | Driver-dependent; Trident 21.08+ adds app-consistency support. |
| **OpenEBS / Mayastor** | Limited | N/A | Mayastor snapshots are volume-level; application consistency requires external mechanisms. |

### Snapshot Flags in Velero

```yaml
# Velero schedule with snapshotVolumes=true
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"
  ttl: 720h
  includedNamespaces:
    - "*"
  snapshotVolumes: true     # <-- triggers CSI snapshot per PVC
  storageLocation: default
```

- `snapshotVolumes: true` — creates a CSI snapshot for each PVC. If the CSI driver does not support snapshots, the backup job will fail or skip the volume.
- `snapshotVolumes: false` — only backs up K8s object manifests; PVC data is not captured.

> **Do NOT assume all CSI drivers support identical snapshot behavior**. Validate the snapshot capability of your specific driver before relying on volume snapshots for recovery.

## App-Consistent Backups

CSI snapshots provide filesystem-point-in-time copies, but they are not always application-consistent. Applications with in-flight writes may have corruption after a snapshot if the filesystem was not quiesced.

### Quiescence Mechanisms

| Mechanism | When Used | How It Works |
|---|---|---|
| **Built-in driver freeze** | EBS, GPD, Azure Disk | Driver internally freezes the filesystem, takes snapshot, thaws. No user action needed. |
| **fsfreeze** | Generic (RBD, others) | `xfs_freeze` or `fsfreeze` utility freefs the filesystem before snapshot; `thaw` after. |
| **Velero `--labels` / annotations** | Per-PVC control | Annotate PVCs with `velero.io/fs-freeze-"true"` if the driver supports it. |
| **Application-level dump** | Databases (PostgreSQL, MySQL, MongoDB) | Use `pg_dump`, `mysqldump`, or `mongodump` outside of K8s; store the dump as a backup artifact. | 

### App-Consistency Verification

After a restore from a snapshot-based backup, run application-level checks:

- For databases: row counts, checksums, and a small set of smoke queries comparing known values.
- For stateful apps: verify configuration files, runtime state, and that the service starts successfully.
- For file-based apps: compare a sample of files against known-good baselines.

## DB-Native Backup vs Volume Snapshots

| Approach | Captures | Restore Target | RPO | RTO |
|---|---|---|---|---|
| **Volume snapshot** (CSI) | Block-layer image of PVC | New PVC attached to a pod; filesystem restored to snapshot time | Minutes | Minutes to hours (depends on rebuild) |
| **DB-native dump** (pg_dump, mysqldump) | Logical database data | New database instance; data imported via SQL | Seconds (frequency) | Minutes to hours (import time) |
| **Combined** (Velero + DB dump) | Both K8s objects + DB dump | Full application stack recovery | Best of both | Best of both |

> **Recommendation**: For databases, use DB-native backup (dump/archive) in addition to Velero volume snapshots. A volume snapshot alone does not guarantee a consistent database restore — WAL replay or dump restore is required.

## PVC / PV Recovery

When restoring PVCs from snapshots or backups, the recovery path depends on the mechanism used.

### Restore from CSI Snapshot

```bash
# Create a new PVC from a snapshot (driver-specific)
kubectl create -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restored-pvc
spec:
  storageClassName: ceph-rbd
  dataSource:
    name: <snapshot-name>
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF
```

### Restore from Velero Backup

Velero automatically restores the original PVCs when restoring namespaced resources. If the original PV is deleted or the storage class changed, Velero may recreate PVCs with a new storage class (if configured).

### PV Recovery Considerations

- **Original storage class preserved** — if the same SC exists in the target cluster, the PV binds automatically.
- **Storage class migration** — if the target cluster has a different SC, Velero can re-bind the PV (configure via `backup storage location` settings).
- **Data source snapshot** — if restoring from a snapshot, the snapshot must be available in the target cluster's storage system.
- **PersistentVolume reclaim policy** — `Retain` preserves data after PVC deletion; `Delete` removes the underlying volume.

## Restore Ordering & Dependency Handling

When restoring a cluster from backup, restore ordering matters for applications with startup dependencies.

### Recommended Restore Order

1. **Core infrastructure** (DNS, networking, storage classes, secrets).
2. **Etcd/restore control plane** (if not already done).
3. **Observability stack** (Prometheus, Grafana, Alertmanager).
4. **System namespaces** (kube-system, kube-public).
5. **Application namespaces** — in dependency order (databases first, then supporting services, then front-end apps).
6. **Namespaces with `velero.io/optimize` annotations** — Velero respects these for incremental restore.

### Namespace / App-Level Recovery

```bash
# Restore specific namespace
velero restore create --from-backup <backup-name> --include-namespaces <namespace>

# Restore specific resources (label selector)
velero restore create --from-backup <backup-name> --selector app=<app-name>

# Restore with resource exclusions
velero restore create --from-backup <backup-name> --exclude-resources='events,events.events.k8s.io'
```

### Velero Restore Annotations

| Annotation | Effect |
|---|---|
| `velero.io/skip-namespaces` | Namespaces listed are skipped during restore. |
| `velero.io/do-not-backup` | Resources matching this label are excluded from future backups. |
| `cluster.k8s.io/ported-from` | Helps track which cluster a resource originated from during migrate/restore. |

## Redis Example: Persistence, Backup, Recovery, Validation

Redis is a common stateful workload in K8s. Its backup strategy depends on the persistence configuration.

### Redis with RDB Persistence (snapshots)

| Configuration | Backup Mechanism | Restore Steps |
|---|---|---|
| `appendonly no`, `save 60 1000` | Velero volume snapshot of PVC + RDB file | 1. Restore PVC from snapshot. <br>2. Start Redis pod. <br>3. Verify RDB loads: `INFO keyspace`. |
| `appendonly yes` | Velero volume snapshot + AOF rewrite | 1. Restore PVC from snapshot. <br>2. Start Redis pod. <br>3. Verify AOF integrity: `DEBUG RELOAD`. |
| **Redis replica** | Replication is NOT a backup. | Promoting a lagging replica loses writes. Always use Velero + RDB/AOF. |

### Redis Backup Best Practice

```yaml
# Velero schedule with Redis-labeled PVCs
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: redis-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"
  ttl: 720h
  includedNamespaces:
    - redis
  snapshotVolumes: true
  storageLocation: default
```

After restore:

```bash
# Verify Redis data
redis-cli -h <pod> KEYS "*"
redis-cli -h <pod> GET my-key

# Compare against expected values
# Run a smoke test: set a known value, read it back, delete it
```

> **Key point**: Redis RDB/AOF files on disk are the data. A volume snapshot captures the PVC state, but if the Redis process wrote data after the snapshot was taken but before the crash, that data may be lost. Always verify data after restore.

## Distinguishing Backup Types

| Statement | Truth |
|---|---|
| "Manifest backup = data backup" | **False**. Manifests only recover object definitions. |
| "Volume snapshot = app-consistent" | **False**. Snapshots are filesystem-point-in-time; application data consistency depends on quiescence. |
| "Replication = backup" | **False**. Replication synchronizes data in real time; it does not provide point-in-time recovery or protection against logical corruption. |
| "Restoring objects = recoverable app data" | **False**. Objects are recovered, but application data (DB contents, files, caches) must be restored separately. |

> **Always treat manifest backups and volume snapshots as incomplete**. Combine with application-native backups for full recoverability.

---
*Status: DRAFT | Owner: Platform Team | Last reviewed: 02026-11-23*