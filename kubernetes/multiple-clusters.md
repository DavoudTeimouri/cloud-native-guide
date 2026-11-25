# Multiple Kubernetes Clusters

This document describes the multi-cluster architecture and management.

## Overview

The platform supports multiple Kubernetes clusters managed by a single Rancher instance.

## Cluster Types

| Cluster Type | Purpose | Control Plane |
|---|---|---|
| Management | Rancher, Argo CD, Keycloak, Observability | 3 nodes |
| Application (General) | General workloads | 3 nodes |
| Application (GPU) | AI/ML workloads | 3 + GPU workers |
| Application (Storage) | Ceph CSI, Rook-Ceph | 3 + storage workers |

## Cluster Lifecycle

### Creation

```bash
# Via Rancher UI or API
# Or via Kubespray inventory
```

### Registration

```bash
# Rancher imports existing cluster
kubectl apply -f https://rancher.internal/v3/import/<cluster-id>.yaml
```

### Upgrade

```bash
# Via Rancher or Kubespray
kubespray upgrade -i inventory/production -e kube_version=v1.37.0
```

## Cluster Registration

### Via Rancher UI

1. Navigate to **Clusters** → **Create**
2. Select **Import existing cluster**
3. Follow the generated `kubectl apply` command

### Via CLI

```bash
# Get registration token from Rancher
curl -k -X POST https://rancher.internal/v3/clusters \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"app-cluster-1","type":"import"}'

# Apply the generated manifest on the target cluster
kubectl apply -f <generated-manifest>.yaml
```

## Cluster Types

### Management Cluster

- **Components**: Rancher, Argo CD, Keycloak, Prometheus/Grafana/Loki, GitLab Runner
- **Workers**: 3 infrastructure workers (no app workloads)
- **Purpose**: Platform management, GitOps, identity, observability

### Application Clusters

- **Control Plane**: 3 nodes per cluster, stacked etcd
- **Workers**: General, GPU, Storage-facing pools
- **Components**: Cilium CNI, MetalLB, NGINX Gateway Fabric, Rook-Ceph CSI, ExternalDNS, cert-manager
- **No**: Rancher, Vault server, GitLab

## Multi-Cluster GitOps

Argo CD manages all clusters via App-of-Apps pattern:

```yaml
# Root Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform
  namespace: argocd
spec:
  project: platform
  source:
    repoURL: https://gitlab.internal/platform/apps.git
    targetRevision: main
    path: clusters/production
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
```

Each application cluster has its own Argo CD Application pointing to its own path in the Git repo.

## Inter-Cluster Communication

- **Service Mesh**: Not deployed initially (ADR-0009)
- **Cross-cluster DNS**: ExternalDNS creates records in internal DNS
- **Service Discovery**: Internal DNS zone `internal.example.com`
- **API Access**: Via Rancher proxy or direct kubeconfig

## Cluster Upgrade Strategy

1. **Staging first**: Upgrade staging cluster first
2. **One at a time**: Upgrade one application cluster at a time
3. **Rollback plan**: `kubespray reset` + rebuild from inventory
4. **Validation**: Acceptance tests after each upgrade

## Cluster Decommissioning

1. Drain workloads: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`
2. Remove from Rancher: UI → Cluster → Delete
3. Clean up: `kubespray reset` on nodes
4. Remove from Argo CD: Delete Application resources

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*