# Section 6 — RBAC and Identity

*Illustrative only — not production-committed configurations. Marked as such where indicated. No RBAC rules are applied to a live cluster from this document.*

---\n\n## 6.1 RBAC Overview and Responsibility Boundary

Kubernetes RBAC (Role-Based Access Control) regulates who can perform what actions within the cluster. It is enforced by the `kube-apiserver` via `Role`, `ClusterRole`, `RoleBinding`, and `ClusterRoleBinding` objects. RBAC operates at the API server layer — every `kubectl` command, API request, and internal service communication is checked against the RBAC ruleset.

**Responsibility boundary**: RBAC decisions are binary: allowed or denied. There is no partial enforcement. The `cluster-admin` ClusterRole grants unrestricted access; all other roles must be explicitly assigned. The `system:authenticated` and `system:anonymous` groups provide baseline access; these should be narrowed in production.

---\n\n## 6.2 RBAC Validation

### Verify User/Service Account Permissions

```bash
# Test intended privileges
kubectl auth can-i 'get' 'pods' --namespace=<ns> --as=<user>

# Test wildcard access (should be restricted)
kubectl auth can-i '*' '*' --all-namespaces --as=<user>

# Verify system group access
kubectl auth can-i 'get' 'pods' --namespace=kube-system --as=system:anonymous

# List all roles and bindings in the namespace
kubectl get role-binding --all-namespaces
kubectl get clusterrole-binding --all-namespaces
```

### RBAC Audit Checklist

- [ ] No user has `*` verb on `*` resource across all namespaces
- [ ] `system:authenticated` access is narrowed to required operations only
- [ ] `system:anonymous` access is disabled or restricted to health checks
- [ ] `pods/exec` and `pods/portforward` are restricted to diagnostic or service-account users only
- [ ] Service account tokens are not automounted (`automountServiceAccountToken: false`)
- [ ] Each role/binding has a documented owner and review cadence (quarterly)
- [ ] No role grants `create` on secrets unless explicitly required and documented
- [ ] RBAC rules are minimal — grant only the verbs required for the workload's operation

---\n\n## 6.3 Identity Integration

### OIDC and IdP Integration

The cluster integrates with an Identity Provider (IdP) via OpenID Connect (OIDC). Users authenticate using their IdP credentials, and RBAC rules govern what they can do.

```bash
# Verify OIDC authentication works
kubectl auth can-i 'get' 'pods' --as=<user-id-from-idp>

# List users subject to RBAC rules
kubectl get users  # via plugin or external tool
```

### Break-Glass Login

A break-glass (emergency access) procedure must be documented and tested:

```bash
# Break-glass: use a local account when IdP is unavailable
kubectl --kubeconfig=<break-glass-kubeconfig> get nodes
# The break-glass account must have only emergency privileges
# Never grant break-glass accounts cluster-admin unless in true emergency
```

### IdP-Down Exception Process

1. Document the break-glass local account and its kubeconfig
2. Grant minimal required privileges (not cluster-admin)
3. Store credentials in a password manager or Vault
4. Alert on usage: `audit on break-glass login and notify security team`
5. Restore IdP connectivity as soon as possible
6. Rotate the break-glass credentials after use

---\n\n## 6.4 RBAC Rollout Strategy

### Step 1: Inventory Existing Rules

```bash
# List all ClusterRoles and Roles
kubectl get clusterrole --output yaml > clusterroles.yaml
kubectl get role --all-namespaces > roles-by-ns.yaml

# Identify overly broad rules
grep -A5 "verbs:\ [\"*\"]" clusterroles.yaml | head -30
```

### Step 2: Narrow Broad Rules

For each broad rule found, create a more restrictive replacement:

```yaml
# Before: overly broad rule
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: old-role
  namespace: team-alpha
rules:
  - apiGroups: [""]
    resources: ["*"]
    verbs: ["*"]

# After: narrowed rule
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: new-role
  namespace: team-alpha
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
```

### Step 3: Deploy Narrowed Rules

```bash
# Apply the new restricted role
kubectl apply -f new-role.yaml

# Verify the old role is no longer used
kubectl replace -f old-role.yaml --force  # or delete after verification

# Test that intended workloads still function
kubectl auth can-i 'get' 'pods' --namespace=team-alpha --as=<service-account>
```

### Step 4: Quarterly Review

1. Review all ClusterRoles and Roles for overly broad rules
2. Narrow any rules that have become unnecessary
3. Document any required broad rules with justification and risk acceptance
4. Update the RBAC exceptions registry

---\n\n## 6.5 Common RBAC Patterns

### Minimal Role for Pod Management

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-manager
  namespace: team-alpha
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/exec", "pods/portforward"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

**Critical**: `pods/exec` and `pods/portforward` provide shell-like access to the node; these must be restricted via RBAC andNetworkPolicy where possible. Grant only the verbs required for the workload's operation.

### View Role for Read-Only Access

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: viewer
  namespace: team-alpha
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
```

### Admin Role for Namespace Operations

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: namespace-admin
  namespace: team-alpha
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets", "deployments"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

---\n\n## 6.6 RBAC Troubleshooting

| Symptom | Expected Cause | Corrective Action |
|---|---|---|
| `kubectl auth can-i` returns `no` for intended action | Role/binding missing or too restrictive | Add the required verb/resource combination |
| `kubectl auth can-i '*' '*'` returns `yes` for a non-admin user | `system:authenticated` has wildcard access | Narrow `system:authenticated` rules to specific operations |
| `pods/exec` works for unintended user | `pods/exec` verb granted too broadly | Remove `pods/exec` from roles unless specifically required |
| Service account cannot pull images | Image pull secret missing or wrong | Add or fix `imagePullSecret` in pod spec or service account |
| `kubectl apply` rejected with RBAC error | Missing `create` verb on resource | Add the required verb to the role/binding |

---\n--- 

*End of Section 6 — RBAC and Identity*