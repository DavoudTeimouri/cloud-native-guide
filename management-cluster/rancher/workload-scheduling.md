# Rancher Workload Scheduling

[Previous step](../rancher/rancher.md) | [Next step](../../kubespray/kubespray-deployment.md]

## A. Purpose and scope

Document Rancher and Kubernetes workload scheduling mechanisms: resource requests/limits, node affinity, pod affinity/anti-affinity, topology spread constraints, and priority classes. These controls determine where pods are placed, how they compete for resources, and how critical workloads are prioritized during resource contention.

Cross-references `management-cluster/rancher/rancher.md` §Architecture, `kubernetes/scheduling/priority-classes.md` §Priority classes, `kubernetes/scheduling/resource-reservation.md` §QoS classes.

## B. Resource requests and limits

Resource requests and limits determine the QoS class and influence scheduling decisions.

```yaml
apiVersion: v1
kind: Pod
spec:
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

| Resource | Requests | Limits | Effect |
|---|---|---|---|
| **CPU** | Guaranteed scheduling slot; vCPU charged at runtime | Capped at limit; excess throttled on `cpu.cfs_quota` | Requests = minimum guaranteed; Limits = maximum consumption |
| **Memory** | Guaranteed memory available at admission | OOM killed if exceeded; no throttling | Requests determine QoS class; Limits determine OOM boundary |

### QoS class derivation

| QoS class | CPU requests/limits | Memory requests/limits | Typical use |
|---|---|---|---|
| **Guaranteed** | All containers have equal requests and limits | All containers have equal requests and limits | Critical stateful workloads |
| **Burstable** | At least one container has request != limit | At least one container has request != limit | Most application workloads |
| **BestEffort** | No requests or limits | No requests or limits | Batch/job workloads |

## C. Node affinity

Node affinity schedules pods based on node labels. Use it to constrain workloads to specific node groups (e.g., GPU nodes, bare-metal, zoned infrastructure).

### Node affinity types

| Type | Syntax | Behavior |
|---|---|---|
| **Required during scheduling** (`requiredDuringSchedulingIgnoredDuringExecution`) | `nodeSelectorTerms[0].matchExpressions[0].operator In` | Pod will not schedule unless at least one term matches; enforced at pod creation |
| **Preferred during scheduling** (`preferredDuringSchedulingIgnoredDuringExecution`) | `nodeSelectorTerms[0].weightedPreferredSchedulingTerms[0].weight` | Soft preference; scheduler tries to find a matching node but falls back |

### Example: required node affinity

```yaml
apiVersion: v1
kind: Pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["amd64", "arm64"]
              - key: topology.kubernetes.io/zone
                operator: In
                values: ["us-west-2a", "us-west-2b"]
```

### Example: preferred node affinity

```yaml
apiVersion: v1
kind: Pod
spec:
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 80
          preference:
            matchExpressions:
              - key: node-type
                operator: In
                values: ["gpu"]
        - weight: 60
          preference:
            matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values: ["us-west-2a"]
```

## D. Pod affinity and anti-affinity

Pod affinity/anti-affinity control scheduling based on labels of *other* pods already running on a node. Use affinity to co-locate related workloads (e.g., frontend + backend) and anti-affinity to separate them.

### Affinity types

| Type | Operator | Behavior |
|---|---|---|
| **Required** (`requiredDuringSchedulingIgnoredDuringExecution`) | `In` | Pod will not schedule unless the condition is met |
| **Preferred** (`preferredDuringSchedulingIgnoredDuringExecution`) | Weight + label selector | Soft preference with weight (0-100) |
| **Not** (`requiredDuringSchedulingIgnoredDuringExecution`) | `Not In` | Pod will not schedule if any label matches |

### Example: pod affinity (co-locate)

```yaml
apiVersion: v1
kind: Pod
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values: ["backend"]
          topologyKey: topology.kubernetes.io/zone
```

### Example: pod anti-affinity (separate)

```yaml
apiVersion: v1
kind: Pod
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values: ["database"]
          topologyKey: topology.kubernetes.io/zone
```

### Soft preferred affinity

```yaml
apiVersion: v1
kind: Pod
spec:
  affinity:
    podAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          preference:
            labelSelector:
              matchExpressions:
                - key: app
                  operator: In
                  values: ["cache"]
            topologyKey: topology.kubernetes.io/hostname
```

## E. Topology spread constraints

Topology spread constraints distribute pods across failure domains (nodes, zones, hosts) to improve availability and fault tolerance.

### Structure

```yaml
apiVersion: v1
kind: Deployment
spec:
  template:
    spec:
      affinity: {}
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: my-app
```

### `maxSkew` options

| Value | Description |
|---|---|
| `Integer` | Maximum difference between the highest and lowest pod counts across topology nodes |
| `Fraction` | Percentage-based skew (alpha feature, not recommended for production) |

### `whenUnsatisfiable` options

| Option | Behavior |
|---|---|
| `DoNotSchedule` | Pods are not scheduled if the constraint cannot be satisfied |
| `ScheduleAnyway` | Pods are scheduled regardless; skew may occur |
| `MostSuitable` (default) | Scheduler picks the most suitable node among candidates |

### Example: multi-zone spread

```yaml
apiVersion: v1
kind: Deployment
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: my-app
```

### Example: spread across nodes (host-level)

```yaml
apiVersion: v1
kind: Deployment
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: my-app
```

## F. Priority classes

Priority classes assign a priority to pods, influencing scheduling order and preemption behavior. Higher-priority pods are scheduled ahead of lower-priority pods and can preempt them when resources are insufficient.

### Built-in priority classes

| Name | Value | Description |
|---|---|---|
| `system-node-critical` | 2000000000 | K8s system pods (kube-proxy, DNS, device plugins) |
| `system-cluster-critical` | 2000000000 | Cluster networking, storage controllers |

### Custom priority class example

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pods
value: 1000000000
globalDefault: false
description: "Critical business workloads — scheduled before all other priorities"
```

### Preemption policy

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

### Policy options

| Policy | Behavior |
|---|---|
| `PreemptLowerPriority` (default) | Preempts pods with lower `priorityClassValue`; does not preempt pods with equal or higher priority |
| `NeverPreemptLowerPriority` | Never preempts lower-priority pods; the pod will remain in `Pending` state if no node can satisfy it |

### Global default

Set a `globalDefault` PriorityClass to apply a baseline priority to all pods that do not specify `priorityClassName`. **Best practice**: Do not set `globalDefault: true` for very high values (e.g., >1000000) as it can cause unexpected preemption behavior. Instead, explicitly set `priorityClassName` on critical pods.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: true
description: "Baseline priority for all pods without explicit priority class"
```

### Usage in pod spec

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

## G. Cross-references

- `management-cluster/rancher/rancher.md` — Rancher deployment and architecture
- `kubernetes/scheduling/priority-classes.md` — Kubernetes priority classes and preemption
- `kubernetes/scheduling/resource-reservation.md` — QoS classes and kubelet resource reservation
- [Kubernetes scheduler documentation](https://kubernetes.io/docs/concepts/scheduling/) — Official scheduler reference
- [Kubernetes topology spread constraints](https://kubernetes.io/docs/concepts/workloads/controllers/topology-sped-constraints/) — Official topology spread docs

## H. Best practices

- **Set resource requests** equal to actual minimum usage; over-requesting wastes cluster capacity and can cause scheduling failures.
- **Use node affinity** for hardware-specific or regulatory constraints (GPU, compliance zones, bare-metal).
- **Prefer pod anti-affinity** for stateful services to avoid co-locating replicas on the same node.
- **Apply topology spread constraints** across zones to protect against zone-level failures; use `maxSkew: 1` as a starting point.
- **Assign priority classes** to critical system and business workloads; avoid `globalDefault: true` for high values.
- **Combine multiple scheduling mechanisms** for complex placement: e.g., node affinity + topology spread constraints for multi-zone dedicated infrastructure.
- **Verify scheduling with `kubectl describe pod <pod-name> --field-selector=status.phase=Pending`** to understand why a pod is not scheduling.

---
[Previous step](../rancher/rancher.md) | [Next step](../../kubespray/kubespray-deployment.md)