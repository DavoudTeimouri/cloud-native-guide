# Vault Access Control

## A. Purpose and scope

Document Vault access control: auth methods, roles, policies, token policies, seal/unseal process.

Cross-references `secrets-management/vault/vault-architecture.md`, `secrets-management/kubernetes-integration/secret-delivery.md`, `kubernetes/security/security-controls.md`.

## B. Auth methods

| Auth method | Use case | Configuration |
|-------------|----------|---------------|
| Kubernetes | Workload identity | `vault auth enable kubernetes` |
| GitHub | Human operator | `vault auth enable github` |
| LDAP | Enterprise directory | `vault auth enable ldap` |
| Token | Service-to-service | Built-in |

## C. Roles and policies

Policies are HCL-based and attached to roles:

```hcl
# policy/readonly.hcl
path "secret/data/platform/*" {
  capabilities = ["read"]
}

path "secret/data/secrets/*" {
  capabilities = ["read", "list"]
}
```

```bash
# Write policy
vault policy write readonly policy/readonly.hcl

# Create role with policy
vault write auth/kubernetes/role/platform \
  bound_service_account_names=platform-app \
  bound_service_account_namespaces=platform \
  policies=readonly \
  ttl=24h
```

## D. Token policies

Tokens are short-lived with least privilege:

```bash
# Create token with TTL
vault token create -policy=readonly -ttl=1h

# Revoke token
vault token revoke <token-id>
```

## E. Seal/unseal process

Vault starts sealed. Unseal requires 3 of 5 shares:

```bash
# Unseal with one share
vault operator unseal <share-1>

# Check seal status
vault status

# Seal Vault
vault operator seal
```

## F. Cross-references

- `secrets-management/vault/vault-architecture.md` — Vault deployment architecture
- `secrets-management/kubernetes-integration/secret-delivery.md` — Secret delivery to workloads
- `kubernetes/security/security-controls.md` §Vault — Vault in security context
