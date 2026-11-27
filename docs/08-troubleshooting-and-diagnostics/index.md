# 08 · Troubleshooting and Diagnostics

## Purpose and scope
Comprehensive troubleshooting handbook organized by infrastructure component and failure category. Every procedure follows: symptoms, possible causes, diagnostic commands, expected output, investigation procedure, resolution, verification, prevention.

## Subsections
| Subsection | Covers |
|---|---|
| [Operating systems](08-operating-systems.md) | OS install, kernel, firewall, SSH, NTP, DNS |
| [DNS and NTP](08-dns-and-ntp.md) | CoreDNS, chrony, resolution, clock skew |
| [Network and firewall](08-network-and-firewall.md) | Segments, ports, VIP failover, load balancer |
| [Load balancers](08-load-balancers.md) | HAProxy, Nginx, Keepalived, MetalLB, F5 NIC |
| [Kubernetes](08-kubernetes.md) | Control plane, nodes, etcd, API server |
| [CNI](08-cni.md) | Cilium, kube-proxy replacement, connectivity |
| [CSI](08-csi.md) | Ceph CSI, PVC binding, snapshots |
| [Rancher](08-rancher.md) | Management cluster, cluster registration |
| [Argo CD](08-argocd.md) | GitOps, sync, ApplicationSet, drift |
| [Ceph](08-ceph.md) | MON/MGR/OSD/MDS/RGW, PG, rebalance |
| [Rook-Ceph](08-rook-ceph.md) | Operator, cluster, storage class |
| [Longhorn](08-longhorn.md) | Replica, volume, snapshot |
| [Repositories and registries](08-repositories-and-registries.md) | Harbor, Nexus, GitLab, mirroring |
| [GitLab](08-gitlab.md) | CI/CD, runners, registry, backup |
| [Monitoring and logging](08-monitoring-and-logging.md) | Prometheus, Grafana, Loki, Alertmanager |
| [Authentication and AD](08-authentication-and-ad.md) | Keycloak, OIDC, LDAP, RBAC |
| [Certificates and TLS](08-certificates-and-tls.md) | cert-manager, Vault PKI, expiry |
| [Performance](08-performance.md) | CPU, memory, disk, network, storage |
| [HA and failover](08-ha-and-failover.md) | etcd quorum, VIP failover, DR drills |

## Troubleshooting format
1. Symptoms
2. Possible causes
3. Diagnostic commands
4. Expected output
5. Investigation procedure
6. Resolution
7. Verification
8. Prevention

## Related
- [06 · Kubernetes Infrastructure](../06-kubernetes-infrastructure/index.md)
- [07 · Software-Defined Storage](../07-software-defined-storage/index.md)
- [05 · Load Balancers and Traffic Management](../05-load-balancers/index.md)
