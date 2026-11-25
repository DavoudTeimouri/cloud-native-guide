# Vault Backup and Restore

## Overview

Vault stores secrets, PKI certificates, and encryption keys. Backup includes both storage backend and seal/unseal material.

## Backup

### Automated Backup (CronJob)

```yaml
# vault-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vault-backup
  namespace: vault
spec:
  schedule: "0 3 * * *"  # Daily at 3 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: vault-backup
          containers:
          - name: vault-backup
            image: harbor.internal/hashicorp/vault:2.2.0
            command:
            - /bin/bash
            - -c
            - |
              # Create snapshot
              vault operator raft snapshot save /backup/vault-snapshot-$(date +%Y%m%d-%H%M%S).snap
              # Upload to Ceph RGW
              aws s3 cp /backup/vault-snapshot-*.snap s3://backups/vault/ --endpoint-url https://rgw.internal
            env:
            - name: VAULT_ADDR
              value: "https://vault.internal:8200"
            - name: VAULT_TOKEN
              valueFrom:
                secretKeyRef:
                  name: vault-backup-token
                  key: token
            volumeMounts:
            - name: backup
              mountPath: /backup
            - name: aws-credentials
              mountPath: /root/.aws
              readOnly: true
          volumes:
          - name: backup
            emptyDir: {}
          - name: aws-credentials
            secret:
              secretName: rgw-credentials
      restartPolicy: OnFailure
```

### Manual Backup

```bash
# On Vault node
vault operator raft snapshot save /backup/vault-snapshot-$(date +%Y%m%d-%H%M%S).snap

# Verify
vault operator raft snapshot inspect /backup/vault-snapshot-*.snap
```

### Backup Retention

| Schedule | Retention | Offsite Copy |
|---|---|---|
| Daily | 30 days | Yes (Ceph RGW) |
| Pre-change | Until next successful | Yes |

## Restore

### Prerequisites

- Vault cluster stopped (or in standby)
- Valid snapshot file
- Unseal keys available

### Restore Procedure

```bash
# 1. Stop Vault on all nodes
for node in vault-1 vault-2 vault-3; do
  ssh $node "systemctl stop vault"
done

# 2. Restore snapshot on first node
vault operator raft snapshot restore /backup/vault-snapshot-<timestamp>.snap

# 3. Start Vault on first node
systemctl start vault

# 4. Wait for leader election
vault operator raft list-peers

# 5. Start remaining nodes
for node in vault-2 vault-3; do
  ssh $node "systemctl start vault"
done

# 6. Unseal all nodes
for node in vault-1 vault-2 vault-3; do
  vault operator unseal -address=https://$node:8200 $SHARD1
  vault operator unseal -address=https://$node:8200 $SHARD2
  vault operator unseal -address=https://$node:8200 $SHARD3
done
```

### Multi-Node Restore

1. Restore on first node (becomes leader)
2. Start remaining nodes
3. They will join the Raft cluster automatically
4. Unseal all nodes

## Validation

```bash
# Check cluster status
vault status
vault operator raft list-peers

# Verify data
vault kv list secret/
vault auth list
vault policy list
```

## Unseal Material Backup

### Offline Storage

- **Shamir Shards**: 3 of 5 required
- **Storage**: Physical safe, geographically distributed
- **Access**: Requires 3 custodians
- **Rotation**: Annual rotation of shards

### Automated Verification

```bash
# Quarterly unseal test
vault operator unseal $SHARD1
vault operator unseal $SHARD2
vault operator unseal $SHARD3
# Verify
vault status
# Re-seal
vault operator seal
```

## Automation

The backup CronJob runs daily at 3 AM. Manual restore is a coordinated operation requiring multiple operators.

---

*Status: DRAFT | Owner: Security Team | Last reviewed: 2026-11-23*