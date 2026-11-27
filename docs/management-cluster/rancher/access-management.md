# Rancher Access Management

## A. Purpose and scope

Document access management: RBAC, roles, bindings, service accounts, OIDC integration with Keycloak.

Cross-references `management-cluster/rancher/rancher.md`, `management-cluster/keycloak/keycloak.md`, `kubernetes/security/security-controls.md` §RBAC.

## B. RBAC model

| Role | Scope | Capabilities |
|------|-------|--------------|
| Admin | Cluster | Full access |
| Member | Project | Read/write resources |
| Viewer | Cluster/Project | Read-only |
| Restricted | Project | Read-only, no exec/secrets |

## C. Service accounts

Service accounts are created per application and scoped to a namespace:

```yaml
# ServiceAccount example
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: app-ns
automountServiceAccountToken: true
```

## D. OIDC integration with Keycloak

Rancher integrates with Keycloak for centralized identity:

```bash
# Configure OIDC provider
rancher auth configure oidc \
  --issuer https://keycloak.internal/realms/platform \
  --client-id rancher \
  --client-secret <secret>

# Map Keycloak groups to Rancher roles
rancher group create --name developers --oidc-group developers
rancher role-template binding create --role project-member --group developers --project app-prod
```

## E. Cross-references

- `management-cluster/rancher/rancher.md` — Rancher deployment
- `management-cluster/keycloak/keycloak.md` — Keycloak deployment
- `kubernetes/security/security-controls.md` §RBAC — Kubernetes RBAC
