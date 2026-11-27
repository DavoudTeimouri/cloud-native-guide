# Harbor Backup and Restore

## Overview

Harbor backup includes registry data, database, and configuration.

## Backup

### Automated Backup (CronJob)

```yaml
# harbor-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: harbor-backup
  namespace: harbor
spec:
  schedule: "0 5 * * *"  # Daily at 5 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: harbor-backup
          containers:
          - name: harbor-backup
            image: harbor.internal/goharbor/harbor-db:v2.15.4
            command:
            - /bin/bash
            - -c
            - |
              # Backup database
              pg_dump -h postgres -U harbor -d registry > /backup/harbor-db-$(date +%Y%m%d).sql
              # Backup registry data
              tar -czf /backup/harbor-data-$(date +%Y%m%d).tar.gz /data/registry
              # Backup config
              tar -czf /backup/harbor-config-$(date +%Y%m%d).tar.gz /etc/harbor
              # Upload to RGW
              aws s3 cp /backup/harbor-db-$(date +%Y%m%d).sql s3://backups/harbor/ --endpoint-url https://rgw.internal
              aws s3 cp /backup/harbor-data-$(date +%Y%m%d).tar.gz s3://backups/harbor/ --endpoint-url https://rgw.internal
              aws s3 cp /backup/harbor-config-$(date +%Y%m%d).tar.gz s3://backups/harbor/ --endpoint-url https://rgw.internal
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: harbor-db-password
                  key: password
            envFrom:
            - secretRef:
                name: rgw-credentials
            volumeMounts:
            - name: harbor-data
              mountPath: /data/registry
              readOnly: true
            - name: harbor-config
              mountPath: /etc/harbor
              readOnly: true
            - name: backup
              mountPath: /backup
            - name: aws-credentials
              mountPath: /root/.aws
              readOnly: true
          volumes:
          - name: harbor-data
            persistentVolumeClaim:
              claimName: harbor-registry-pvc
          - name: harbor-config
            hostPath:
              path: /etc/harbor
          - name: backup
            emptyDir: {}
          - name: aws-credentials
            secret:
              secretName: rgw-credentials
      restartPolicy: OnFailure
```

### Manual Backup

```bash
# Backup database
pg_dump -h postgres -U harbor -d registry > harbor-db-$(date +%Y%m%d).sql

# Backup registry data
tar -czf harbor-data-$(date +%Y%m%d).tar.gz /data/registry

# Backup config
tar -czf harbor-config-$(date +%Y%m%d).tar.gz /etc/harbor

# Upload to RGW
aws s3 cp harbor-db-$(date +%Y%m%d).sql s3://backups/harbor/ --endpoint-url https://rgw.internal
aws s3 cp harbor-data-$(date +%Y%m%d).tar.gz s3://backups/harbor/ --endpoint-url https://rgw.internal
aws s3 cp harbor-config-$(date +%Y%m%d).tar.gz s3://backups/harbor/ --endpoint-url https://rgw.internal
```

### Backup Components

| Component | Method | Retention |
|---|---|---|
| Database (PostgreSQL) | pg_dump | 30 days + 1 offline |
| Registry Data | tar.gz | 30 days |
| Configuration | tar.gz | 30 days |

## Restore

### Database Restore

```bash
# 1. Stop Harbor services
docker-compose -f /etc/harbor/docker-compose.yml stop

# 2. Restore database
psql -h postgres -U harbor -d registry < harbor-db-<timestamp>.sql

# 3. Restore registry data
tar -xzf harbor-data-<timestamp>.tar.gz -C /

# 4. Restore config
tar -xzf harbor-config-<timestamp>.tar.gz -C /

# 4. Restart Harbor
docker-compose -f /etc/harbor/docker-compose.yml up -d
```

### Full Restore Procedure

```bash
# 1. Stop Harbor
docker-compose -f /etc/harbor/docker-compose.yml down

# 2. Restore database
psql -h postgres -U harbor -d registry < harbor-db-<timestamp>.sql

# 3. Restore registry data
tar -xzf harbor-data-<timestamp>.tar.gz -C /

# 3. Restore config
tar -xzf harbor-config-<timestamp>.tar.gz -C /

# 5. Start Harbor
docker-compose -f /etc/harbor/docker-compose.yml up -d

# 6. Verify
curl -k https://harbor.internal/api/v2.0/health
```

## Validation

```bash
# Check Harbor health
curl -k https://harbor.internal/api/v2.0/health

# Check database
psql -h postgres -U harbor -d registry -c "SELECT count(*) FROM project;"

# Check registry
curl -k https://harbor.internal/v2/_catalog
```

## Backup Storage

- **Backend**: Ceph RGW (S3-compatible)
- **Bucket**: `backups/harbor`
- **Retention**: 30 days + 1 offline copy
- **Offsite**: Monthly copy to offline media

## Validation

```bash
# Verify backup files exist
aws s3 ls s3://backups/harbor/ --endpoint-url https://rgw.internal

# Test restore on staging
# (Use separate Harbor instance)
```

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*
