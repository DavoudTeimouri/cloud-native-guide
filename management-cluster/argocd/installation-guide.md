# Argo CD Installation Guide

## A. Installation

### Argo CD Server

```bash
# Create the Argo CD namespace
kubectl create namespace argocd

# Install Argo CD using the official manifest
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for the server to become ready
kubectl -n argocd rollout status deployment/argocd-server --timeout=300s

# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

### High Availability Setup

For production deployments, deploy Argo CD with HA configuration:

- `argocd-server`, `argocd-repo-server`, `argocd-application-controller` with `replicas: 2`
- Redis with a sentinel or a managed HA Redis instance
- PostgreSQL as the backend database (never SQLite in production)
- A separate `argocd-application-controller` per cluster for large fleets, with sharding

## B. Configuration

### Application Projects

Create an `AppProject` for each team or group to organize applications and restrict destinations:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-payments
  namespace: argocd
spec:
  description: Payments team applications
  sourceRepos:
    - https://gitlab.internal/apps/payments
  destinations:
    - namespace: payments
      server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  namespaceResourceWhitelist: []
  clusterResourceBlacklist:
    - group: rbac.authorization.k8s.io
      kind: ClusterRole
    - group: rbac.authorization.k8s.io
      kind: ClusterRoleBinding
  namespaceResourceBlacklist:
    - group: ""
      kind: Pod
```

Restricting destinations prevents a team from deploying into platform namespaces.

### ConfigMap Settings

Configure the Argo CD ConfigMap (`argocd-cm`) for site-wide settings:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  application.resourceTrackingMethod: annotation
  application.instanceLabelKey: argocd.argoproj.io/instance
  # OIDC configuration is configured via the argocd-cm ConfigMap
  oidc.config: |
    name: Keycloak
    issuer: https://keycloak.internal/realms/platform
    clientID: argocd
    clientSecret: $oidc-keycloak:oidc.clientSecret
    requestedScopes: openid,profile,email,groups
    groupMappingEnabled: "true"
    groupsClaim: groups
    groupMapping:
      "platform-admins": role:admin
      "platform-operators": role:admin
      "developers": role:readonly
    scopes:
      - group:platform-admins
      - group:platform-operators
```

The `clientSecret` is referenced using the `$namespace:key` syntax, which Argo CD resolves against secrets in the `argocd` namespace.

### TLS for Internal CA

Mount the internal CA certificate into the repo-server pods so Argo CD can trust internal Git hosts:

```yaml
# In the repo-server Deployment
volumeMounts:
  - name: ca
    mountPath: /etc/ssl/certs/ca-certificates.crt
    subPath: ca-certificates.crt
volumes:
  - name: ca
    configMap:
      name: argocd-ca
      items:
        - key: ca-certificates.crt
          path: ca-certificates.crt
```

## C. Application Setup

### Creating an Application

Define an Argo CD `Application` to represent a Kubernetes workload:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: payments-api
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: team-payments
  source:
    repoURL: https://gitlab.internal/apps/payments
    targetRevision: main
    path: k8s/api
    helm:
      valueFiles: [values-production.yaml]
  destination:
    server: https://kubernetes.default.svc
    namespace: payments
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    retry:
      limit: 5
      backoff:
        duration: 15s
        factor: 2
        maxDuration: 5m
```

### ApplicationSet for Fleet Management

Use `ApplicationSet` to manage a fleet of identical services:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: microservices
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - service: payments
            tier: gold
          - service: ledger
            tier: gold
          - service: notify
            tier: silver
  template:
    metadata:
      name: '{{service}}'
    spec:
      project: team-payments
      source:
        repoURL: https://gitlab.internal/apps/payments
        targetRevision: main
        path: 'k8s/{{service}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{service}}'
      syncPolicy:
        automated: {prune: true, selfHeal: true}
```

### Git Generator for Directory-of-Services Layout

```yaml
  generators:
    - git:
        repoURL: https://gitlab.internal/apps/payments
        revision: main
        directories:
          - path: k8s/*
```

### Offline Configuration

- Internal GitLab: `repoURL` points at the internal GitLab instance
- Internal image registry: Images already named with the internal registry in Git, or use `argocd-cm` resource customizations
- Repository credentials: Argo CD repository secret in the `argocd` namespace, sourced from Vault via External Secrets
- TLS trust for internal CA: Mounted into repo-server pods as described above

## D. Sync Waves

### Controlling Sync Order

Sync waves control the order in which resources are created across multiple applications. Set the sync wave via annotation:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"
```

### Example: Platform Application with Sync Wave

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "0"
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
  source:
    directoryRecurse: true
    kustomize:
      namePrefix: platform-
  destination:
    server: https://kubernetes.default.svc
    namespace: platform
```

### Sync Wave Hierarchy

- Lower wave numbers sync first (wave "0" before wave "1", etc.)
- Applications at the same wave sync in parallel
- Sync waves prevent resource ordering issues when one application depends on resources created by another
- Use cases: placing core infrastructure applications at wave "0", followed by dependent services at higher wave numbers

### Setting Sync Waves via CLI

```bash
# Set sync wave for an application
argocd app set <application> --annotation argocd.argoproj.io/sync-wave="1"

# View current sync wave annotation
argocd app get <application> --metric annotation.argocd.argoproj.io/sync-wave
```

## E. Validation

### Check Application Status

```bash
# List all applications
argocd app list

# Get detailed status of a specific application
argocd app get payments-api

# View sync history
argocd app history payments-api

# Diff between Git and cluster state
argocd app diff payments-api
```

### Healthy State Expectations

- `Sync Status: Synced`
- `Health Status: Healthy`
- No `OutOfSync` on a quiet system

### From Inside the Cluster

```bash
# List applications managed by Argo CD
kubectl -n argocd get applications

# Describe a specific application
kubectl -n argocd describe application payments-api
```

## F. Operations

### Promote a Version

Merge to `main`; Argo CD syncs automatically (respecting sync wave order).

### Rollback

```bash
# Roll back to a previous revision
argocd app rollback <application> <revision>
```

### Pause an Application

```bash
# Prevent Argo CD from auto-syncing during an incident
argocd app set <app> --sync-policy=none
```

### Add or Delete a Resource

- Add it to Git; Argo CD adopts or creates it
- Remove it from Git; with `prune: true` Argo CD deletes it — confirm the resource is not stateful

### Refresh a Secret

```bash
argocd app get <app> --refresh
```

## G. Cross-References

- `management-cluster/argocd/argocd.md` — Full Argo CD reference
- `management-cluster/argocd/application-sync.md` — Sync procedures, drift detection, rollback
- `management-cluster/argocd/drift-detection.md` — Drift detection frequency and conflict resolution

## H. Best Practices

- `prune: true` and `selfHeal: true` for application workloads (explicit review for stateful resources)
- `AppProject` per team with restricted destinations and resource whitelists
- `ServerSideApply=true` for large applications
- Repository credentials from Vault via External Secrets, never inline in Application manifests
- Pin the Argo CD version and mirror internal images
- The App-of-apps pattern: one root Application that creates platform Applications
- A sync window per project to avoid fleet-wide sync at the same moment
- Health checks customized per resource type in `argocd-cm`
- Argo CD notifications for sync failures, wired to Alertmanager
