# Failure Scenario Tests

## Node Failure

**Description**: A worker or control-plane node becomes unavailable (hardware failure, power loss, etc.).

| Aspect | Details |
|--------|---------|
| Impact | Workloads rescheduled to remaining nodes; API remains available if control-plane node |
| Detection | Node Not Ready status, kubelet heartbeats stop |
| Recovery | Replace node, rejoin cluster; drain pods before failure if possible |

Cross-reference: [`../kubernetes/control-plane/ha-topology.md`](../kubernetes/control-plane/ha-topology.md) | [`../architecture/03-failure-domains.md`](../architecture/03-failure-domains.md)

---

## Network Partition

**Description**: Network connectivity between cluster components is interrupted (partitioned network, VPC issues, routing failure).

| Aspect | Details |
|--------|---------|
| Impact | Control plane cannot communicate with etcd/workers; API requests time out; workloads lose external connectivity |
| Detection | etcd leader flapping, API server response degradation, ping loss between nodes |
| Recovery | Restore network path; if partition persists, apply quorum-based recovery for etcd |

Cross-reference: [`../network-matrix/network-communication-matrix.md`](../network-matrix/network-communication-matrix.md) | [`../kubernetes/control-plane/ha-topology.md`](../kubernetes/control-plane/ha-topology.md)

---

## etcd Quorum Loss

**Description**: etcd cluster loses majority (odd number of members lost), stopping all API writes while read-only workloads continue running.

| Aspect | Details |
|--------|---------|
| Impact | All `kubectl` write operations fail; etcd keys inaccessible; running pods continue from local state |
| Detection | etcd member goes `unhealthy`, API server 5xx errors, `etcdctl` quorum alerts |
| Recovery | Restore from last snapshot; add new etcd member; avoid restarting all members simultaneously |

Cross-reference: [`../kubernetes/control-plane/etcd-restore.md`](../kubernetes/control-plane/etcd-restore.md) | [`../kubernetes/control-plane/index.md`](../kubernetes/control-plane/index.md#failure-scenarios) | [`../lifecycle/disaster-recovery/index.md`](../lifecycle/disaster-recovery/index.md#scenario-index)

---

## Control Plane Failure

**Description**: Control-plane components (API server, controller manager, scheduler) become unavailable (certificate expiry, configuration drift, etcd sync loss).

| Aspect | Details |
|--------|---------|
| Impact | API server unreachable; no new workloads can be scheduled; existing workloads continue if etcd is healthy |
| Detection | `kubectl` authentication failure, API server health check failure, controller manager leader election logs |
| Recovery | Restart control-plane nodes one at a time; restore etcd quorum; rotate certificates if needed |

Cross-reference: [`../kubernetes/control-plane/index.md`](../kubernetes/control-plane/index.md) | [`../lifecycle/upgrades/upgrade-procedures.md`](../lifecycle/upgrades/upgrade-procedures.md) | [`../architecture/03-failure-domains.md`](../architecture/03-failure-domains.md)

---

## Anti-circularity Rules

1. etcd must not depend on the control plane API for snapshot restore operations (offline `etcdctl` restore).
2. Control plane must not depend on application workload availability for API server health.
3. Network partition recovery must not assume immediate etcd quorum — use staged member re-add.
4. Node replacement must not require API server write access during the join process.

[Previous step](#) | [Next step](#)
