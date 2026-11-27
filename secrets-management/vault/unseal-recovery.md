# Vault Unseal Recovery

## A. Purpose and scope

Document Vault unseal recovery mechanisms: Shamir's Secret Sharing, auto-unseal with KMS, recovery key management, emergency unseal procedures, and unseal key rotation. This is step 1 of the recovery order defined in `lifecycle/disaster-recovery/index.md` — all other components depend on Vault for secrets.

Cross-references: `secrets-management/vault/vault-architecture.md`, `secrets-management/vault/recovery/restore.md`, `secrets-management/kubernetes-integration/secret-delivery.md`.

## B. Unseal methods

### 1. Shamir's Secret Sharing (manual unseal)

Vault uses Shamir's Secret Sharing to split the master key into N shares, requiring M-of-N shares to reconstruct the key and unseal Vault.

- **Parameters**: Typically 5 shares with 3-of-5 threshold (3 shares required to unseal)
- **Share storage**: Shares are stored offline by separate custodians — hardware security modules, physical safes, or trusted individuals
- **No single point of failure**: Any 3 of the 5 shares can unseal Vault, but no 2 shares reveal any information about the master key
- **Cryptographic security**: Each share is a point on the polynomial; 2 shares define a line, but 3+ shares are needed to determine the constant term (the master key)

```bash
# Unseal Vault with a single share
vault operator unseal <share-value>

# Example: Unseal all 3 required shares
vault operator unseal share-1
vault operator unseal share-2
vault operator unseal share-3
```

### 2. Auto-unseal with KMS

Auto-unseal delegates unseal key management to a cloud KMS, eliminating manual share handling.

- **AWS KMS**: Configured via `vault operator init` and `vault operator unseal` with KMS ARNs
- **Azure Key Vault**: Integration via `vault operator unseal` with Azure Key URI
- **Google Cloud KMS**: Integration via `vault operator unseal` with Cloud KMS key reference
- **Benefits**: No offline share storage required; unseal happens automatically on restart; integrates with IAM for access control
- **Considerations**: KMS must remain available; loss of KMS access = loss of Vault availability; ensure redundancy of KMS keys across regions

```bash
# Initialize Vault with auto-unseal (AWS KMS example)
vault operator init \
  -key-shares=5 \
  -key-threshold=3 \
  -root-token-ttl=1h \
  -unseal-kms-arn arn:aws:kms:us-east-1:123456789012:key/abc123
```

## C. Recovery key management

### Key share storage

| Method | Description | Risk |
|---|---|---|
| **Offline physical** | Printed shares in sealed envelopes, stored in separate locations | Theft, physical loss |
| **HSM-protected** | Shares encrypted and stored in Hardware Security Modules | HSM compromise, single point |
| **Cloud KMS** | Shares encrypted under KMS keys; KMS auto-unseal | KMS outage, IAM misconfiguration |
| **Split knowledge** | Multiple custodians, each holds one share; no single person has enough | Custody disputes, accessibility |

### Rotating unseal keys

Rotate unseal keys when:
- A custodian departs and their share is suspected compromised
- M-of-N threshold changes (e.g., 3-of-5 → 4-of-6)
- KMS key rotation policy requires it
- Security incident involving share storage

**Rotation procedure**:

1. **Add new shares**: Use `vault operator init` with new shares or `vault operator unseal` to add additional shares
2. **Remove old shares**: Once new shares are verified, securely erase old shares from storage
3. **Verify**: Confirm Vault starts and remains unsealed with the new key material
4. **Document**: Update this file and the key custody log with rotation date and custodian changes

```bash
# Add a new unseal share (requires existing quorum)
vault operator unseal <new-share-value>

# After all new shares are added and verified, remove old shares
# securely erase old share storage media
```

## D. Emergency unseal procedures

### Standard emergency unseal

When Vault restarts and auto-unseal is unavailable:

1. **Locate share storage**: Retrieve 3 of 5 stored shares from custodians
2. **Unseal each Vault node**: Run `vault operator unseal <share>` on each pod
3. **Verify status**: `vault status` should show `Sealed: false`
4. **Restore access**: Users can authenticate; secrets are readable

### Partial unseal (node-specific)

If only some nodes are sealed (e.g., after a rolling restart):

```bash
# On each unsealed pod, provide shares until unsealed
kubectl -n vault exec -it vault-0 -- vault operator unseal <share-1>
kubectl -n vault exec -it vault-1 -- vault operator unseal <share-2>
kubectl -n vault exec -it vault-2 -- vault operator unseal <share-3>
```

### Emergency access without unseal (break-glass)

In extreme scenarios where all shares are unavailable but the Raft snapshot exists:

1. **Restore from snapshot**: Use `vault operator raft snapshot restore` (requires Vault stopped)
2. **Re-initialize**: If snapshot is also lost, re-initialize Vault with new shares (destroys existing data)
3. **Restore data from backup**: Apply application-level data backups after Vault is running

**Never** bypass the unseal process — doing so exposes the master key and compromises all stored secrets.

## E. Unseal key rotation

Rotate unseal key material when the security of existing shares is compromised or when changing the M-of-N threshold.

### Rotation procedure (3-of-5 → 3-of-5, new shares)

1. **Bring existing Vault online**: Ensure Vault is running and unsealed with current shares
2. **Add new share shares**: Each custodian generates a new share; add via `vault operator unseal <new-share>`
3. **Remove old shares**: Once 3+ new shares are confirmed, securely erase old shares
4. **Verify**: `vault status` should remain unsealed; test secret access
5. **Update documentation**: Record rotation date, old shares decommissioned, new custodians

```bash
# Add share 4 (while 3-of-5 is already active)
vault operator unseal <share-4>

# Add share 5
vault operator unseal <share-5>

# Now remove share 1 (securely erase it)
# ... securely delete share-1 from all storage locations

# Verify Vault still works
vault status
```

### Rotation procedure (threshold change: 3-of-5 → 4-of-6)

1. **Add shares incrementally**: Add share 6 first, then share 5, while keeping 3-of-5 active
2. **Raise threshold**: After 4-of-6 is configured, update Vault's internal threshold
3. **Remove old shares**: Securely erase shares 1-3 once new quorum is verified
4. **Full verification**: Run disaster recovery drill to confirm the new threshold works

### Automated rotation with KMS

When using auto-unseal with KMS, key rotation is handled by the KMS service. To rotate:

1. **Create new KMS key**: `aws kms create-key --description "Vault auto-unseal key rotation"`
2. **Update KMS reference**: Configure Vault to use the new key (may require re-initialization)
3. **Re-initialize if needed**: Some KMS integrations require `vault operator init` after key rotation
4. **Verify**: Confirm auto-unseal works with the new key

## F. Cross-references

- `secrets-management/vault/vault-architecture.md` — Vault deployment architecture and HA topology
- `secrets-management/vault/recovery/restore.md` — Full recovery procedure (snapshot restore step 2)
- `lifecycle/disaster-recovery/index.md` — Recovery order and dependencies
- `secrets-management/kubernetes-integration/secret-delivery.md` — Secret delivery to workloads after unseal
- `identity/directory-integration.md` — Authentication integration after recovery