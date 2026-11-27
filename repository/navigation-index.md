# Repository Navigation Index

## A. Purpose and scope

Create central navigation index: all major sections, cross-references, quick links for operators.

This is the top-level index for the cloud-native-guide repository, helping operators find documents across all engineering domains.

## B. Navigation structure

| Section | Path | Description |
|---------|------|-------------|
| Architecture | architecture/ | High-level architecture and deployment topology |
| Kubernetes Platform | kubernetes/ | Control plane, nodes, networking, security |
| Kubespray | kubespray/ | Kubespray deployment, group vars, certificates |
| Rancher | management-cluster/rancher/ | Cluster management, Fleet, access management |
| Keycloak | management-cluster/keycloak/ | Identity and access management |
| Ceph Storage | storage/ceph/ | Ceph deployment, pools, monitoring |
| Rook-Ceph | storage/rook-ceph/ | Rook-Ceph operator |
| Backup & DR | lifecycle/disaster-recovery/ | Disaster recovery runbooks |
| Backup | lifecycle/backup/ | Backup architecture and procedures |
| Upgrades | lifecycle/upgrades/ | Kubernetes, Kubespray upgrade procedures |
| Networking | network-matrix/ | Network communication, ports, load balancers |
| CNI | kubernetes/networking/ | Cilium, Calico, CoreDNS, BGP |
| Offline | offline-artifacts/ | Artifact matrix, offline deployment |
| Nexus/Harbor | offline-artifacts/ | Image registry, Helm repositories |
| Automation | automation/ansible/ | Ansible playbooks, roles, inventory |
| Terraform | automation/terraform/ | Infrastructure as Code |
| Secrets | secrets-management/vault/ | Vault/OpenBao, PKI, certificates |
| Monitoring | monitoring/ | Prometheus, Grafana, Alertmanager |
| GitOps | management-cluster/argocd/ | Argo CD, Fleet, GitOps |
| Security | security/ | Pod security, audit logging, image provenance |
| Tests | tests/ | Repository validation tests |

## C. Quick links for operators

| Task | Document |
|------|----------|
| Deploy cluster | kubespray/kubespray-deployment.md |
| Upgrade Kubernetes | lifecycle/upgrades/kubernetes.md |
| Recover from disaster | lifecycle/disaster-recovery/full-site-rebuild.md |
| Rotate certificates | kubernetes/control-plane/cert-rotation.md |
| Restore etcd | kubernetes/control-plane/etcd-restore.md |
| Add worker node | kubernetes/control-plane/node-lifecycle.md |
| Deploy monitoring | monitoring/prometheus.md |
| Deploy secrets | secrets-management/vault/vault-architecture.md |
| Deploy GitOps | management-cluster/argocd/argocd.md |
| Backup etcd | kubernetes/control-plane/etcd-backup.md |

## D. Cross-references

- `architecture/00-overview.md` — Architecture overview
- `architecture/02-deployment-topology.md` — Deployment topology
- `compatibility/version-matrix.md` — Version compatibility matrix
- `catalog/catalog.json` — Document catalog
