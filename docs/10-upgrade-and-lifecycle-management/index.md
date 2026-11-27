# 10 · Upgrade and Lifecycle Management

## Purpose and scope
Document controlled upgrade procedures for every infrastructure component: OS, firmware, hypervisors, Kubernetes, Kubespray, Rancher, CNI, CSI, add-ons, Argo CD, Ceph, Rook-Ceph, storage appliances, load balancers, GitLab, Nexus, Harbor, monitoring. Includes version compatibility, upgrade order, prerequisites, backup, pre-upgrade validation, execution, post-upgrade validation, rollback strategy, downtime considerations, air-gapped upgrade procedures.

## Subsections
| Subsection | Covers |
|---|---|
| [OS, Firmware, Hypervisor](10-01-os-firmware-hypervisor.md) | OS patches, firmware, hypervisor upgrades; compatibility, backup, rollback |
| [Kubernetes & Kubespray](10-02-kubernetes-kubespray.md) | K8s and Kubespray version upgrades; upgrade order, etcd backup, one control-plane node at a time |
| [CNI, CSI, Add-ons, Argo CD](10-03-cni-csi-addons-argocd.md) | CNI/CSI/add-on/Argo CD upgrades; compatibility, rollback |
| [Ceph, Rook-Ceph, Storage Appliances](10-04-ceph-rook-storage-appliances.md) | Ceph/Rook/storage appliance upgrades; expansion, upgrade, troubleshooting |
| [Load Balancer, GitLab, Nexus, Harbor](10-05-lb-gitlab-nexus-harbor.md) | LB, GitLab, Nexus, Harbor upgrades; TLS, backup/restore |
| [Monitoring Components](10-06-monitoring-components.md) | Prometheus, Grafana, Alertmanager, Loki upgrades |
| [Compatibility, Order, Backup, Rollback](10-07-compat-order-backup-rollback.md) | Version compatibility, upgrade order, backup, pre/post validation, rollback strategy, downtime |
| [Air-Gapped Upgrade](10-08-air-gapped-upgrade.md) | Upgrade procedures for fully disconnected environments |

## Cross-references
- Every upgrade references [shared version & compatibility matrix](../shared/matrices/version-matrix/index.md) before starting
- Rollback/restore procedures in [08 · Troubleshooting](../08-troubleshooting-and-diagnostics/index.md) and [11 · Maintenance](../11-maintenance-and-operations/index.md)
- Air-gapped artifact handling in [03 · Repository & Registry Management](../03-repository-registry/index.md)
