# Shared · Version & Compatibility Matrix

## Purpose and scope
Every pinned version with source URL and check date. Authoritative single source for version compatibility across the guide.

## Component versions
| Component | Version | Source URL | Check date | Notes |
|---|---|---|---|---|
| Kubernetes | 1.29.x | https://kubernetes.io | — | Pin exact patch in inventory |
| Kubespray | 2.32.0 | https://github.com/kubernetes-sigs/kubespray | — | Uses kube_oidc_* vars |
| Ceph | Quincy/Reef | https://ceph.io | — | Quincy EOL; prefer Reef |
| Rook-Ceph | 1.13+ | https://rook.io | — | Match Ceph version |
| Rancher | 2.9+ | https://rancher.io | — | Management platform |
| Argo CD | 2.10+ | https://argo-cd.io | — | GitOps |
| Prometheus | 2.50+ | https://prometheus.io | — | Monitoring |
| Grafana | 11+ | https://grafana.com | — | Dashboards |

## Usage
Check this matrix before any upgrade or new deployment. Record check date; re-verify quarterly.

## Related
- [10 · Upgrade & Lifecycle (10-07 Compatibility, Order, Backup, Rollback)](../../../10-upgrade-and-lifecycle-management/10-07-compat-order-backup-rollback.md)
- [11 · Maintenance & Operations (11-quarterly-capacity-review)](../../../11-maintenance-and-operations/11-quarterly-capacity-review.md)
