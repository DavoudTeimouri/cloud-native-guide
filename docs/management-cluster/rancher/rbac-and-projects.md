# Rancher RBAC: Projects, Namespaces, and Multi-Tenancy

## Overview

This document describes Rancher's RBAC model for managing access across projects, namespaces, and resource quotas. It covers role templates, global vs project-scoped roles, and multi-tenancy patterns for platform teams.

## Project-Level RBAC

### Rancher Project Roles

Rancher provides three default project roles that control what members can do within a project:

| Role | Scope | Capabilities |
|------|-------|--------------|
| **Admin** | Project | Full access including user management, project settings, and all resources |
| **Member** | Project | Read/write access to most resources, cannot manage project settings or users |
| **Viewer** | Project | Read-only access to project resources and metadata |

### Custom Role Templates

Platform teams can create custom role templates using the Rancher API or `kubectl` against the `management-cluster`. Role templates define precise permissions and can be bound to groups or users.

```yaml
# Custom role template example
apiVersion: v3.rancher.io/v1
kind: RoleTemplate
metadata:
  name: restricted-developer
spec:
  description: "Restricted developer role - no cluster-scoped resources"
  targets:
    - targetKind: Project
      targetName: project-name
  permissions:
    - apiGroups: [""]
      resources: ["pods", "services", "configmaps"]
      verbs: ["get", "list", "watch", "create", "update", "patch"]
    - apiGroups: ["apps"]
      resources: ["deployments"]
      verbs: ["get", "list", "watch", "create", "update", "patch"]
```

## Namespace-Scoped RBAC

### Kubernetes RBAC Within Projects

Inside each Rancher project, standard Kubernetes RBAC applies within project namespaces. This allows granular control over which applications and operators can access which namespaces.

```yaml
# Namespace-level Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: namespace-reader
  namespace: app-production
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "ingresses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
```

### Service Account Scoping

Service accounts should be scoped to specific namespaces to limit blast radius. Use project-level service account projections to avoid cross-project leakage.

## Resource Quotas

Resource quotas enforce per-project resource limits and prevent namespace-level overconsumption.

```yaml
# Resource quota example
apiVersion: v1
kind: ResourceQuota
metadata:
  name: project-quota
  namespace: project-name
spec:
  hard:
    cpu: "4"
    memory: "8Gi"
    pods: "20"
    services: "10"
    persistentvolumeclaims: "5"
    requests.cpu: "2"
    requests.memory: "4Gi"
    limits.cpu: "4"
    limits.memory: "8Gi"
```

## Global vs Project-Scoped Roles

### Global Roles

Global roles apply across **all projects** in the Rancher management cluster. Use sparingly for cluster-wide operations.

| Role Type | When to Use |
|-----------|-------------|
| **cluster-admin** | Cluster infrastructure, add-on deployment, disaster recovery |
| **cluster-reader** | Observability, monitoring, audit tools |
| **Custom global roles** | API server access, certificate rotation, Velero backup |

### Project-Scoped Roles

Project-scoped roles apply only within their specific project. This is the default and recommended approach for application teams.

| Role Type | When to Use |
|-----------|-------------|
| **project-admin** | Platform teams managing a specific project |
| **project-member** | Application developers within a project |
| **project-viewer** | Auditors, compliance teams |

### Migration Pattern

When moving from global to project-scoped roles:

1. Identify all global role bindings
2. Create equivalent project role templates
3. Bind to specific projects instead of cluster-wide
4. Verify no functional gaps
5. Decommission global bindings

## Multi-Tenancy Patterns

### Pattern 1: Shared Infrastructure, Isolated Workloads

- Single Rancher management cluster
- Multiple projects for different teams/departments
- Resource quotas enforce isolation
- Network policies prevent cross-project traffic

### Pattern 2: Dedicated Management Clusters per Tenant

- Separate management clusters for each tenant/org
- Centralized identity provider (Keycloak/OIDC)
- Federation for cross-tenant visibility
- Higher operational overhead

### Pattern 3: Fleet-Driven Multi-Tenancy

- Use Rancher Fleet for cluster management
- Applications deployed as GitOps via Argo CD
- Project boundaries enforced via namespace templates
- Role templates deployed as Git manifests

```yaml
# Fleet role template deployment example
apiVersion: fleets Rancher/v1
kind: GitConfig
metadata:
  name: rbac-templates
spec:
  repo:
    url: https://github.com/org/rancher-configs
    branch: main
  paths:
    - management-cluster/rancher/rbac-role-templates/
```

## Best Practices

1. **Prefer project-scoped roles** over global roles for application teams
2. **Use role templates** to codify permissions in Git, enabling review and change tracking
3. **Enforce resource quotas** on every project to prevent resource exhaustion
4. **Implement namespace segregation** within projects for different application environments
5. **Audit role bindings quarterly** to remove unused or overly permissive roles
6. **Use OIDC group mapping** (Keycloak → Rancher roles) for centralized identity management
7. **Document role purpose** in the template metadata for future maintainers

## Cross-References

- `management-cluster/rancher/access-management.md` — Service accounts, OIDC integration, role bindings
- `management-cluster/rancher/cluster-onboarding.md` — Cluster import and provisioning
- `kubernetes/security/security-controls.md` §RBAC — Kubernetes RBAC complement
- `management-cluster/argocd/argocd.md` — GitOps deployment of RBAC configurations
