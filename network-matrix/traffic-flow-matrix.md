# Traffic Flow Matrix

## A. Purpose and scope

Create traffic flow matrix: north-south, east-west, control-plane to nodes, monitoring scrape targets.

Cross-references `network-matrix/network-communication-matrix.md`, `network-matrix/port-requirements.md`.

## B. North-south traffic (external to cluster)

| Source | Destination | Port | Protocol | Purpose |
|--------|-------------|------|----------|---------|
| External users | Ingress LB | 80 | HTTP | Web traffic |
| External users | Ingress LB | 443 | HTTPS | Secure web traffic |
| API clients | API server LB | 6443 | TCP | Kubernetes API |
| Administrators | SSH bastion | 22 | TCP | Administrative access |
| Operators | Rancher UI | 443 | HTTPS | Cluster management |

## C. East-west traffic (pod to pod)

| Source | Destination | Port | Protocol | Purpose |
|--------|-------------|------|----------|---------|
| Application pod | Application pod | 8080 | TCP | Application communication |
| Application pod | Database | 5432 | TCP | Database access |
| Application pod | Redis | 6379 | TCP | Cache access |
| Application pod | Vault | 8200 | TCP | Secret retrieval |
| Application pod | Prometheus | 9090 | TCP | Metrics scrape |

## D. Control-plane to nodes

| Source | Destination | Port | Protocol | Purpose |
|--------|-------------|------|----------|---------|
| API server | Kubelet | 10250 | TCP | Node metrics and exec |
| API server | etcd | 2379 | TCP | etcd client |
| API server | etcd | 2380 | TCP | etcd peer |
| Scheduler | API server | 6443 | TCP | Scheduling decisions |
| Controller manager | API server | 6443 | TCP | Controller operations |
| Kube-proxy | API server | 6443 | TCP | Service endpoints |

## E. Monitoring scrape targets

| Source | Destination | Port | Protocol | Purpose |
|--------|-------------|------|----------|---------|
| Prometheus | Node exporter | 9100 | TCP | Node metrics |
| Prometheus | Kubelet | 10250 | TCP | kubelet metrics |
| Prometheus | cAdvisor | 4194 | TCP | Container metrics |
| Prometheus | etcd | 2381 | TCP | etcd metrics |
| Prometheus | API server | 6443 | TCP | API server metrics |
| Prometheus | Cilium | 9091 | TCP | CNI metrics |
| Prometheus | Ceph exporter | 9283 | TCP | Ceph metrics |

## F. Cross-references

- `network-matrix/network-communication-matrix.md` — Network communication matrix
- `network-matrix/port-requirements.md` — Port requirements
