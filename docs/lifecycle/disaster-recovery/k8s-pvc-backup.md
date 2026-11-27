# Kubernetes PVC Backup

## A. Velero Backup Configuration

Velero is the primary mechanism for backing up Kubernetes resources and PVCs. Without it, a cluster loss means complete workload data loss.

### Installation

```bash
# Install Velero with an object storage bucket (Ceph RGW, S3, or GCS)
velero install \
  --provider aws \
  --bucket velero-backups \
  --secret-file <credentials-file> \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1 \
  --use-restic
```

### Backup Criteria

| Resource | Included | Excluded | Notes |
|---|---|---|---|
| Namespaces | All | `kube-system`, `openshift-marketplace` | Exclude noisy namespaces |
| PVCs | All persistent volumes | Ephemeral inline volumes | Only bound PVs are backed up |
| Deployments, StatefulSets, DaemonSets | All | — | Resources are restored as manifests |
| ClusterRoles, RBAC | Excluded | — | Restored from cluster spec, not backup |
| PV metadata | Included | PV data | PV data is in the underlying storage snapshot |

### RPO and RTO targets

- **RPO**: ≤ 5 minutes (Velero periodic backup interval)
- **RTO**: ≤ 30 minutes (measured from backup restore drill; includes Velero restore + CSI reattachment + Argo CD sync)

### Velero backup schedule

```bash
# Create a Velero scheduled backup every 5 minutes
velero schedule create daily-backup \
  --schedule "every 5 minutes" \
  --include-namespaces "*" \
  --exclude-namespaces "kube-system,openshift-marketplace" \
  --label-selector app.integrations/backup=true \
  --ttl 24h0m0s
```

### Restic integration for pod files

Restic is required for backing up container volumes that are not managed by a CSI driver. Ensure each namespace has the label `app.integrations/backup=true` if you want Restic-backed inclusion.

## B. Snapshot Strategies

Velero snapshots alone only capture PVC metadata. The underlying block/storage snapshots provide the point-in-time data consistency.

### CSI driver snapshots (Ceph RBD, Ceph FS, EBS, GCSF, etc.)

```bash
# Trigger a manual volume snapshot via Velero
velero snapshot create manual-snapshot \
  --volume <pvc-name> \
  --snapshot-location <location-name>
```

### Snapshot cadence

| Tier | Frequency | Method | Retention |
|---|---|---|---|
| On-node rolling | Every 5 min | `etcdctl` snapshot (separate from Velero) | 7 most recent per node |
| Off-site archive | Within 1 cycle | Copy to object storage | 30 days |
| Long-term cold | After 30 days | Cold storage (Glacier/Deepfreeze) | 90 days |
| Immutable/compliance | Indefinite | WORM/object-lock storage | Never purge without approval |

### Off-site copy verification

After each copy, verify integrity:

```bash
# Generate SHA256 on source
sha256sum /var/lib/etcd/snapshot-$(date +%F).db > /tmp/snapshot-$(date +%F).sha256

# Verify on destination (Ceph RGW example)
# The object storage must support hash verification;
# otherwise compare the downloaded file against the source checksum
```

### Snapshot retention policy

```bash
# Prune local Velero snapshots older than 7 days
velero snapshot list -o wide | grep older-than 7d | xargs velero snapshot delete

# Remove off-site objects older than 30 days (using gsutil)
gsutil -m rm gs://velero-backups/snapshot-$(date -d '30 days ago' +%F).db
```

## C. Restore Procedures

### Restore order

1. **Vault** — unseal and confirm secrets read access
2. **Identity** — Keycloak authentication
3. **Management cluster** — Rancher, Argo CD, platform services
4. **Application cluster** — Velero restore + PVC reattachment
5. **Workload data** — Ceph pools and application data verification

### Velero restore (application cluster)

```bash
# List available backups
velero backup list

# Restore from a specific backup
velero restore create --from-backup <backup-name>

# Wait for restore to complete
velero restore describe --restore <restore-name> -o wide
```

### PVC reattachment verification

After Velero restore, PVCs reference the original PV. The CSI driver must reattach them to the correct nodes.

```bash
# Check PVC status across all namespaces
kubectl get pvc -A

# Identify PVCs not yet bound
kubectl get pvc -A | grep -v Bound | grep -v NAME

# Check CSI controller logs for attachment events
kubectl -n rook-ceph get pods -l app=csi-rbd-provisioner
kubectl -n rook-ceph logs -l app=csi-rbd-provisioner | grep -i attach

# Verify node volume bindings
kubectl get nodes -o wide
```

### Workload verification

Argo CD should automatically detect the restored resources and sync them to the desired state.

```bash
# Check Argo CD application status
argocd app list

# Force sync any drifted applications
argocd app sync <app-name>

# Verify all resources are Healthy
argocd app get <app-name>

# Check pod status across all namespaces
kubectl get pods -A
```

### Data integrity checks

Run smoke queries to verify data was not corrupted during restore.

```bash
# Example: check row counts in key tables
kubectl exec -it <pod> -- psql -U postgres -c 'SELECT count(*) FROM orders;'

# Example: verify checksums if available
velero backup describe <backup-name> --details | grep -i checksum

# Test application-level connectivity
kubectl -n <namespace> get svc <service-name>
```

### Final validation checklist

| Check | Expected | Command |
|---|---|---|
| All pods Running | No pods in Error/CrashLoop | `kubectl get pods -A | grep -v Running | grep -v Completed` |
| All PVCs Bound | All PVCs show Bound | `kubectl get pvc -A | grep -v Bound` |
| Argo CD applications Healthy | All apps show Healthy | `argocd app list | grep -v Healthy` |
| Services reachable | Services have external IPs/hosts | `kubectl get svc -A` |
| Data integrity verified | Smoke queries pass | Application-specific checks |