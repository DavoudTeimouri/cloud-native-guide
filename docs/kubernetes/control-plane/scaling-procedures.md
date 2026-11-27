# Cluster Scaling Procedures

## Overview

This document covers adding and removing control-plane and worker nodes, auto-scaling configuration, and drain/uncordon workflows for Kubernetes clusters managed by Kubespray.

Cross-references: `kubernetes/control-plane/index.md`, `kubernetes/node-lifecycle.md`, `addons/vpa.md`.

## A. Node Types

| Type | Groups | Purpose |
|------|--------|---------|
| Control-plane | `[control-plane]`, `[etcd]` | API server, scheduler, controller-manager, stacked etcd |
| Worker | `[k8s-node]` | Application pods |
| GPU worker | `[k8s-node]`, `[gpu-node]` | GPU-accelerated workloads |

## B. Add Control-Plane Node

### 1. Add to inventory

```ini
[control-plane]
k8s-cp-4 ansible_host=10.20.0.14 ip=10.20.0.14

[etcd]
k8s-cp-4
```

### 2. Add OS and container runtime

- OS installed from internal mirror (Oracle Linux or Ubuntu)
- containerd installed from internal repository
- SSH access for the Ansible user
- NTP/synchronized time
- etcd data directory storage: local SSD or NVMe (no shared storage)

### 3. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4
```

### 4. Verify

```bash
kubectl get nodes k8s-cp-4
kubectl -n kube-system get pods -l component=etcd --field-selector spec.nodeName=k8s-cp-4
kubectl -n kube-system exec etcd-k8s-cp-4 -- etcdctl endpoint health --cluster
```

**Rule:** Add one control-plane node at a time. Never add all control-plane nodes simultaneously during a rebuild.

## C. Remove Control-Plane Node

### 1. Drain the node

```bash
kubectl drain k8s-cp-4 --ignore-daemonsets --delete-emptydir-data
```

### 2. Remove from inventory

Remove the node from `[control-plane]` and `[etcd]` in `inventory/<cluster>/hosts.ini`.

### 3. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4
```

### 4. Verify

```bash
kubectl get nodes | grep k8s-cp-4  # Should return nothing
kubectl -n kube-system get etcd-member-list  # Verify quorum intact
```

**Never remove more than one control-plane node at a time** without ensuring quorum remains intact.

## D. Add Worker Node

### 1. Add to inventory

```ini
[k8s-node]
k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23
```

### 2. Add OS and container runtime

- OS installed from internal mirror
- containerd 2.3.7 installed from internal repository
- SSH access for the Ansible user
- NTP/synchronized time

### 3. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3
```

### 4. Verify

```bash
kubectl get nodes k8s-w-3
kubectl get pods -o wide --field-selector spec.nodeName=k8s-w-3
```

## E. Remove Worker Node

### 1. Drain the node

```bash
kubectl drain k8s-w-3 --ignore-daemonsets --delete-emptydir-data
```

### 2. Remove from inventory

Remove the node from `[k8s-node]` in `inventory/<cluster>/hosts.ini`.

### 3. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3
```

### 4. Verify

```bash
kubectl get nodes | grep k8s-w-3  # Should return nothing
```

## F. Replace Worker Node

Replace = drain + remove + rebuild + re-add:

1. Drain: `kubectl drain k8s-w-3 --ignore-daemonsets --delete-emptydir-data`
2. Remove from inventory
3. Rebuild the host (Terraform + Ansible, or manual reinstall)
4. Re-add to inventory with same or new name
5. Run Kubespray: `cluster.yml -b --limit k8s-w-3`
6. Verify: node is Ready

## G. Cordon and Uncordon

### Cordon (mark unschedulable)

```bash
kubectl cordon k8s-w-3
```

Use before maintenance or when a node is unhealthy.

### Uncordon (mark schedulable)

```bash
kubectl uncordon k8s-w-3
```

Use after maintenance is complete and the node is healthy.

## H. Auto-Scaling Configuration

### 1. Horizontal Pod Autoscaler (HPA)

HPA is configured per-workload based on CPU and memory utilization:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2. Vertical Pod Autoscaler (VPA)

VPA is configured for stateful workloads that benefit from automatic resource adjustment. See `addons/vpa.md` for deployment and operation procedures.

### 3. Cluster-Autoscaler

The cluster-autoscaler monitors pod pending times and adds/removes worker nodes automatically:

```bash
# Check cluster-autoscaler status
kubectl -n kube-system get deployment cluster-autoscaler -o yaml

# Scale the node group min/max size
kubectl -n kube-system patch deployment cluster-autoscaler -p '{"spec":{"template":{"spec":{"containers":[{"name":"cluster-autoscaler","resources":{"limits":{"cpu": "500m","memory": "512Mi"}}]}}}}'

# Node group scaling (managed by cloud provider or on-prem provisioner)
# See infrastructure-specific documentation for node group configuration
```

**Node group autoscaling rules:**
- Min replicas: 2 (high availability)
- Max replicas: based on infrastructure capacity and SLO error budget
- Scale-down delay: 10 minutes to avoid flapping
- Cooldown period: 5 minutes between scale events

### 4. Manual Scaling Override

To manually override auto-scaling during a window:

```bash
# Scale deployment manually
kubectl scale deployment app-deployment --replicas=5

# HPA resumes control on next metrics reconciliation
```

## I. Error Budget and SLO Considerations

- Node additions that increase API server load must not push latency p99 above the 300ms SLO target.
- HPA/VPA reactions are rate-limited; manual intervention may be required for rapid scaling.
- Cluster-autoscaler scale-out is blocked if the error budget is >80% consumed.
- Scale-in is blocked if pending pods exceed the available capacity threshold.

## J. Cross-References

- `kubernetes/control-plane/index.md` — Control plane decisions and operational boundaries
- `kubernetes/control-plane/ha-topology.md` — HA topology and failure domain design
- `kubernetes/node-lifecycle.md` — Full node lifecycle procedures (add/remove/reset)
- `addons/vpa.md` — Vertical Pod Autoscaler configuration
- `lifecycle/upgrades/upgrade-procedures.md` — Upgrade procedures and node upgrade sequence
- `addons/metrics-server.md` — Metrics pipeline for HPA calculations
- `monitoring/prometheus-rules.md` — Alerting rules for scaling events