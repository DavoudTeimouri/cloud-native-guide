# Kubernetes

## Purpose and scope
Kubernetes infrastructure: architecture, best practices, Kubespray deployment, management and application clusters, Rancher, Argo CD GitOps, CNI/CSI networking, add-ons, observability, policies, alerts, security, validation.

## Subsections
| Subsection | Covers |
|---|---|
| [Architecture](6.1-kubernetes-architecture.md) | Control plane, worker nodes, etcd, networking, storage, multi-cluster |
| [Deployment Methods](6.3-deployment-methods.md) | Kubespray, Ansible, inventory, offline deployment, version selection |
| [Management Cluster Deployment](6.4-mgmt-cluster-deployment.md) | Prerequisites, inventory, authentication modes, validation |
| [Application Cluster Deployment](6.5-app-cluster-deployment.md) | Sizing profiles, multi-cluster connectivity, registration |
| [Additional Application Clusters](6.6-additional-clusters.md) | Capacity planning, network planning, IP allocation, onboarding |
| [Kubernetes Management Platform](6.7-kubernetes-management-platform.md) | Rancher: install, HA, TLS, RBAC, cluster registration |
| [Cluster Storage Integration](6.8-cluster-storage-integration.md) | Rook-Ceph, external Ceph, CSI, StorageClasses |
| [Kubernetes Networking](6.9-kubernetes-networking.md) | CNI, Calico, pod/service CIDR, network policies, ingress |
| [CSI and Storage Integration](6.10-csi-and-storage-integration.md) | CSI architecture, StorageClasses, PVCs, snapshots |
| [Kubernetes Add-ons](6.11-kubernetes-add-ons.md) | MetalLB, Gatekeeper, Falco, cert-manager, ingress controllers |
| [GitOps & Application Delivery](6.12-gitops-and-application-delivery.md) | Argo CD: install, RBAC, ApplicationSets, GitOps workflows |
| [Monitoring & Logging](6.13-monitoring-and-logging.md) | Prometheus, Grafana, Loki, Alertmanager, remote write |
| [Alert Management](6.14-alert-management.md) | Alert rules, severity, routing, escalation, testing |
| [Deployment Governance & Auditing](6.15-deployment-governance-and-auditing.md) | Admission policies, Gatekeeper, policy-as-code, audit logging |
| [Security & Identity](6.16-security-and-identity.md) | AD, LDAP, OIDC, RBAC, service accounts, secrets, certificates |
| [Validation & Acceptance Testing](6.17-validation-and-acceptance-testing.md) | HA, node failure, network, storage, DNS, ingress, backup/restore |

## Cross-references
- [Overview (1.2 Reference Architectures)](../01-overview-and-architecture/1.2-reference-architectures.md)
- [Load Balancers (5.1 Architecture)](../05-load-balancers/5.1-architecture.md)
- [SDS (7.1 Architecture)](../07-software-defined-storage/7.1-architecture.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
