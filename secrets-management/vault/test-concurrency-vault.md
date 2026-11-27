# Vault Secret Rotation Procedures

## Rotation Schedule

| Secret Type | Rotation Frequency | Owner | Automated |
|-------------|-------------------|-------|-----------|
| Database credentials | 30 days | Team DB | Yes |
| API keys | 90 days | Team API | Yes |
| Service tokens | 60 days | Team Infra | Yes |
| Root tokens | 180 days | Security team | No |
| SSH keys | 90 days | Team Ops | Yes |

## Automated Rotation

Automated rotation uses Vault's `rotation` feature with custom scripts:

```bash
# Rotate a secret automatically
vault write -field=value secret/rotation/trigger \
  secret_name=prod/db-credentials \
  rotation_interval=2592000  # 30 days in seconds
```

Automated rotation workflow:
1. **Pre-rotation check**: Validate secret health, check dependent services
2. **Generate new credentials**: Create new secret via provider API
3. **Update consumers**: Write new secret to Vault, update dependent configs
4. **Rotate in Vault**: `vault rotate` command updates the secret version
5. **Post-rotation validation**: Verify new credentials work, deprecate old ones
6. **Cleanup**: Remove old version after retention period

### Supported Rotation Types

- **Database credentials**: Rotate via native database authentication APIs
- **API keys**: Generate new key, update routing, depracate old
- **Service tokens**: Rotate HMAC keys, update service configs
- **SSH keys**: Generate key pair, update authorized_keys, rotate old

## Manual Rotation

Manual rotation for emergencies or automated failures:

```bash
# Step 1: Generate new credentials
# (via provider console, API, or kms command)

# Step 2: Store in Vault
vault kv put secret/prod/db-credentials \
  username=new_user \
  password=new_password \
  rotation_allowed=true

# Step 3: Update dependent services
# (restart pods, update configs, notify teams)

# Step 4: Mark old secret as deprecated
vault kv metadata touch secret/prod/db-credentials \
  --deletion-after=2592000

# Step 5: Remove after verification period
vault kv delete secret/prod/db-credentials
```

**Manual rotation checklist:**
- [ ] New credentials generated and tested
- [ ] All consumers updated before old secret invalidation
- [ ] Team notified of rotation
- [ ] Old secret marked for deletion with retention window
- [ ] Audit log verified for complete chain of custody

## Audit Logging

All rotation actions are logged to Vault's audit devices:

```json
{
  "time": "2024-01-15T10:30:00Z",
  "type": "rotation",
  "actor": "team-db",
  "action": "automated_rotation",
  "secret": "prod/db-credentials",
  "version": "2",
  "status": "success",
  "details": "Rotated from v1 to v2, 0 consumers failed"
}
```

### Audit Device Configuration

```hcl
# Audit device config for rotation logging
audit "file" {
  path    = "/var/log/vault/audit.json"
  type    = "json"
  format  = "logfmt"
}
```

### Required Audit Fields

- **actor**: Who initiated the rotation (user or automation)
- **action**: Type of rotation (automated, manual, emergency)
- **secret**: Fully qualified secret path
- **version**: Secret version before/after rotation
- **status**: success/failed
- **details**: Contextual information (duration, errors, affected services)

### Log Retention

- Minimum 90 days rotation history
- Immutable storage for compliance audits
- Searchable by secret path, actor, and date range
- Exported to SIEM for correlation with access events
