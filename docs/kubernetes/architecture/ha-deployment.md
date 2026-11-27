# Kubernetes HA Deployment Architecture

## A. Purpose and scope

Document the high-availability Kubernetes deployment architecture for production platforms: multi-control-plane setup, etcd quorum, API server load balancing, worker node patterns, and HA validation procedures.

Cross-references: `kubernetes/control-plane/ha-topology.md`, `architecture/03-failure-domains.md`, `infrastructure-provisioning-docs/terraform-iks.md`, and `site/cluster-status.md`.

## B. Control plane HA design

### B.1. Multi-control-plane setup

| Configuration | Control-plane nodes | etcd placement | Failure tolerance | Recommended use |
|---------------|--------------------|----------------|-------------------|-----------------|
| 3-node | 3 | Stacked on each CP node | 1 node | Development, small production |
| 5-node | 5 | Stacked on each CP node | 2 nodes | Reference production topology |

Both configurations use **stacked etcd** — etcd members run on the same nodes as kube-apiserver. This is the Kubespray default and the simplest operational model.

**Rule:** A node in the `[control-plane]` inventory group with stacked etcd must also be listed in the `[etcd]` group. Never list a host in both `[control-plane]` and `[k8s-node]`.

### B.2. Node placement and failure domains

Control-plane nodes must be spread across independent failure domains:

- **3-node**: 3 separate failure domains (e.g., 3 availability zones, 3 racks, or 3 physical sites)
- **5-node**: 5 separate failure domains, or 3 zones with 2+2+1 distribution

Control-plane nodes **must not** run application workloads. Taints are applied to prevent scheduling, and a `NoSchedule` taint is enforced via admission controller.

### B.3. etcd quorum and failure scenarios

|| Failure | Effect | etcd quorum | Recovery |
|---|---|---|---|---|
| 1 CP node lost (3-node) | API available through remaining 2 members | Intact (2/3) | Rebuild node, rejoin with `cluster.yml --limit <host>` |
| 1 CP node lost (5-node) | API available through remaining 4 members | Intact (4/5) | Rebuild node, rejoin with `cluster.yml --limit <host>` |
| 2 CP nodes lost (3-node) | etcd loses quorum, all API writes stop | Lost (1/3) | Restore quorum from etcd snapshot |
| 2 CP nodes lost (5-node) | etcd quorum intact at 3 members | Intact (3/5) | Rebuild nodes one at a time |
| Slow etcd disk | API latency rises, leader elections flap | Intact | Replace disk; etcd is not tunable around bad hardware |

**Never restart all control-plane nodes simultaneously** — this removes API server quorum and makes the cluster unreachable.

## C. API server load balancing

### C.1. Front-end load balancer

API server access is fronted by a load balancer (MetalLB, HAProxy, or cloud external LB) in the management subnet:

```text
                    +-------------------+
                    | External LB /     |
                    | MetalLB speaker   |
                    | (VIP: 10.20.0.10) |
                    +-------------------+
                              |
        +---------------------+---------------------+
        |                     |                     |
+-------+-----------------+---------+   +-------+-----------+--------+--------+
| CP node 1 |         CP node 2      |   | CP node 3 |       CP node 4  | CP node 5 |
| kube-apiserver |            |  | kube-apiserver |  | kube-apiserver | kube-apiserver |
| stacked etcd  |            |  | stacked etcd  |  | stacked etcd  | stacked etcd  |
+-----------+--------------+  +-----------+  +-------+-----------+--------+--------+
```

The load balancer health-checks the API server port (6443/TCP) on each control-plane node and removes failed nodes from the pool.

### C.2. Load balancer configuration

- **Protocol**: TCP port 6443 for API server, TCP port 2379-2380 for etcd peer communication (if exposed)
- **Health check**: TCP connect to 6443, optionally `/readyz` endpoint
- **Session persistence**: None required (API server is stateless between requests)
- **Algorithm**: Round-robin or least-connections
- **Timeouts**: Health check timeout 10s, connection drain 30s

### C.3. DNS and VIP

- Virtual IP (VIP) configured on the load balancer
- DNS `kubernetes.<cluster-name>.<namespace>.svc.cluster.local` → VIP
- Split-horizon DNS for internal/external access
- TLS termination at the load balancer; re-encrypt to API server

## D. Worker node patterns

### D.1. Node categories

| Node type | Purpose | Taints | Autoscaling |
|-----------|---------|--------|-------------|
| General workers | Application workloads | None | HPA, KHA |
| GPU workers | AI/ML workloads | `nvidia.com/gpu` role | Device plugin + HPA |
| Infrastructure workers | Platform add-ons, no app pods | `node-role.kubernetes.io/infra:NoSchedule` | Manual |
| Edge workers | Perimeter workloads | `node-role.kubernetes.io/edge:NoSchedule` | Manual |

### D.2. Node taint topology

```yaml
# Control-plane taint (prevents workload scheduling)
apiVersion: v1
kind: Node
metadata:
  name: k8s-cp-1
spec:
  taints:
  - key: "CriticalAddonsOnly"
    effect: "NoSchedule"
```

### D.3. Worker node sizing

- Minimum 2 worker nodes per availability zone
- Node labels for topology spread constraints
- `kubernetes.io/hostname` and `beta.kubernetes.io/arch` labels set automatically

## E. HA validation procedures

### E.1. Pre-deployment validation

```bash
# Verify control-plane node connectivity
kubectl get nodes -l node-role.kubernetes.io/control-plane

# Verify etcd cluster health
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster

# Verify etcd member list matches inventory
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  member list

# Verify API server readiness
kubectl get --raw='/readyz?verbose'

# Verify load balancer health
<check-lb-health.sh>
```

### E.2. Post-deployment validation

```bash
# All control-plane nodes Ready and Ready status
kubectl get nodes -l node-role.kubernetes.io/control-plane -o wide

# All control-plane pods running
kubectl -n kube-system get pods -l tier=control-plane

# API server availability through LB
curl -s -o /dev/null -w "%{http_code}" https://<VIP>:6443/readyz

# etcd quorum verification
etcdctl member list \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  -w table

# Pod scheduling on control-plane nodes (should be zero)
kubectl get nodes -l node-role.kubernetes.io/control-plane -o jsonpath='{.items[*].spec.unschedulable}'

# Network policy connectivity test
kubectl run test-net --rm -i --restart=Never --image=busybox -- /bin/sh -c "curl -s http://<service>:<port>"
```

### E.3. HA failure scenario testing

| Scenario | Expected outcome | Validation |
|----------|-----------------|------------|
| 1 CP node power loss | API continues through remaining nodes | `kubectl get nodes` shows 2/3 or 4/5 CP nodes Ready |
| 1 CP node network partition | API failover to healthy nodes | Load balancer removes partitioned node |
| etcd member loss (1 of 3) | Cluster continues with reduced quorum | `etcdctl member list` shows remaining members healthy |
| etcd member loss (2 of 5) | Cluster continues with 3/5 quorum | `etcdctl endpoint health` all healthy |
| Load balancer node failure | API failover to remaining CP nodes | `curl` to VIP returns 200 from remaining node |

### E.4. Upgrade validation order

1. Upgrade one control-plane node with `cluster.yml --limit <host>`
2. Verify node is Ready and etcd member is healthy
3. Verify API server availability through load balancer
4. Repeat for remaining control-plane nodes
5. Verify worker nodes still schedule pods
6. Run full HA validation suite (Section E.2)

## F. Cross-references

- `kubernetes/control-plane/ha-topology.md` — Detailed control-plane HA topology, etcd quorum, certificate lifecycle
- `architecture/03-failure-domains.md` — Failure domain design and anti-circularity rules
- `infrastructure-provisioning-docs/terraform-iks.md` — Terraform provisioning for IBM Cloud Kubernetes Service
- `site/cluster-status.md` — Real-time cluster status dashboard
- `network-matrix/network-communication-matrix.md` — API server port restrictions and network policies
- `lifecycle/upgrades/upgrade-procedures.md` — Control plane and worker upgrade procedures