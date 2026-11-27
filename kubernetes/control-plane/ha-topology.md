# HA Control Plane Topology

## A. Purpose and scope

Document the high-availability control plane topology for the platform: 3 or 5 control-plane nodes, stacked etcd, failure domain distribution, VIP/load balancing, and node loss recovery.

Cross-references `kubernetes/control-plane/index.md`, `architecture/03-failure-domains.md`, `kubespray/kubespray-deployment.md`, and `network-matrix/network-communication-matrix.md`.

## B. Topology options

| Option | Control-plane nodes | etcd placement | Failure tolerance | Use case |
|--------|--------------------|----------------|-------------------|----------|
| 3-node | 3 | Stacked on each CP node | 1 node | First environment, development/staging |
| 5-node | 5 | Stacked on each CP node | 2 nodes | Reference production topology |

Both options use stacked etcd — etcd members run on the same nodes as the control plane components. This is the Kubespray default and the simplest operational model.

## C. Node placement and failure domains

Control-plane nodes must be spread across failure domains:

- **3-node**: 3 separate failure domains (e.g., 3 availability zones or 3 racks)
- **5-node**: 5 separate failure domains, or 3 zones with 2+2+1 distribution

Control-plane nodes are **not workers** — no application pods are scheduled on them. Taints are applied to prevent workload scheduling.

## D. Load balancing and VIP

API server access is fronted by a load balancer (MetalLB or external LB) in the management subnet:

```
                    +-------------------+
                    |  External LB /    |
                    |  MetalLB speaker  |
                    |  (VIP: 10.20.0.10)|
                    +-------------------+
                             |
        +--------------------+--------------------+
        |                    |                    |
   +----+----+         +----+----+         +----+----+
   | CP node 1 |       | CP node 2 |       | CP node 3 |
   | kube-apiserver |  | kube-apiserver |  | kube-apiserver |
   | stacked etcd  |  | stacked etcd  |  | stacked etcd  |
   +----+----+         +----+----+         +----+----+
```

The load balancer health-checks the API server port (6443/TCP) on each control-plane node and removes failed nodes from the pool.

## E. Inventory grouping

Kubespray inventory for stacked etcd:

```ini
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11 ip=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12 ip=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13 ip=10.20.0.13

[etcd]
k8s-cp-1
k8s-cp-2
k8s-cp-3

[k8s-cluster:children]
control-plane
etcd
```

**Rule:** A node in `[control-plane]` with stacked etcd must also be in `[etcd]`. Never list a host in two `k8s-node` groups.

## F. etcd quorum and failure scenarios

| Failure | Effect | etcd quorum | Recovery |
|---------|--------|-------------|----------|
| 1 CP node lost (3-node) | API available through remaining 2 members | Intact (2/3) | Rebuild node, rejoin with `cluster.yml --limit <host>` |
| 1 CP node lost (5-node) | API available through remaining 4 members | Intact (4/5) | Rebuild node, rejoin with `cluster.yml --limit <host>` |
| 2 CP nodes lost (3-node) | etcd loses quorum, all API writes stop | Lost (1/3) | Restore quorum from etcd snapshot |
| 2 CP nodes lost (5-node) | etcd quorum intact at 3 members | Intact (3/5) | Rebuild nodes one at a time |
| Slow etcd disk | API latency rises, leader elections flap | Intact | Replace disk; etcd is not tunable around bad hardware |

**Never restart all control-plane nodes simultaneously** — this removes API server quorum and makes the cluster unreachable.

## G. Certificate lifecycle

Kubernetes internal PKI (API server, kubelet, front-proxy, etcd certificates) is managed by Kubespray, not cert-manager:

- Certificates are renewed by Kubespray's `cluster.yml` certificate renewal workflow
- cert-manager issues ingress and service certificates only (`secrets-management/pki/index.md`)
- OIDC integration requires `kube_oidc_ca_file` (CA that signed Keycloak TLS cert) on every control-plane node (`kubespray/kubespray-deployment.md` Section L)

Certificate expiry causes API server or kubelet TLS failure. Renew via `cluster.yml` before expiry.

## H. Validation

```bash
# Control-plane nodes are Ready
kubectl get nodes -l node-role.kubernetes.io/control-plane

# Control-plane pods running
kubectl -n kube-system get pods -l tier=control-plane

# etcd cluster healthy
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster

# etcd members all present
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  member list

# API server readiness
kubectl get --raw='/readyz?verbose'
```

All etcd members must report `healthy`. A member list shorter than the inventory means a member was lost and must be replaced before the next failure.

## I. Upgrade order

Control plane first, one node at a time:

1. Upgrade one control-plane node with `cluster.yml --limit <host>`
2. Verify node is Ready and etcd member is healthy
3. Repeat for the next control-plane node
4. Then upgrade worker nodes

Kubernetes supports only one minor version skew in each direction — do not skip minors.

## J. Cross-references

- `kubernetes/control-plane/index.md` — Control plane decisions and operational boundaries
- `architecture/03-failure-domains.md` — Failure domain design
- `kubespray/kubespray-deployment.md` — Kubespray deployment, group vars, OIDC CA
- `compatibility/version-matrix.md` — Version pins (K8s v1.36.5 default, v1.34.0 minimum)
- `network-matrix/network-communication-matrix.md` — API server port restrictions
- `lifecycle/upgrades/upgrade-procedures.md` — Upgrade procedures
