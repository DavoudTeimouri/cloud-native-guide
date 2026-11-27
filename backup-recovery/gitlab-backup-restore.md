# GitLab Backup and Restore

## Overview

GitLab backup includes repositories, database, registry, and configuration.

## Backup

### Automated Backup (CronJob)

```yaml
# gitlab-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: gitlab-backup
  namespace: gitlab
spec:
  schedule: "0 4 * * *"  # Daily at 4 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: gitlab-backup
          containers:
          - name: gitlab-backup
            image: harbor.internal/gitlab/gitlab-ce:19.5.1-ce.0
            command:
            - /bin/bash
            - -c
            - |
              # Create backup
              gitlab-backup create STRATEGY=copy
              # Find latest backup
              BACKUP_FILE=$(ls -t /var/opt/gitlab/backups/*_gitlab_backup.tar | head -1)
              # Upload to Ceph RGW
              aws s3 cp "$BACKUP_FILE" s3://backups/gitlab/ --endpoint-url https://rgw.internal
            env:
            - name: AWS_ENDPOINT_URL
              value: "https://rgw.internal"
            envFrom:
            - secretRef:
                name: rgw-credentials
            volumeMounts:
            - name: gitlab-backups
              mountPath: /var/opt/gitlab/backups
            - name: aws-credentials
              mountPath: /root/.aws
              readOnly: true
          volumes:
          - name: gitlab-backups
            hostPath:
              path: /var/opt/gitlab/backups
          - name: aws-credentials
            secret:
              secretName: rgw-credentials
      restartPolicy: OnFailure
```

### Manual Backup

```bash
# On GitLab node
gitlab-backup create STRATEGY=copy

# Find backup file
ls -t /var/opt/gitlab/backups/*_gitlab_backup.tar | head -1
```

### Backup Components

- Repositories (Git data)
- Database (PostgreSQL dump)
- Redis dump
- Container Registry images
- Build artifacts
- Pages
- LFS objects
- Uploads
- CI/CD variables

### Backup Retention

| Schedule | Retention | Offsite Copy |
|---|---|---|
| Daily | 30 days | Yes (Ceph RGW) |
| Pre-change | Until next successful | Yes |

## Restore

### Prerequisites

- Same GitLab version as backup
- Fresh GitLab installation or existing instance
- Backup file available

### Restore Procedure

```bash
# 1. Stop GitLab services
gitlab-ctl stop unicorn
gitlab-ctl stop sidekiq
gitlab-ctl stop puma

# 2. Copy backup file
cp /media/backups/gitlab/1234567890_gitlab_backup.tar /var/opt/gitlab/backups/

# 3. Restore
gitlab-backup restore BACKUP=1234567890

# 4. Restart services
gitlab-ctl start

# 5. Verify
gitlab-rake gitlab:check SANITIZE=true
```

### Restore Specific Components

```bash
# Restore only repositories
gitlab-backup restore BACKUP=1234567890 SKIP=db,uploads,artifacts,lfs,registry,pages

# Restore only database
gitlab-backup restore BACKUP=1234567890 SKIP=repositories,uploads,artifacts,lfs,registry,pages
```

## Validation

```bash
# Check backup integrity
gitlab-backup check

# Verify restore
gitlab-rake gitlab:check SANITIZE=true

# Check specific components
gitlab-rake gitlab:backup:check
```

## Backup Storage

- **Backend**: Ceph RGW (S3-compatible)
- **Bucket**: `backups/gitlab`
- **Retention**: 30 days + monthly full
- **Offsite**: Monthly full backup to offline media

## Validation

```bash
# Check backup status
ls -la /var/opt/gitlab/backups/

# Verify backup file
tar -tzf /var/opt/gitlab/backups/1234567890_gitlab_backup.tar | head -20

# Test restore on staging
# (Use separate GitLab instance)
```

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*
