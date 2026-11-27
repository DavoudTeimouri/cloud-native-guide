# Resource Reservation

## A. Purpose and scope

Document kubelet resource reservation, pod priority classes, QoS classes, topology spread constraints.

Cross-references `kubernetes/control-plane/node-lifecycle.md`, `kubernetes/control-plane/index.md` §Sizing and placement.

## B. Kubelet resource reservation

Resource reservation reserves CPU and memory for Kubernetes system daemons:

```yaml
# kubelet config
kubeletConfig:
  systemReserved:
    cpu: "100m"
    memory: "256Mi"
  kubeReserved:
    cpu: "100m"
    memory: "256Mi"
  evictionHard:
    memory.available: "500Mi"
    nodefs.available: "10%"
    nodefs.inodesFree: "5%"
```

## C. Priority classes

Priority classes determine pod scheduling precedence:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "High priority for critical workloads"
```

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: cluster-critical
value: 2000000000
globalDefault: false
description: "Critical cluster system pods"
```

## D. QoS classes

Kubernetes assigns QoS classes based on resource requests and limits:

| QoS class | Requirements | OOM score |
|-----------|-------------|-----------|
| Guaranteed | All containers have equal requests and limits | -998 |
| Burstable | At least one container has request != limit | -998 to -999 |
| BestEffort | No requests or limits | -1000 |

## E. Topology spread constraints

Topology spread constraints distribute pods across failure domains:

```yaml
spec:
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: myapp
```

## F. Cross-references

- `kubernetes/control-plane/node-lifecycle.md` — Node lifecycle
- `kubernetes/control-plane/index.md` §Sizing and placement — Control plane sizing
- `kubernetes/admission-policy.md` — Admission policy
