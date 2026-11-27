# SDS

## Purpose and scope
Software-Defined Storage: architecture, platform selection, independent Ceph, Rook-Ceph, other SDS solutions, monitoring, maintenance, data protection.

## Subsections
| Subsection | Covers |
|---|---|
| [Architecture](7.1-architecture.md) | Block, file, object, distributed storage, failure domains, capacity planning |
| [Best Practices](7.2-best-practices.md) | MON/OSD guidelines, CRUSH rules, PG count, capacity headroom |
| [Storage Platform Selection](7.3-storage-platform-selection.md) | Ceph, Rook-Ceph, Longhorn, hardware appliances selection matrix |
| [Independent Ceph Deployment](7.4-independent-ceph.md) | Hardware prep, OS prep, MON/MGR/OSD/MDS/RGW, CRUSH maps, pools |
| [Other SDS Solutions](7.5-other-sds-solutions.md) | Equivalent docs for alternative SDS platforms |
| [Monitoring & Logging](7.6-monitoring-and-logging.md) | Ceph health, OSD, MON quorum, capacity, Prometheus/Grafana |
| [Maintenance & Data Protection](7.7-maintenance-and-data-protection.md) | Backup, recovery, disk replacement, rebalancing, expansion, DR |

## Cross-references
- [Kubernetes (6.8 Cluster Storage Integration)](../06-kubernetes-infrastructure/6.8-cluster-storage-integration.md)
- [Kubernetes (6.10 CSI and Storage Integration)](../06-kubernetes-infrastructure/6.10-csi-and-storage-integration.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
