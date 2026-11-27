# Vault Policy Management

## A. Purpose and scope

Document Vault policy management: policy creation, policy assignment, token policies, API method restrictions, path-based access control, and policy auditing.

Cross-references `secrets-management/vault/vault-architecture.md`, `secrets-management/vault/access-control.md`, `secrets-management/vault/secret-rotation.md`, `kubernetes/security/security-controls.md`.

## B. Policy creation

Policies are HCL-based and define what capabilities a principal has at which paths.

```hcl
# policy/readonly.hcl
path "secret/data/platform/*" {
  capabilities = ["read"]
}

path "secret/data/secrets/*" {
  capabilities = ["read", "list"]
}

# policy/admin.hcl
path "sys/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/seal/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/mounts/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/config/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/audit/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/auth/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/cubbyhole/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```

## C. Policy assignment

Policies are attached to named roles via auth methods. A role maps a principal (e.g., a Kubernetes service account) to a policy.

```bash
# Write policies
vault policy write readonly policy/readonly.hcl
vault policy write admin policy/admin.hcl

# Create a Kubernetes auth role with policy assignment
vault write auth/kubernetes/role/platform-app \
  bound_service_account_names=platform-app \
  bound_service_account_namespaces=platform \
  policies=readonly \
  ttl=24h

# Create an admin role
vault write auth/kubernetes/role/admin-app \
  bound_service_account_names=admin-app \
  bound_service_account_namespaces=admin \
  policies=admin \
  ttl=1h
```

Token policies can also be specified at token creation time.

```bash
# Create token with specific policy and TTL
vault token create -policy=readonly -ttl=1h -max-ttl=24h

# Create token with multiple policies
vault token create -policy=readonly -policy=admin -ttl=1h
```

## D. Token policies

Tokens carry policies that define their capabilities. Token policies control:

- **TTL and max TTL**: How long the token is valid
- **Num uses**: Number of times the token can be used
- **Display name**: Human-readable token name
- **Policy**: Attached policies that grant capabilities
- **No wrap**: Whether the token can be wrapped
- **Period**: Renewal period for the token

Token accessor and review:

```bash
# Review current token's policies and TTL
vault token lookup -self

# Revoke a token
vault token revoke <token-id>

# Revoke all tokens for a specific policy
vault token revoke -policy=readonly
```

## E. API method restrictions

Policy capabilities map to Vault API methods. The principle of least privilege applies: grant only the methods needed for the principal's function.

| Capability | API Methods |
|---|---|
| `read` | GET, HEAD |
| `create` | POST |
| `update` | PUT, POST |
| `delete` | DELETE |
| `list` | LIST |
| `sudo` | Full access (bypasses policy) |

Example restricting to read-only access at specific paths:

```hcl
path "secret/data/*" {
  capabilities = ["read"]
}

# Deny specific paths even at higher levels
path "secret/data/credentials/*" {
  capabilities = []
}
```

## F. Path-based access control

Path-based access control is the primary mechanism for restricting Vault access. Patterns support:

- Exact match: `secret/data/db-passwords`
- Wildcard: `secret/data/*` matches all data under `secret/data/`
- Recursive wildcard: `secret/**` matches all paths recursively
- Negation: Empty capabilities `[]` denies access

Best practices for path-based access control:

1. **Start least-privilege**: Begin with `[]` (no access) and only add needed capabilities
2. **Use specific paths**: `secret/data/platform/*` rather than `secret/data/*`
3. **Separate environments**: `secret/data/prod/*`, `secret/data/staging/*`, `secret/data/dev/*`
4. **Audit-sensitive paths**: Restrict `sys/` and `auth/` paths to operational roles only

Example: Environment-separated policies

```hcl
# Policy for production
path "secret/data/prod/*" {
  capabilities = ["read", "list"]
}

path "secret/data/prod/*" {
  capabilities = ["update"]
  # Limited update scope
}

# Policy for staging
path "secret/data/staging/*" {
  capabilities = ["read", "list", "update"]
}

# Policy for development
path "secret/data/dev/*" {
  capabilities = ["read", "list", "create", "update", "delete"]
}
```

## G. Policy auditing

Audit policies track who accessed what, when, and from where. Enable audit devices and define audit policies to control logging.

```bash
# List existing audit devices
vault audit list

# Enable audit device (file example)
vault audit enable file filePath=/var/log/vault/audit.log

# Enable audit device (syslog example)
vault audit enable syslog address="syslog://localhost:514"

# Write audit policy that logs all methods
audit "file" {
  file_path = "/var/log/vault/audit.log"
  # Log all requests
  style = "log"
}
```

Audit log best practices:

- Ship audit logs to immutable, centralized storage
- Retain audit logs per compliance requirements (1-7 years minimum)
- Never log secret values — metadata only
- Use HMAC-request-response mode for additional value protection
- Configure alerting on: failed auth, policy changes, unexpected path access, privilege escalation

Example audit policy logging all requests:

```hcl
# audit/logging.hcl
path "*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```

## H. Cross-references

- `secrets-management/vault/vault-architecture.md` — Vault deployment architecture
- `secrets-management/vault/access-control.md` — Auth methods, roles, policies, token policies
- `secrets-management/vault/secret-rotation.md` — Secret rotation procedures
- `kubernetes/security/security-controls.md` — Vault in security context
- `identity/directory-integration.md` — Directory integration procedures