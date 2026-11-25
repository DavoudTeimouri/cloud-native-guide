# Infrastructure Inventory Template and Assumption Register (TASK 006)

## 1. Purpose
Capture what is known and what remains unknown about the Lab infrastructure. Use explicit placeholders for missing information. Do not invent hardware specifications, IP addresses, VLAN IDs, or available capacity.

This template is designed to be filled in by the infrastructure owner and confirmed by the user before implementation begins.

## 2. Physical server inventory
| Field | Value (placeholder) | Source | Confidence | Blocks implementation? |
|---|---|---|---|---|
| Server make/model | `<SERVER_MODEL>` | — | — | Yes |
| CPU model | `<CPU_MODEL>` | — | — | Yes |
| Total CPU cores per host | `<CPU_CORES>` | — | — | Yes |
| RAM per host | `<RAM_GB>` | — | — | Yes |
| Local disk (boot) | `<BOOT_DISK>` | — | — | Yes |
| Local disk (data/SSD/NVMe) | `<DATA_DISK>` | — | — | Yes (Ceph OSD DB/WAL, etcd) |
| NIC count | `<NIC_COUNT>` | — | — | Yes |
| NIC speed | `<NIC_Gbps>` | — | — | Yes |
| IPMI/BMC present | `<YES/NO>` | — | — | Yes |
| Rack location | `<RACK>` | — | — | No |
| Power feed | `<PDU/CIRCUIT>` | — | — | No |

## 3. Hypervisor and virtualization capacity
| Field | Value (placeholder) | Source | Confidence | Blocks implementation? |
|---|---|---|---|---|
| Hypervisor type | `<KVM/VMware/oVirt/other>` | — | — | Yes |
| Hypervisor host count | `<HOST_COUNT>` | — | — | Yes |
| Allocatable vCPUs | `<VCPU_TOTAL>` | — | — | Yes |
| Allocatable RAM | `<RAM_TOTAL_GB>` | — | — | Yes |
| Allocatable storage | `<STORAGE_TOTAL_GB>` | — | — | Yes |
| Storage type (local/shared) | `<LOCAL/SHARED>` | — | — | Yes (Ceph requires raw/passthrough disks) |
| GPU availability | `<YES/NO + model>` | — | — | No (optional future extension) |

## 4. Network and addressing
| Field | Value (placeholder) | Source | Confidence | Blocks implementation? |
|---|---|---|---|---|
| Management subnet | `<MGMT_SUBNET>` | — | — | Yes |
| K8s node subnet | `<K8S_NODE_SUBNET>` | — | — | Yes |
| Pod CIDR | `<POD_CIDR>` | — | — | Yes |
| Service CIDR | `<SERVICE_CIDR>` | — | — | Yes |
| Ceph public subnet | `<CEPH_PUBLIC_SUBNET>` | — | — | Yes |
| Ceph cluster subnet | `<CEPH_CLUSTER_SUBNET>` | — | — | Yes |
| LB VIP | `<LB_VIP>` | — | — | Yes |
| VLAN IDs | `<VLAN_IDS>` | — | — | Yes |
| DNS service | `<DNS_INTERNAL>` | — | — | Yes |
| NTP service | `<NTP_INTERNAL>` | — | — | Yes |
| Internet egress | `<DIRECT/PROXY/RESTRICTED>` | — | — | Yes |

## 5. Existing infrastructure classification
| Resource | Category | Notes |
|---|---|---|
| Production Kubernetes clusters | Existing production infrastructure | Not available for Lab |
| Production Ceph cluster | Existing production infrastructure | Not available for Lab |
| Virtualized Ceph (elsewhere) | Existing virtualized Ceph | Confirm allocatable capacity before reuse |
| Spare hypervisor hosts | Available but unconfirmed | Verify before counting as Lab capacity |
| Unallocated VLANs | Available but unconfirmed | Confirm with network team |

## 6. Assumption register
| # | Assumption | Source | Confidence | Impact if incorrect | Validation required | Blocks implementation? |
|---|---|---|---|---|---|---|
| A1 | `<SERVER_MODEL>` hosts with `<CPU_CORES>` cores and `<RAM_GB>` RAM are available | User to confirm | Low | Sizing invalid; cannot fit management + workload clusters | Physical/hypervisor inventory walk-through | Yes |
| A2 | `<MGMT_SUBNET>`, `<K8S_NODE_SUBNET>`, `<POD_CIDR>`, `<SERVICE_CIDR>` do not overlap | User to confirm | Low | Network misconfiguration; cluster creation fails | CIDR overlap check against existing network | Yes |
| A3 | Ceph OSD disks can be raw or SCSI-passthrough on the hypervisor | User to confirm | Medium | Rook-Ceph/Ceph deployment fails | Hypervisor storage passthrough test | Yes (if using Ceph/Rook) |
| A4 | Internal DNS/NTP are reachable from the Lab segment | User to confirm | High | Node bootstrap fails (K8s certs, etcd) | DNS/NTP reachability test | Yes |
| A5 | Controlled internet egress exists via a proxy/upstream host | User to confirm | High | Image/package mirroring impossible | Egress connectivity test | Yes |
| A6 | Three-control-plane-node quorum is acceptable for the Lab | P11.8 traceability | Medium | Reduced failure tolerance vs five nodes | User confirmation | No |

## 7. Instructions
1. Fill every `<PLACEHOLDER>` above with real values from the infrastructure owner.
2. Mark Confidence as High/Medium/Low based on evidence.
3. Resolve every "Blocks implementation? = Yes" item before the Lab deployment sequence begins.
4. Return the completed register to the user for sign-off. No deployment occurs without sign-off.
