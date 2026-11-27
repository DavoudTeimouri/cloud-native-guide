# Vault Recovery

## A. Purpose and scope

Recovery procedure for HashiCorp Vault: unseal, restore from raft snapshot, and confirm read access to secrets.

This is step 1 of the recovery order defined in `lifecycle/disaster-recovery/index.md` — it runs before every other recovery step because all other components depend on Vault for secrets.

## B. Prerequisites

| Prerequisite | Source |
|--------------|--------|
| Vault raft snapshot available | `lifecycle/backup/backup-and-dr.md` §Vault |
| Unseal keys (3 of 5 shares) | Offline storage, key holders |
| Vault TLS certificate valid | `secrets-management/pki/root-ca-rotation.md` |

## C. Recovery procedure

### 1. Start Vault

```bash
# If Vault is not running, start it
kubectl -n vault rollout restart sts/vault
kubectl -n vault rollout status sts/vault
```

### 2. Unseal Vault

Vault starts sealed. Provide 3 of 5 unseal shares:

```bash
# On each Vault pod, or via vault operator
kubectl -n vault exec -it vault-0 -- vault operator unseal <share-1>
kubectl -n vault exec -it vault-0 -- vault operator unseal <share-2>
kubectl -n vault exec -it vault-0 -- vault operator unseal <share-3>
```

Or use the Vault operator's automatic unseal if configured with KMS/auto-unseal.

### 3. Restore from raft snapshot

```bash
# Copy snapshot to a Vault pod
kubectl -n vault cp /path/to/snapshot.snap vault-0:/tmp/snapshot.snap

# Restore (Vault must be stopped first for raft restore)
kubectl -n vault rollout pause sts/vault
kubectl -n vault exec -it vault-0 -- vault operator raft snapshot restore /tmp/snapshot.snap
kubectl -n vault rollout resume sts/vault
```

**Note:** Raft snapshot restore requires Vault to be stopped. Schedule this during a maintenance window.

### 4. Verify read access

```bash
# Authenticate
vault login -method=kubernetes role=platform

# Verify a known secret path
vault kv get secret/platform/database

# Verify AppRole auth works for applications
vault write auth/approle/login role_id=<role_id> secret_id=<secret_id>
```

## D. Verification

```bash
# Vault is unsealed
vault status | grep "Sealed.*false"

# Secrets are readable
vault kv list secret/platform/

# Applications can authenticate
vault token lookup <app-token>
```

## E. Cross-references

- `lifecycle/disaster-recovery/index.md` — Recovery order (step 1)
- `lifecycle/backup/backup-and-dr.md` §Vault — Backup mechanics
- `secrets-management/vault/vault-architecture.md` — Vault deployment architecture
- `secrets-management/pki/root-ca-rotation.md` — PKI certificate management
