# Lab Architecture Overview (TASK 006)

## 1. Purpose and scope
This document defines the target architecture and capacity plan for the Cloud-Native Stack Lab. It is **planning and architecture only**. No infrastructure is deployed, modified, or validated here.

The Lab transitions the project from documentation completion (P11.5–P11.9) toward a controlled implementation phase. Every statement below is a proposal pending user confirmation of the actual infrastructure inventory.

## 2. Classification of resources
Distinguish these four categories throughout planning. Never treat existing production capacity as available Lab capacity.

| Category | Meaning | Example |
|---|---|---|
| Existing production infrastructure | Servers/services already running production workloads | Production Kubernetes clusters, production Ceph |
| Existing virtualized Ceph | Ceph already running under a hypervisor elsewhere | A virtualized Ceph cluster on existing VM hosts |
| Proposed Lab resources | Resources this document recommends acquiring/allocating for the Lab | Lab management cluster, lab worker nodes |
| Available but unconfirmed resources | Capacity that might exist but is not yet verified | Spare hypervisor hosts, unallocated VLANs |

## 3. Target platform components
The Cloud-Native Stack target includes:

- OS: Oracle Linux and Ubuntu (per Kubespray release-2.32 kernel matrix)
- Kubernetes: deployed via Kubespray v2.32.0, base K8s v1.36.5, upgrade path v1.37.0
- Cluster management: Rancher (ADR-0011), GitOps: Argo CD (ADR-0014), identity: Keycloak (ADR-0031), secrets: Vault on dedicated hosts outside clusters (ADR-0016)
- CNI: Cilium (primary candidate), Calico (alternative)
- SDS: Ceph primary, Rook-Ceph optional Kubernetes-native deployment
- Repositories/registry: Nexus (OS/packages/artifacts), Harbor (OCI images)
- Load balancing: HAProxy/Nginx + Keepalived VIP
- Observability: Prometheus, Grafana, Alertmanager, Thanos, Loki, Fluent Bit
- Security: Gatekeeper/Kyverno, Falco, cert-manager
- Backup/restore: Velero (implied by backup runbooks)

## 4. Recommended initial implementation topology
**One management cluster + one workload cluster** as the initial Lab. Rationale:

- Lowest resource footprint that still exercises the multi-cluster pattern (management cluster runs Rancher/Argo CD/Keycloak/observability; workload cluster runs applications).
- Management cluster has an independent recovery path (etcd snapshot + Kubespray rebuild) and is not required to recover the workload cluster. Per ADR-0025, management cluster restore requires Vault (secrets) and Keycloak (identity) to be restored first — workload cluster recovery is **not** dependent on the Management Cluster.
- Can expand later to one management + two workload clusters, or add GPU/storage-specialized workload clusters, without redesign.

Explicitly not recommended for the initial Lab:
- Two independent clusters without a dedicated management cluster (loses centralized management, contradicts ADR-0011).
- Five control-plane nodes per cluster as the default (see Section 5 of `lab/kubernetes-cluster-topology.md`).

## 5. Key architectural constraints
- Internal Kubernetes nodes must not have uncontrolled public Internet access. All egress flows through the External Upstream layer (Nexus/Harbor proxy/sync), per the two-tier repository & registry architecture (`architecture/two-tier-repository-registry.md`).
- Vault runs on dedicated hosts outside Kubernetes clusters (ADR-0016). Keycloak and observability run in the management cluster.
- etcd quorum loss and kube-apiserver failure have different failure modes and recovery procedures (corrected in P11.9 — one-way hard startup dependency kube-apiserver → etcd, not a circular deadlock).
- No concrete hardware specifications, IP addresses, VLAN IDs, or capacity figures are invented here. All are placeholders pending the infrastructure inventory.

## 6. Deliverables
| Document | Purpose |
|---|---|
| `lab/infrastructure-inventory-template.md` | Infrastructure inventory and assumption register |
| `lab/kubernetes-cluster-topology.md` | Cluster topology, control-plane vs worker sizing |
| `lab/compute-capacity-planning.md` | Compute/memory/storage/network estimates, three Lab profiles |
| `lab/storage-architecture.md` | Ceph vs Rook-Ceph comparison and recommendation |
| `lab/network-and-vlan-design.md` | Network/VLAN segmentation, placeholders, IP template |
| `lab/repository-registry-bootstrap.md` | Nexus/Harbor, External Upstream, bootstrap sequence |
| `lab/security-and-identity-design.md` | Keycloak, Vault, RBAC, certificate strategy |
| `lab/availability-backup-and-recovery.md` | Failure domains, HA, backup destinations |
| `lab/deployment-dependency-sequence.md` | Ordered implementation sequence |
| `lab/assumptions-and-open-decisions.md` | Decision register and items requiring user confirmation |

## 7. Open questions requiring user confirmation
These must be answered before any implementation:

1. What physical servers or hypervisor hosts are available for the Lab? (CPU models, cores, RAM per host, local disk, NIC count/speed.)
2. Is there an existing hypervisor (KVM, VMware, oVirt, Nutanix) with allocatable capacity?
3. What VLANs and IP subnets are available, and who controls allocation?
4. Is there an existing internal DNS/NTP service the Lab can use?
5. Is there an existing Ceph deployment (physical or virtualized) whose capacity could host Lab storage?
6. What is the internet egress policy — direct, proxy, or fully restricted?
7. Is Active Directory available for identity integration, or is local identity acceptable for the Lab?

Stop here until the user confirms or declines each item.
