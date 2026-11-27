# Chaos Engineering Test Plan

## Overview

This document defines chaos engineering tests to validate system resilience across pod, node, network, and data-layer failure modes. Tests are designed to be progressive, observable, and scoped by blast radius controls.

---

## Pod Failure Tests

**Description**: Terminate random or targeted pods to verify self-healing, rescheduling, and workload continuity.

| Aspect | Details |
|--------|---------|
| **Scope** | Random pod kill via `kubectl delete pod` or Chaos Mesh; targeted kill of specific deployment replicas |
| **Duration** | 5m per pod; 20m total test window |
| **Metrics** | Pod restart time, service latency, error rate spike |
| **Success Criteria** | < 30s pod restart; error budget < 5% consumption; no data loss |
| **Cross-reference** | `../kubernetes/workloads/deployment-rollouts.md` |

---

## Node Failure Tests

**Description**: Simulate node loss (power, kernel panic, network loss) to verify node drainage, pod rescheduling, and control-plane continuity.

| Aspect | Details |
|--------|---------|
| **Scope** | `kubectl drain` of a worker node (with `--ignore-daemonsets-if-unschedulable`); or kill kubelet process |
| **Duration** | Until node is fully recovered; 30m test window |
| **Metrics** | Pod reschedule time, API server availability, etcd health |
| **Success Criteria** | < 2m reschedule for non-daemonset pods; API 5xx < 1%; no data corruption |
| **Cross-reference** | `../kubernetes/control-plane/ha-topology.md` |

---

## Network Partition Tests

**Description**: induce network isolation between cluster nodes to verify partition behavior, quorum maintenance, and split-brain prevention.

| Aspect | Details |
|--------|---------|
| **Scope** | `kubectl exec` into a pod; `tc` netem latency/jitter; or use Chaos Mesh network chaos |
| **Duration** | 10m; progressive: 30s → 2m → 10m steps |
| **Metrics** | etcd leader stability, API server error rate, pod health status |
| **Success Criteria** | No etcd quorum loss; API remains available for writes on majority partition; no split-brain |
| **Cross-reference** | `../kubernetes/control-plane/etcd-restore.md` |

---

## etcd Quorum Loss Tests

**Description**: Simulate etcd member loss to verify quorum behavior, data availability, and recovery procedures.

| Aspect | Details |
|--------|---------|
| **Scope** | Stop random etcd member(s); or use `etcdctl` to remove member; or restart all members simultaneously (not recommended) |
| **Duration** | 15m total; measure from member stop to quorum restoration |
| **Metrics** | etcd member health, API write availability, snapshot latency |
| **Success Criteria** | Write availability preserved on remaining quorum; no data loss; recovery < 10m |
| **Cross-reference** | `../kubernetes/control-plane/etcd-restore.md` |

---

## Blast Radius Control

**Description**: Define and measure blast radius per test type, ensuring failures are contained within expected scopes.

| Test Type | Default Blast Radius | Measurement Method |
|-----------|---------------------|-------------------|
| Pod failure | 1 pod per 10; max 10% of replicas | `kubectl get pods` replica count diff; `kubectl describe pod` restart time |
| Node failure | 1 node per cluster; max 20% of worker nodes | Node count delta; `kubectl get nodes` readiness |
| Network partition | 1 subnet / 1 zone | Partition scope via `tc` rule cidr; zone tag from topology labels |
| etcd quorum loss | 1 member per cluster; max floor(n/2) members | `etcdctl member list` quorum count; `etcdctl endpoint status` health |

**Blast Radius Validation**

- Before each test: record baseline (replicas, nodes, etcd members, API health)
- During test: track delta from baseline in real time
- After test: compute `blast_radius = (affected / baseline) * 100%`
- Success: `blast_radius` ≤ defined limit for test type
- Failure: abort test, document deviation, adjust scope

---

## Test Execution Flow

1. **Pre-check**: Verify cluster health, error budget > 20%, all monitoring active
2. **Baseline**: Record current state (replicas, nodes, etcd health, API latency p99)
3. **Inject**: Apply chaos injection per test type
4. **Observe**: Monitor metrics, logs, alerts for duration of test window
5. **Reclaim**: Restore state (undelete pods, uncordon nodes, remove netem, restart etcd)
6. **Post-check**: Verify cluster back to baseline; compute blast radius; document results

---

## Safety Controls

- All tests require SRE on-call approval
- Tests paused automatically if error budget > 10% consumption
- No etcd member restart > 1 at a time
- Network chaos limited to non-production namespaces first
- Rollback procedure documented per test type
- All actions recorded in cluster audit log

---

## Related Documentation

- `../architecture/03-failure-domains.md` — Failure domain topology
- `../kubernetes/control-plane/ha-topology.md` — HA control plane design
- `../lifecycle/disaster-recovery/index.md` — Disaster recovery procedures
- `../monitoring/alert-rules.md` — Chaos-relevant alert rules