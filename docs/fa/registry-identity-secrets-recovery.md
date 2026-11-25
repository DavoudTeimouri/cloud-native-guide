# REGISTRY-IDENTITY-SECRETS-RECOVERY

*مثالی است. هیچ secret/real recovery key در مثال‌ها نیست.*

## REGISTRY-IDENTITY-SECRETS-RECOVERY-1. Nexus/Harbor

 config، metadata DB، blob/artifact storage، certificates، RBAC/project config، replication state، metadata-artifact consistency.

## REGISTRY-IDENTITY-SECRETS-RECOVERY-2. Keycloak

 DB backup، realm/client export، IdP/OIDC recovery، cert/secret dependencies.

## REGISTRY-IDENTITY-SECRETS-RECOVERY-3. Vault/OpenBao

 storage backend backup، Raft snapshot، unseal+recovery key protection، seal config، restore+validation.

## REGISTRY-IDENTITY-SECRETS-RECOVERY-4. warning

 config-only backup برای خدمات stateful کافی نیست.

---

*SND 004-P11.5 — REGISTRY-IDENTITY-SECRETS-RECOVERY (illustrative)*
