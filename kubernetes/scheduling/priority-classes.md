# Priority Classes and Preemption

## A. Purpose and scope

Document Kubernetes `PriorityClass` and `PriorityConfiguration` for pod scheduling precedence, preemption policies, and resource quota integration. Cross-references `kubernetes/scheduling/resource-reservation.md` §Priority classes.

## B. PriorityClass definition

A `PriorityClass` is a cluster-level object that assigns a priority to pods. Higher-priority pods are scheduled ahead of lower-priority pods and preempt them when necessary.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pods
value: 1000000000
globalDefault: false
description: "Critical business workloads — scheduled before all other priorities"
```

| Field | Required | Description |
|-------|--------|-------------|
| `value` | yes | Integer priority value. Higher values = higher precedence. Range: -2147483648 to 2147483647 |
| `globalDefault` | no | If true, assigns this priority to all pods without an explicit `priorityClassName` |
| `description` | no | Human-readable description (visible in `kubectl describe`) |

### Recommended priority values

| Priority class name | Value | Use case |
|---------------------|-------|----------|
| `system-node-critical` | 2000000000 | K8s system pods (kube-proxy, DNS, etc.) |
| `system-cluster-critical` | 2000000000 | Cluster networking, storage controllers |
| `critical-pods` | 1000000000 | Business-critical workloads |
| `high-priority` | 1000000 | Important but preemptable workloads |
| `normal-pods` | 0 | Default / best-effort workloads |

## C. Preemption policies

When the scheduler cannot find a feasible node for a pod, it may **preempt** (terminate) lower-priority pods to make room. Preemption is controlled per `PriorityClass` via the `preemptionPolicy` field.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pods
value: 1000000000
preemptionPolicy: PreemptLowerPriority
globalDefault: false
description: "Preempts lower-priority pods when scheduling"
```

### PreemptionPolicy options

| Policy | Behavior |
|--------|----------|
| `PreemptLowerPriority` (default) | Preempts pods with lower `priorityClassValue`; does not preempt pods with equal or higher priority |
| `NeverPreemptLowerPriority` | Never preempts lower-priority pods; the pod will remain in a `Pending` state if no node can satisfy it |

### Controlling preemption with `clusterSettings`

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: ClusterSettings
metadata:
  name: scheduler
spec:
  defaultPreemptionPolicy: PreemptLowerPriority
```

## D. Resource quota integration

Priority classes interact with resource quotas to determine which pods can be scheduled. When a namespace has a `ResourceQuota`, the scheduler considers:

1. **Total allocatable resources** across all pods in the namespace
2. **Priority order** when admitting new pods
3. **Preemption decisions** based on priority differences

### Example: Namespace with resource quota and priority classes

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: critical-workloads
annotations:
  scheduler.alpha.kubernetes.io/critical-pods: "true"
---
apiResourceQuota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: critical-quota
  namespace: critical-workloads
spec:
  hard:
    cpu: "50"
    memory: "100Gi"
    pods: "20"
    requests.cpu: "40"
    requests.memory: "80Gi"
```

### Interaction summary

| Scenario | Behavior |
|----------|----------|
| High-priority pod exceeds quota | Admission denied unless preemption removes lower-priority pods |
| Low-priority pod in namespace with high-priority traffic | May be preempted to satisfy the high-priority pod |
| `globalDefault: true` PriorityClass | All pods without explicit `priorityClassName` get this priority |

## E. Default priority class configuration

Set a `globalDefault` PriorityClass to apply a baseline priority to all pods that do not specify `priorityClassName`. This ensures no pod falls below a minimum precedence.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: true
description: "Baseline priority for all pods without explicit priority class"
```

**Best practice**: Do not set `globalDefault: true` for very high values (e.g., >1000000) as it can cause unexpected preemption behavior. Instead, explicitly set `priorityClassName` on critical pods.

## F. Example PriorityClass YAML

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pods
value: 1000000000
preemptionPolicy: PreemptLowerPriority
description: "Critical business workloads — preempts lower-priority pods to ensure availability"
```

### Usage

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-critical-app
spec:
  priorityClassName: critical-pods
  containers:
    - name: app
      image: myapp:latest
      resources:
        requests:
          cpu: "500m"
          memory: "512Mi"
        limits:
          cpu: "1"
          memory: "1Gi"
```

## G. Preemption victim selection guidance

When the scheduler decides which pods to preempt, it follows these rules:

1. **Select lowest total value first** — Among all pods in the scheduling queue, prefer preempting pods with the lowest `priorityClassValue`
2. **Minimize preempted pods** — Preempt the minimum number of pods needed to satisfy the higher-priority pod
3. **Respect `preemptionPolicy`** — Pods with `NeverPreemptLowerPriority` are never selected; pods with `PreemptLowerPriority` can be selected only if their value is lower than the incoming pod's value
4. **Consider pod disruption budgets (PDBs)** — Prefer preempting pods that have PDB `minAvailable > 0` or no PDB at all
5. **Avoid starving system-critical pods** — System pods (`system-node-critical`, `system-cluster-critical`) are never preempted even if their value is lower

### Visual flow

```
High-priority pod arrives → Scheduler checks resources →
No fit → Check preemption candidates →
  ▼
  Lowest priority value first →
  ▼
  PDB compliance check →
  ▼
  Preempt and reschedule
```

## H. Cross-references

- `kubernetes/scheduling/resource-reservation.md` — Kubelet resource reservation and QoS classes
- `kubernetes/control-plane/node-lifecycle.md` — Node lifecycle and taints
- [Kubernetes PriorityClass docs](https://kubernetes.io/docs/concepts/scheduling-preemption-and-priority-classes/)
- [Kubernetes scheduler preemption](https://kubernetes.io/docs/concepts/scheduling-preemption-and-priority-classes/#preemption)
