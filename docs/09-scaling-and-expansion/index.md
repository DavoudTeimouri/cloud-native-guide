# Scaling and Expansion

## Purpose and scope
Document controlled infrastructure growth: adding servers/VMs, expanding K8s clusters and worker pools, adding app clusters and GPU workers, expanding Ceph/storage/repo/monitoring/LB capacity, network and IP pool expansion. Includes capacity planning, risk analysis, prerequisites, execution procedures, and post-expansion validation.

## Subsections
| Subsection | Covers |
|---|---|
| [Adding Physical Servers & VMs](09-adding-physical-vm.md) | Add physical servers and VMs; hardware prep, OS prep, join to stack |
| [Expanding Kubernetes Clusters](09-expanding-k8s-clusters.md) | Add control-plane and worker nodes; preserve etcd quorum; one node at a time |
| [Adding Application Clusters](09-adding-app-clusters.md) | Prepare infra/networking, deploy additional clusters, register with Rancher, consistent config |
| [Expanding Worker & GPU Pools](09-expanding-worker-gpu-pools.md) | Expand general and GPU worker pools; node labels/taints, MIG, scheduling |
| [Expanding Ceph & Storage](09-expanding-ceph-storage.md) | Add OSDs/MON/MGR/RGW, expand pools, storage appliances |
| [Expanding Repo, Monitoring, LB](09-expanding-repo-monitoring-lb.md) | Expand registry capacity, monitoring infrastructure, load balancers |
| [Network & IP Pool Expansion](09-network-ip-pool-expansion.md) | Network expansion, IP pool expansion, CIDR changes |
| [Capacity Planning & Risk](09-capacity-planning-risk.md) | Capacity planning, growth estimates, failure tolerance, risk analysis, overcommit |

## Cross-references
- [Operating Systems (2.7 Kubernetes Nodes)](../02-components/2.7-kubernetes-nodes.md)
- [Software-Defined Storage (7.7 Maintenance and Data Protection)](../07-software-defined-storage/7.7-maintenance-and-data-protection.md)
- [Load Balancers (5.3 Application Cluster Load Balancers)](../05-load-balancers/5.3-app-cluster-lbs.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
