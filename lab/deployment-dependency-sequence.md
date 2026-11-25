# Deployment Dependency Sequence (TASK 006)

## 1. Purpose
Ordered, dependency-aware implementation sequence for the Lab. Review critically — some services may move earlier or later depending on bootstrap dependencies. This is a plan only; do not execute.

## 2. Implementation sequence
| # | Stage | Depends on | Notes |
|---|---|---|---|
| 1 | Infrastructure and resource readiness | Inventory confirmation (user sign-off) | Confirm servers, hypervisor, VLANs, IP subnets, DNS, NTP, egress policy |
| 2 | Hypervisor or physical host preparation | Stage 1 | Install/configure hypervisor, BMC/IPMI, RAID, storage passthrough for Ceph OSD |
| 3 | Network, VLAN, DNS, NTP | Stage 2 | Create VLANs, assign `<MGMT_SUBNET>`, `<K8S_NODE_SUBNET>`, confirm DNS/NTP reachability |
| 4 | OS installation and prerequisites | Stage 3 | Kubespray OS baseline: kernel, containerd, swap disabled, firewall, SELinux |
| 5 | Internal repository bootstrap | Stage 4 | Local bootstrap registry → Nexus → Harbor (see `lab/repository-registry-bootstrap.md`) |
| 6 | External load balancer and API endpoint | Stage 3 | Keepalived VIP (`<LB_VIP>`), HAProxy/Nginx, health checks |
| 7 | Kubernetes control-plane bootstrap | Stages 4, 5, 6 | Kubespray `kubeadm init`; etcd quorum; API server health |
| 8 | CNI installation and network validation | Stage 7 | Cilium (or Calico); pod-to-pod connectivity; network policy |
| 9 | Storage deployment and CSI validation | Stages 7, 8 | Ceph/Rook-Ceph; OSD devices available; CSI provisioning |
| 10 | Rancher and management services | Stage 7 | Rancher server, Argo CD, Keycloak, cert-manager |
| 11 | Observability | Stages 7, 8 | Prometheus, Grafana, Alertmanager (local TSDB first) |
| 12 | Identity and secrets | Stages 7, 9 | Vault (dedicated hosts), Keycloak, OIDC configuration |
| 13 | Registry and artifact integration | Stages 5, 12 | containerd → Harbor; package managers → Nexus |
| 14 | GitOps | Stages 7, 10, 12 | Argo CD apps, GitLab repo mirror, sync |
| 15 | Security policy enforcement | Stages 7, 8, 14 | Gatekeeper/Kyverno, PSS restricted, Falco, Trivy, Cosign |
| 16 | Backup and recovery tests | Stages 1-9 | etcd snapshot, Velero restore test on disposable cluster |
| 17 | P11.7 end-to-end acceptance tests | Stages 1-15 | Full platform acceptance per `testing/` |

## 3. Critical dependency notes
- **Stage 5 before Stage 7**: control-plane images must come from the internal/bootstrap registry. Nodes have no direct public Internet.
- **Stage 8 before Stage 9**: storage (Ceph/Rook CSI) needs CNI for pod networking.
- **Stage 7 before Stages 10-15**: all management services depend on a healthy K8s API and etcd.
- **Stage 12 (Vault/Keycloak) after Stage 9**: Vault uses integrated Raft on dedicated hosts (ADR-0016), not etcd; Keycloak uses PostgreSQL which needs storage. Vault is restored first per ADR-0025, before the Management Cluster.
- **Stage 14 (GitOps) after Stage 12**: Argo CD may need secrets from Vault for repository access.

## 4. Services that could move earlier/later
- **Observability (stage 11)**: a minimal Prometheus could run earlier to validate node bootstrapping, but full stack waits for K8s.
- **Ingress/LB (stage 6)**: the API endpoint VIP is needed early for kubectl/Rancher access; ingress controller can come later.
- **Rancher (stage 10)**: could be deferred if initial validation uses kubectl directly; Rancher is for multi-cluster management, not cluster creation.

## 5. Open questions
1. Is a bootstrap node available, or must the first node be installed from physical media?
2. Is the LoadBalancer VIP available before K8s bootstrap, or is a temporary nodeport used?
3. Does the team want to validate with kubectl first and add Rancher later?
