# Kubernetes Cluster Topology (TASK 006)

## 1. Purpose
Define the Kubernetes cluster topology for the Lab: number of clusters, control-plane node count, worker roles and counts, and the management cluster placement. All figures are planning inputs pending the infrastructure inventory.

## 2. Existing decisions (from prior tasks)
- Kubespray v2.32.0 deploys Kubernetes.
- Base version: K8s v1.36.5; upgrade path to v1.37.0; no version-skipping.
- Rancher manages multiple clusters (ADR-0011).
- Argo CD provides GitOps for all clusters (ADR-0014).
- Cilium is the primary CNI candidate; Calico is the alternative (`compatibility/version-matrix.md`: Cilium 1.20.3, Calico 3.31.7).
- Vault runs on dedicated hosts outside clusters (ADR-0016).

## 3. Control-plane node count: three vs five
| Criterion | Three control-plane nodes | Five control-plane nodes |
|---|---|---|
| etcd quorum | 2 of 3 (1 fault tolerance) | 3 of 5 (2 fault tolerance) |
| etcd write latency | Lower | Higher (more raft participants) |
| Cost / resource overhead | Lower | Higher |
| Failure scenarios exercised | Single node loss | Double node loss |
| Operational complexity | Lower | Higher |
| Recommended for initial Lab | Yes | No — only if control-plane HA failure scenarios are explicitly tested |

Recommendation: start with three control-plane nodes per cluster. Expand to five only when the Lab explicitly tests double-control-plane failure and etcd quorum recovery. Do not assume five is always better — the added etcd latency and cost are rarely justified in a Lab.

## 4. Recommended cluster topologies

### Initial Lab: one management cluster + one workload cluster
| Cluster | Purpose | Control plane | Workers |
|---|---|---|---|
| Management | Rancher, Argo CD, Keycloak, observability | 3 nodes | 2 infra workers |
| Workload (app) | General application workloads | 3 nodes | 3 workers |

Rationale: exercises the multi-cluster pattern with minimum footprint. Management cluster is not required to recover the workload cluster — each has independent etcd and Kubespray rebuild path. If the Management Cluster is unavailable, workload clusters keep running (data plane unaffected) but cannot be managed, upgraded, or have new workloads deployed via Rancher/Argo CD until management is restored. Operators can reach the Workload Cluster API directly via its control-plane VIP using a static admin kubeconfig (break-glass credentials), not via Rancher/Argo CD.

### Expansion option A: one management + two workload clusters
Adds a second application cluster (general workloads) with its own CIDRs and sizing. Tests cluster separation and Rancher multi-cluster management.

### Expansion option B: dedicated GPU / storage workload clusters
- GPU cluster: 3 control-plane + GPU workers (NVIDIA passthrough, optional future extension).
- Storage cluster: 3 control-plane + dedicated storage workers for Ceph/Rook OSD.

## 5. Worker roles and counts
| Role | Purpose | Count (initial Lab) |
|---|---|---|
| Infra worker | Ingress, monitoring, logging, registry proxy | 2 (in management cluster) |
| Application worker | General workloads | 3 (in workload cluster) |
| Storage worker | Ceph OSD / Rook-Ceph (if storage included) | 3 (dedicated, optional) |
| GPU worker | AI/ML inference (optional future) | 0 initial; extend later |

Do not colocate Ceph OSD and general application workers on the same node in the Recommended/Expanded profiles — storage I/O can starve workloads.

## 6. Cluster separation
Determine the initial Lab contents:

| Option | Description | Operational consequence | Resource consequence |
|---|---|---|---|
| One management + one workload | Recommended initial | Simplest, exercises multi-cluster pattern | Lowest |
| One management + two workloads | Expansion | More clusters to manage via Rancher; tests workload mobility | ~2× workload nodes |
| Two independent clusters, no management | Not recommended | No centralized management; contradicts ADR-0011 | Similar total, less managed |

Recommended initial: **one management cluster + one workload cluster**. Expand to two workload clusters after the initial Lab is validated.

## 7. Management plane failure and recovery
- The management cluster runs Rancher, Argo CD, Keycloak, observability.
- Management cluster has independent recovery: etcd snapshot + Kubespray rebuild, separate from workload clusters.
- Do NOT design so the management cluster is required to recover the workload clusters without an independent recovery path. Each workload cluster can be rebuilt independently via Kubespray inventory.
- If the management cluster is unavailable, workload clusters continue running (data plane unaffected) but cannot be managed, upgraded, or have new workloads deployed via Rancher/Argo CD until management is restored.

## 8. CIDR and network isolation
Each cluster uses its own:
- Pod CIDR: `<POD_CIDR_1>` (workload), `<POD_CIDR_MGMT>` (management)
- Service CIDR: `<SERVICE_CIDR_1>`, `<SERVICE_CIDR_MGMT>`
- Control-plane VIP: `<LB_VIP_1>`, `<LB_VIP_MGMT>`

CIDRs must not overlap with each other or with existing production networks (see `lab/network-and-vlan-design.md` for CIDR overlap risks).

## 9. Open questions
1. How many workload clusters does the Lab need initially? (Recommended: one.)
2. Three or five control-plane nodes? (Recommended: three.)
3. Are dedicated storage workers available for Ceph/Rook-Ceph?
4. Is GPU passthrough available for the optional GPU worker extension?
