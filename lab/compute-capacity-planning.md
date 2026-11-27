# Compute and Capacity Planning (TASK 006)

## 1. Purpose and method
Sizing estimates for Lab components. All values are **planning estimates**, not measurements. No hardware capacity is claimed or validated.

For each component: minimum practical allocation, recommended initial Lab allocation, CPU, RAM, disk, network, HA considerations, scaling direction.

Three profiles are provided:
1. Small Lab profile — minimum for functional testing.
2. Recommended Lab profile — suitable for HA testing.
3. Expanded HA Lab profile — production-oriented sizing.

Do not add all minimum values together and present them as a sufficient shared-host design. Account for CPU overcommit, memory reservation, storage replication overhead, monitoring retention, image/package cache growth, Ceph recovery/backfill headroom, failure scenarios, and resource contention.

## 2. Sizing assumptions
- Kubespray v2.32.0, Kubernetes v1.36.5 base.
- Cilium CNI (primary), containerd 2.3.7.
- etcd 3.6.15 (3-member quorum by default; 5-member optional).
- Rook-Ceph v1.21.0 / Ceph Tentacle 20.2.4 if storage is included.
- All memory figures are guest-visible; add ~10% hypervisor overhead for VMs.
- CPU overcommit is allowed for non-latency-sensitive services only; control plane and etcd must not be overcommitted.

## 3. Control-plane node sizing
| Component | vCPU | RAM | Disk | HA notes | Scaling |
|---|---|---|---|---|---|
| Minimum control-plane node | 2 | 4 GB | 100 GB | etcd quorum needs 3 nodes | Vertical |
| Recommended control-plane node | 4 | 8 GB | 200 GB (SSD) | 3-node quorum, 1 fault tolerance | Vertical |
| Expanded control-plane node | 8 | 16 GB | 400 GB (NVMe) | 5-node quorum, 2 fault tolerance | Vertical |

Rationale:
- etcd is I/O and latency sensitive. Use local SSD/NVMe, never shared virtual disk.
- kube-apiserver, scheduler, controller-manager scale with node/pod count. 4 vCPU / 8 GB is the practical minimum for a 3-node control plane running system components plus core addons (CoreDNS, metrics-server, Cilium).
- Three vs five control-plane nodes: three gives 1 fault tolerance with lower cost; five gives 2 fault tolerance but more etcd write latency and overhead. Do not assume five is always better. Start with three; expand to five only if the Lab exercises control-plane HA failure scenarios.

## 4. Worker node sizing
| Profile | vCPU | RAM | Disk | Role | HA notes | Scaling |
|---|---|---|---|---|---|---|
| Minimum worker | 2 | 4 GB | 100 GB | General | Single point of failure if only one | Horizontal |
| Recommended worker | 4 | 8 GB | 200 GB | General/infra | 2+ nodes for pod disruption budget | Horizontal |
| Expanded worker | 8 | 16 GB | 500 GB | General + storage | Dedicated infra workers for Ceph/Rook OSD | Horizontal |
| GPU worker (optional) | 8+ | 32+ GB | 500 GB | AI/ML | GPU passthrough, not schedulable for general pods | Horizontal |

Infrastructure workers (dedicated): if running Ceph OSD or heavy ingress, dedicate worker nodes so workload scheduling is not starved.

## 5. Management services sizing (per service)
| Service | Min vCPU/RAM/disk | Recommended vCPU/RAM/disk | HA | Scaling |
|---|---|---|---|---|
| Rancher | 2 / 4 GB / 100 GB | 4 / 8 GB / 200 GB | 1 node (Lab), 3 for HA | Vertical |
| Argo CD | 2 / 4 GB / 100 GB | 4 / 8 GB / 200 GB | 1 node (Lab) | Vertical |
| Keycloak | 2 / 4 GB / 100 GB | 4 / 8 GB / 200 GB | Requires PostgreSQL | Vertical |
| Vault (dedicated hosts, ADR-0016) | 2 / 4 GB / 100 GB | 4 / 8 GB / 200 GB | Active/Passive with Consul/etcd backend | Vertical |
| cert-manager | 1 / 2 GB / 50 GB | 2 / 4 GB / 100 GB | Deployment, not HA by default | Vertical |
| Prometheus | 2 / 4 GB / 200 GB | 4 / 8 GB / 500 GB | Single TSDB (Lab); remote write for HA | Vertical |
| Grafana | 1 / 2 GB / 50 GB | 2 / 4 GB / 100 GB | Single | Vertical |
| Alertmanager | 1 / 2 GB / 50 GB | 2 / 4 GB / 100 GB | Single | Vertical |
| Thanos | 1 / 2 GB / 100 GB | 2 / 4 GB / 200 GB | Object storage for long-term | Vertical |
| Loki | 1 / 2 GB / 200 GB | 2 / 4 GB / 500 GB | Single | Vertical |
| Fluent Bit | 0.5 / 1 GB / 20 GB | 1 / 2 GB / 50 GB | DaemonSet per node | Horizontal with nodes |
| Nexus | 2 / 4 GB / 200 GB | 4 / 8 GB / 500 GB | Single | Vertical |
| Harbor | 4 / 8 GB / 300 GB | 8 / 16 GB / 500 GB | Requires PostgreSQL, Redis | Vertical |
| HAProxy/Nginx + Keepalived | 1 / 2 GB / 50 GB | 2 / 4 GB / 100 GB | Active/Passive VIP | Horizontal (2 LB servers) |

## 6. Ceph / storage sizing
| Role | Min | Recommended | Expanded | Notes |
|---|---|---|---|---|
| Ceph MON | 1 / 2 GB / 50 GB ×3 | 2 / 4 GB / 100 GB ×3 | 2 / 8 GB / 200 GB ×5 | Odd number, quorum |
| Ceph MGR | 1 / 2 GB / 50 GB ×2 | 2 / 4 GB / 100 GB ×2 | 2 / 4 GB / 200 GB ×2 | Active/standby |
| Ceph OSD | 2 / 4 GB / 1 TB (disk) | 4 / 8 GB / 2 TB (disk) ×3+ | 8 / 16 GB / 4 TB ×5+ | Raw/passthrough disk; replica 3 |
| Rook OSD worker | 4 / 8 GB / 200 GB | 8 / 16 GB / 500 GB | 16 / 32 GB / 1 TB | Dedicated storage worker |

Usable vs raw capacity: with replica 3, usable ≈ raw/3. With erasure coding, usable ≈ raw×(k/(k+m)). Always plan for ~30% headroom for recovery/backfill.

## 7. Lab profiles
### Small Lab profile (functional testing only)
- Management cluster: 3 control-plane nodes (2 vCPU/4 GB each)
- Workload cluster: 3 control-plane nodes (2 vCPU/4 GB each) + 2 workers (2 vCPU/4 GB each)
- No Ceph/Rook; storage via local-path or hostPath (test-only, not production-grade)
- Rancher, Argo CD, Keycloak, Vault, Prometheus/Grafana/Alertmanager in management cluster
- Total estimate: ~10 nodes, ~40 vCPU, ~80 GB RAM

### Recommended Lab profile (HA testing)
- Management cluster: 3 control-plane nodes (4 vCPU/8 GB each)
- Workload cluster: 3 control-plane nodes (4 vCPU/8 GB each) + 3 workers (4 vCPU/8 GB each)
- Ceph: 3 MON + 2 MGR + 3 OSD (dedicated storage workers or Rook on storage workers)
- Full observability + security stack
- Total estimate: ~14-16 nodes, ~80-100 vCPU, ~160-200 GB RAM

### Expanded HA Lab profile (production-oriented)
- Management cluster: 5 control-plane nodes (8 vCPU/16 GB each)
- Two workload clusters: 3 control-plane nodes each + 5 workers each
- Ceph: 5 MON + 2 MGR + 5+ OSD
- HA load balancers (2 servers, Active/Passive VIP)
- Total estimate: ~25+ nodes, ~200+ vCPU, ~400+ GB RAM

## 8. Resource contention and headroom
- Reserve ~20% CPU and RAM on every host for kubelet, Cilium, OS, and eviction thresholds.
- Ceph recovery/backfill: reserve network bandwidth and CPU on OSD nodes during rebalance.
- Image/package cache growth: allocate disk headroom for Nexus/Harbor retention.
- Monitoring retention: Prometheus/Loki disk grows with retention period; cap and rotate.
- Do not overcommit etcd or control-plane nodes.

## 9. Validation required
Before implementation, confirm:
- Actual host CPU/RAM/disk against profile requirements (Section 2 of `lab/infrastructure-inventory-template.md`).
- That the sum of all components fits the available pool with headroom.
- That Ceph OSD disks are raw/passthrough if Ceph or Rook-Ceph is included.
