# Management Cluster Alternatives

This document evaluates alternatives for the management cluster architecture.

## Current Architecture (Chosen)

| Component | Decision | ADR |
|---|---|---|
| Rancher | Multi-cluster management | ADR-0011 |
| Argo CD | GitOps for all clusters | ADR-0014 |
| Keycloak | Centralized OIDC/SAML | ADR-0031 |
| Vault | Dedicated hosts, outside clusters | ADR-0016 |

## Evaluated Alternatives

### 1. Rancher vs. Native kubectl + Scripts

| Criterion | Rancher | Native kubectl + Scripts |
|---|---|---|
| Multi-cluster management | Native, UI + API | Custom scripts required |
| RBAC integration | Keycloak OIDC built-in | Manual kubeconfig distribution |
| Fleet/Continuous Delivery | Built-in (Fleet) | Argo CD separate |
| Upgrade management | Built-in, version-pinned | Manual kubespray runs |
| Learning curve | Moderate | Low |
| Licensing | Open source (SUSE) | Free |

**Decision**: Rancher chosen for enterprise-grade multi-cluster management.

### 2. Argo CD vs. Flux CD

| Criterion | Argo CD | Flux CD |
|---|---|---|
| UI | Rich, feature-rich | Minimal |
| Multi-tenancy | Projects, RBAC | Namespaces + Kustomize |
| Helm support | Native, first-class | HelmRelease CRD |
| Kustomize | Supported | Native |
| Multi-cluster | App-of-Apps pattern | Multi-cluster via GitRepository |
| Community | Large, CNCF graduated | Large, CNCF graduated |

**Decision**: Argo CD chosen for richer UI and better multi-tenancy model.

### 3. Keycloak vs. Dex vs. OIDC Proxy

| Criterion | Keycloak | Dex | OIDC Proxy |
|---|---|---|---|
| Features | Full IAM (SSO, MFA, LDAP, SAML, Kerberos) | OIDC only, minimal | Proxy only |
| AD/LDAP integration | Native | LDAP connector only | No |
| User management UI | Full admin console | Minimal | None |
| Multi-tenancy | Realms | Connectors | No |
| Scalability | HA with clustering | Limited | Simple |

**Decision**: Keycloak chosen for enterprise features and AD integration.

### 4. Vault on Dedicated Hosts vs. In-Cluster

| Criterion | Dedicated Hosts | In-Cluster (Raft) |
|---|---|---|
| Blast radius | Isolated from cluster failure | Vault down = cluster secrets down |
| Unseal | Offline Shamir shares | Auto-unseal needs KMS |
| Upgrades | Independent of cluster | Coupled to cluster upgrades |
| HA | 3+ dedicated nodes | 3+ pods in cluster |
| Cost | 3 dedicated servers | 3 pods on existing workers |

**Decision**: Dedicated hosts per ADR-0016 — Vault must survive cluster loss.

### 5. Ceph Standalone vs. Rook-Ceph Only

| Criterion | Ceph (cephadm) + Rook | Rook Only |
|---|---|---|
| Use case | Standalone storage cluster + in-cluster CSI | In-cluster only |
| Failure domain | Independent of K8s | Tied to K8s cluster |
| Management | cephadm + Rook operator | Rook operator only |
| Upgrade independence | Yes | Coupled |
| Complexity | Higher | Lower |

**Decision**: Both — standalone Ceph for infrastructure storage, Rook-Ceph for in-cluster CSI.

### 3 vs 5 Control Plane Nodes

| Criterion | 3 Nodes | 5 Nodes |
|---|---|---|
| etcd quorum | 2/3 | 3/5 |
| Failure tolerance | 1 node | 2 nodes |
| Resource cost | Lower | Higher |
| Network latency | Lower | Slightly higher |

**Decision**: 3 nodes minimum, 5 documented as reference topology for larger sites (ADR-0002).

---

## Not Adopted (Rejected)

| Option | Reason |
|---|---|
| OpenShift | Vendor lock-in, cost, heavier |
| TKS/TKG | Vendor-specific, less flexible |
| EKS/GKE/AKS | Not air-gap compatible |
| Pure Flux | Less mature multi-tenancy |
| Vault in-cluster | Violates ADR-0025 (circular dependency) |
| Single control plane | No HA |
| Single LB | No HA |

---

*Status: DRAFT | Owner: Platform Architecture | Last reviewed: 2026-11-23*