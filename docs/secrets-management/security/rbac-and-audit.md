# Kubernetes RBAC and Vault Audit

## RBAC Role Design

### Core Principles
- **Least privilege**: every role grants only the minimum permissions needed
- **Namespace isolation**: roles are scoped to specific namespaces by default
- **Explicit allow**: default deny — every permission must be explicitly granted
- **Role aggregation**: combine related permissions into fewer roles to reduce combinatorial complexity

### Recommended Role Set

```yaml
# admin — full control within a namespace (emergency use only)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: admin
  namespace: production
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]

# view — read-only access for auditors and monitoring
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: view
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["batch"]
  resources: ["cronjobs"]
  verbs: ["get", "list", "watch"]

# edit — read-write for application teams (no resource creation)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: edit
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "update", "patch"]
- apiGroups: [""]
  resources: ["events"]
  verbs: ["create"]
```

### ClusterRole Design (cluster-wide)

```yaml
# cluster-admin — only for cluster operations, never assigned to users
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-admin
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
  resourceNames: [""]  # empty resourceNames = all resources, but restricted by subject

# certificate-approver — approve/rotate PKI certificates
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: certificate-approver
rules:
- apiGroups: ["certificates.k8s.io"]
  resources: ["certificatesigningrequests/approval", "certificatesigningrequests/signing"]
  verbs: ["get", "create", "update"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch"]
  resourceNames: ["ca-key-pair"]  # specific secret name

# ingress-controller — manage ingress resources
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ingress-controller
rules:
- apiGroups: [" networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "endpoints"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```