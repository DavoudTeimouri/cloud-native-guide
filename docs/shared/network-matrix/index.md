# Shared · Network Matrix

## Purpose and scope
Centralized, maintainable network access matrix identifying source, destination, protocol, port, direction, purpose, mandatory/optional status, environment, firewall rule, and documentation reference.

## Network segments
- Management network — operational servers, management cluster control plane
- Control-plane network — Kubernetes API, etcd
- Worker network — workload node traffic, pod CIDR
- Storage network — Ceph replication, heartbeat
- Application network — ingress, North-South traffic
- DMZ — public-facing services behind reverse proxy

## Port matrix
| Source | Destination | Protocol | Port | Direction | Purpose | Mandatory | Env | Firewall rule |
|---|---|---|---|---|---|---|---|---|
| Admin workstation | Operational server | TCP | 22 | Inbound | SSH administration | Yes | All | Allow mgmt subnet |
| Operational server | All infra nodes | TCP | 22 | Outbound | SSH, Ansible | Yes | All | Allow infra subnet |
| LB (mgmt) | K8s control plane | TCP | 6443 | Inbound | Kubernetes API | Yes | All | Allow LB subnet |
| K8s node | K8s node | TCP | 2379-2380 | Inbound | etcd | Yes | Control plane | Allow control plane subnet |
| K8s node | K8s node | TCP | 10250 | Inbound | kubelet | Yes | All | Allow node subnet |
| Ceph OSD | Ceph OSD | TCP | 6800-7300 | Inbound | OSD replication | Yes | Storage | Allow storage subnet |
| Ceph MON | Ceph client | TCP | 6789 | Inbound | Monitor | Yes | Storage | Allow infra subnet |
| Ceph RGW | Client/LB | TCP | 8080 | Inbound | Object storage API | Yes | Storage | Allow infra subnet |
| LB | Registry | TCP | 443 | Inbound | HTTPS registry | Yes | All | Allow LB subnet |
| Prometheus | Targets | TCP | 9100,9090,3000 | Outbound | Scrape metrics | Yes | Monitoring | Allow infra subnet |

## Usage
Extract this table to generate ACL/firewall rules for your deployment. Individual chapters reference this matrix; document component-specific exceptions only.

## Related
- [01 · Overview (1.4 Network Architecture & Access Matrix)](../../01-overview-and-architecture/1.4-network-architecture-and-access-matrix.md)
- [05 · Load Balancers (5.1 Architecture)](../../05-load-balancers/5.1-architecture.md)
