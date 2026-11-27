# Velero Backup and Restore

## Overview

Velero provides Kubernetes cluster backup and restore capabilities, including disaster recovery and cluster migration.

## Installation

```bash
# Add Velero repo
helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
helm repo update

# Install Velero
helm install velero vmware-tanzu/velero \
  --namespace velero --create-namespace \
  --version 12.2.1 \
  --set configuration.provider=aws \
  --set configuration.region=us-east-1 \
  --set configuration.backupStorageLocation[0].name=default \
  --set configuration.backupStorageLocation[0].bucket=velero-backups \
  --set configuration.backupStorageLocation[0].config.region=us-east-1 \
  --set configuration.backupStorageLocation[0].config.s3ForcePathStyle=true \
  --set configuration.backupStorageLocation[0].config.s3Url=https://rgw.internal \
  --set credentials.secretContents.cloud= |
    [default]
    aws_access_key_id=<access-key>
    aws_secret_access_key=<secret-key>
```

## Backup

### Scheduled Backups

```yaml
# velero-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  template:
    ttl: 720h  # 30 days
    includedNamespaces:
      - "*"
    excludedResources:
      - events
      - events.events.k8s.io
    snapshotVolumes: true
    storageLocation: default
```

### On-Demand Backup

```bash
# Full cluster backup
velero backup create <backup-name> --include-namespaces='*' --snapshot-volumes=true

# Namespace-specific backup
velero backup create <backup-name> --include-namespaces=<namespace> --snapshot-volumes=true

# Backup with label selector
velero backup create <backup-name> --selector app=<app-name> --snapshot-volumes=true
```

### Backup Verification

```bash
# List backups
velero backup get

# Describe backup
velero backup describe <backup-name>

# Check backup logs
velero backup logs <backup-name>
```

## Restore

### Full Cluster Restore

```bash
# List available backups
velero backup get

# Restore from backup
velero restore create --from-backup <backup-name>

# Restore specific namespace
velero restore create --from-backup <backup-name> --include-namespaces <namespace>

# Restore with label selector
velero restore create --from-backup <backup-name> --selector app=<app-name>
```

### Restore Validation

```bash
# Check restore status
velero restore get
velero restore describe <restore-name>

# Verify resources
kubectl get all -A
kubectl get pvc -A
```

## Disaster Recovery

### Complete Cluster Loss

1. **Provision new cluster** with same Kubernetes version
2. **Install Velero** on new cluster with same configuration
3. **Restore from backup**:
   ```bash
   velero restore create --from-backup <latest-backup>
   ```
2. **Verify**:
   ```bash
   kubectl get nodes
   kubectl get pods -A
   kubectl get pvc -A
   ```

### Partial Restore

```bash
# Restore specific namespace
velero restore create --from-backup <backup-name> --include-namespaces <namespace>

# Restore specific resources
velero restore create --from-backup <backup-name> --included-resources deployments,services,configmaps

# Restore with label selector
velero restore create --from-backup <backup-name> --selector app=<app-name>
```

## Backup Storage

- **Backend**: Ceph RGW (S3-compatible)
- **Bucket**: `velero-backups`
- **Retention**: 30 days (configurable via TTL)
- **Offsite Copy**: Manual copy to offline storage monthly

## Monitoring

```bash
# Check backup status
velero backup get

# Check schedule status
velero schedule get

# Monitor backup jobs
kubectl get jobs -n velero

# Alert on backup failures
# Prometheus alert: velero_backup_failed
```

## Validation

```bash
# Test restore on staging cluster
velero restore create --from-backup <backup-name> --dry-run

# Verify restored resources
velero restore describe <restore-name>
kubectl get all -A
```

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*