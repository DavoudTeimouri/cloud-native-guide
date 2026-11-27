# Ceph Backup and Restore

## Overview

Ceph backup strategy covers both cephadm standalone and Rook-Ceph in-cluster deployments.

## Backup

### cephadm Standalone

```bash
# Backup Ceph configuration
ceph config dump > /backup/ceph-config-$(date +%Y%m%d).json

# Backup CRUSH map
ceph osd getcrushmap -o /backup/crushmap-$(date +%Y%m%d).bin

# Backup RBD images (incremental)
rbd export --pool replicapool <image> /backup/rbd-<image>-$(date +%Y%m%d).snap

# Backup CephFS (via snapshot)
ceph fs snapshot create cephfs backup-$(date +%Y%m%d)

# Backup Ceph config to RGW
aws s3 sync /etc/ceph/ s3://backups/ceph/config/ --endpoint-url https://rgw.internal
```

### Rook-Ceph (In-Cluster)

```yaml
# ceph-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: ceph-backup
  namespace: rook-ceph
spec:
  schedule: "0 1 * * *"  # Daily at 1 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: ceph-backup
          containers:
          - name: ceph-backup
            image: harbor.internal/ceph/ceph:20.2.4
            command:
            - /bin/bash
            - -c
            - |
              # Backup Ceph config
              ceph config dump > /backup/ceph-config-$(date +%Y%m%d).json
              # Backup CRUSH map
              ceph osd getcrushmap -o /backup/crushmap-$(date +%Y%m%d).bin
              # Upload to RGW
              aws s3 sync /backup/ s3://backups/ceph/ --endpoint-url https://rgw.internal
            env:
            - name: CEPH_CONF
              value: /etc/ceph/ceph.conf
            - name: CEPH_KEYRING
              value: /etc/ceph/ceph.client.admin.keyring
            volumeMounts:
            - name: ceph-config
              mountPath: /etc/ceph
              readOnly: true
            - name: backup
              mountPath: /backup
            - name: aws-credentials
              mountPath: /root/.aws
              readOnly: true
            env:
            - name: AWS_ENDPOINT_URL
              value: "https://rgw.internal"
            envFrom:
            - secretRef:
                name: rgw-credentials
        volumeMounts:
        - name: ceph-config
          mountPath: /etc/ceph
          readOnly: true
        - name: backup
          emptyDir: {}
        - name: aws-credentials
          secret:
            secretName: rgw-credentials
      restartPolicy: OnFailure
```

### RBD Snapshot Backup

```bash
# Create snapshot
rbd snap create replicapool/vm-disk@backup-$(date +%Y%m%d)

# Export snapshot
rbd export replicapool/vm-disk@backup-$(date +%Y%m%d) /backup/vm-disk-$(date +%Y%m%d).img

# Upload to RGW
aws s3 cp /backup/vm-disk-$(date +%Y%m%d).img s3://backups/ceph/rbd/ --endpoint-url https://rgw.internal
```

### Retention Policy

| Backup Type | Frequency | Retention | Offsite |
|---|---|---|---|
| Config/CRUSH | Daily | 30 days | Yes |
| RBD Snapshots | Daily | 7 days | Yes |
| CephFS Snapshots | Daily | 7 days | Yes |
| Full Export | Weekly | 4 weeks | Yes |

## Restore

### Ceph Configuration Restore

```bash
# Restore config
ceph config assimilate -i /backup/ceph-config-<timestamp>.json

# Restore CRUSH map
crushtool -i /backup/crushmap-<timestamp>.bin -o /tmp/crushmap.compiled
ceph osd setcrushmap -i /tmp/crushmap.compiled
```

### RBD Restore

```bash
# Import snapshot
rbd import /backup/vm-disk-<timestamp>.img replicapool/vm-disk-restored

# Or restore from snapshot
rbd snap rollback replicapool/vm-disk@backup-<timestamp>
```

### CephFS Restore

```bash
# List snapshots
ceph fs snapshot ls cephfs

# Restore from snapshot
ceph fs snapshot restore cephfs <snapshot-name>

# Or restore specific path
mkdir /restore
ceph fs snapshot mount cephfs <snapshot-name> /restore
```

### Disaster Recovery

```bash
# Full cluster rebuild
1. Deploy new Ceph cluster (cephadm or Rook)
2. Restore config and CRUSH map
3. Restore RBD images from snapshots
4. Restore CephFS from snapshots
5. Verify: ceph -s, rbd ls, ceph fs ls
```

---

*Status: DRAFT | Owner: Storage Team | Last reviewed: 2026-11-23*
