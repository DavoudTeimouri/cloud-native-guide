# Assumptions and Open Decisions (TASK 006)

## 1. Purpose
Decision register for Lab architecture. Each decision lists the recommended option, alternatives, reasoning, resource impact, risks, required user confirmation, and whether it blocks implementation. These are proposals, not approved ADRs. Do not create or modify ADRs without explicit authorization.

## 2. Decision register

| # | Decision | Recommended option | Alternatives | Reasoning | Resource impact | Risks | User confirmation needed? | Blocks implementation? |
|---|---|---|---|---|---|---|---|---|
| D1 | Number of clusters | One management + one workload | One mgmt + two workloads; two independent | Simplest, exercises multi-cluster pattern, lowest footprint | Low | Management cluster is a single point of management | Yes | No |
| D2 | Control-plane node count | Three per cluster | Five per cluster | Lower cost/latency; 1 fault tolerance sufficient for Lab | Lower vs five | Only 1 fault tolerance | Yes | No |
| D3 | Worker roles | Infra + app + optional storage | Combined infra/app | Separation prevents storage I/O starvation | +3 storage nodes (optional) | More nodes to manage | Yes | No (optional) |
| D4 | Management cluster placement | Dedicated cluster | Colocated with workload | Independent recovery path; contradicts ADR-0011 if colocated | +3 control-plane nodes | Single point of management | Yes | Yes |
| D5 | Dedicated Ceph vs Rook-Ceph | Dedicated Ceph (Recommended/Expanded) | Rook-Ceph; local-path (Small) | Separation of storage lifecycle from K8s; avoids Rook control-plane coupling | +6+ storage nodes | More hardware | Yes | Yes (if storage needed) |
| D6 | Storage network design | Separate Ceph public + cluster subnets | Single shared subnet | Ceph replication traffic isolated; less contention | 2 subnets | More network complexity | Yes | Yes (if Ceph) |
| D7 | Load-balancer HA model | Keepalived Active/Passive VIP | Active/Active; DNS-based | Two LB servers + single VIP = Active/Passive, not true Active/Active | +2 LB servers | Brief failover window | Yes | Yes |
| D8 | Repository and registry placement | Nexus + Harbor in mgmt cluster / dedicated VMs | External SaaS; single registry | Two-tier design; internal nodes have no public egress | Disk for caches/layers | Backup of repos needed | Yes | Yes |
| D9 | Identity architecture | Local Keycloak identity | AD/LDAP-integrated | Simplest; no external dependency for Lab | Keycloak + PostgreSQL | No SSO integration initially | Yes | No |
| D10 | Backup destination | RGW/S3 object storage | NFS; external object store | Aligns with Ceph storage plan | Object storage capacity | Backup target must exist | Yes | No |
| D11 | Hypervisor vs bare metal | TBD — inventory dependent | Either | Depends on available hardware | Varies | Passthrough disks for Ceph may not be virtualizable | Yes | Yes |
| D12 | GPU extension | Optional future | Initial | Not needed for initial Lab validation | GPU nodes + passthrough | Adds complexity | Yes | No |

## 3. Decisions requiring user confirmation (priority order)
1. **D11** Hypervisor vs bare metal — determines all sizing and passthrough feasibility.
2. **D4** Management cluster placement — commits 3+ control-plane nodes.
3. **D5** Dedicated Ceph vs Rook-Ceph — commits storage hardware.
4. **D1** Number of clusters — commits total node count.
5. **D2** Control-plane node count — three vs five.
6. **D7** Load-balancer HA model — commits 2 LB servers + VIP allocation.

## 4. Critical blockers
| Blocker | Dependency | Resolution required |
|---|---|---|
| B1 | No confirmed hardware inventory | User must confirm servers/hypervisor before any sizing is valid |
| B2 | No confirmed VLANs/IP subnets | Network design cannot be realized; CIDR overlap risk |
| B3 | No confirmed OSD/disk passthrough | Ceph/Rook-Ceph cannot be deployed |
| B4 | No confirmed internet egress policy | Repository bootstrap path undefined |
| B5 | No user sign-off on decision register | No implementation may proceed |

## 5. Relationship to P11.8/P11.9 readiness
This architecture is consistent with `lab-readiness-traceability.md`:
- Components #1 (infrastructure), #3 (control plane), #4 (workers), #5 (CNI) are `REQUIRES LAB VALIDATION`.
- Components #2 (OS), #9 (LB), #10 (observability) are `READY WITH CONDITIONS`.
- Components #6 (Ceph/Rook), #7 (Rancher), #8 (Nexus/Harbor), #12 (Vault/Keycloak), #13 (Argo CD/Ingress/cert-manager), #14 (Security) are `BLOCKED BY PREREQUISITES`.

This document does not change those classifications. It defines the architecture under which they will be validated.

## 6. Open questions for the user
1. Confirm or revise each decision in the register (D1-D12).
2. Confirm the infrastructure inventory (see `lab/infrastructure-inventory-template.md`).
3. Confirm which Lab profile to target: Small, Recommended, or Expanded.
4. Confirm the backup target and identity integration (AD vs local).

No implementation may proceed until these are confirmed.
