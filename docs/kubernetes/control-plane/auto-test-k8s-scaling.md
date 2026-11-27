# Auto-Test Kubernetes Control-Plane Scaling

This document covers the procedures for testing Kubernetes control-plane scaling, including node add/remove and auto-scaling configuration validation. It is intended for automated testing and operational verification.

## A. etcd Quorum Checks

### 1. Check etcd cluster health

```bash
# Run on any control-plane node
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster
```

**Expected:** All members report `healthy`

### 2. Check etcd member list

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list
```

**Expected:** Member count matches inventory. A member list shorter than the inventory means a member was lost and must be replaced before the next failure.

### 3. etcd quorum rules

| Control-plane nodes | Tolerated failures | Quorum size |
|---|---|---|
| 3 nodes | 1 failure | 2/3 |
| 5 nodes | 2 failures | 3/5 |

**Never restart all control-plane nodes simultaneously** — this removes API server quorum and makes the cluster unreachable.

### 4. etcd snapshot verification (automated test)

```bash
# Verify latest snapshot is healthy
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  snapshot status /var/lib/etcd/snapshot-*.db \
  --write-out=table
```

Expected output shows `health: "true"`.

## B. API Server Health Checks

### 1. /healthz endpoint

```bash
kubectl get --raw='/healthz?verbose'
```

**Expected:** `200 OK` with healthy component statuses

### 2. /readyz endpoint

```bash
kubectl get --raw='/readyz?verbose'
```

**Expected:** All components `Ready` — API server, scheduler, controller-manager, etcd

### 3. API server availability through load balancer

```bash
curl -k https://<load-balancer-vip>:6443/healthz
curl -k https://<load-balancer-vip>:6443/readyz
```

## C. Controller-Manager Status

```bash
# Check controller-manager pod status
kubectl -n kube-system get pods -l component=controller-manager

# Describe controller-manager
kubectl -n kube-system describe pod -l component=controller-manager

# Check controller-manager metrics
kubectl -n kube-system get --raw '/readyz' | grep -i controller
```

**Expected:** All controller-manager pods are `Ready` and running

### Common issues
- Certificate expiry causing TLS hand failures
- CPU starvation on control-plane nodes
- etcd latency causing leader election flaps

## D. Scheduler Status

```bash
# Check scheduler pod status
kubectl -n kube-system get pods -l component=scheduler

# Describe scheduler
kubectl -n kube-system describe pod -l component=scheduler

# Check scheduler metrics
kubectl -n kube-system get --raw '/readyz' | grep -i scheduler
```

**Expected:** Scheduler pod is `Ready` and accepting scheduling decisions

### Common issues
- Resource constraints preventing pod scheduling
- Node selector/affinity misconfiguration
- Insufficient resources on target nodes

## E. Node Scaling Procedures

### 1. Add Control-Plane Node

#### a. Add to inventory

```ini
[control-plane]
k8s-cp-4 ansible_host=10.20.0.14 ip=10.20.0.14

[etcd]
k8s-cp-4
```

#### b. Add OS and container runtime

- OS installed from internal mirror (Oracle Linux or Ubuntu)
- containerd installed from internal repository
- SSH access for the Ansible user
- NTP/synchronized time
- etcd data directory storage: local SSD or NVMe (no shared storage)

#### c. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4
```

#### d. Verify

```bash
kubectl get nodes k8s-cp-4
kubectl -n kube-system get pods -l component=etcd --field-selector spec.nodeName=k8s-cp-4
kubectl -n kube-system exec etcd-k8s-cp-4 -- etcdctl endpoint health --cluster
```

**Rule:** Add one control-plane node at a time. Never add all control-plane nodes simultaneously during a rebuild.

### 2. Remove Control-Plane Node

#### a. Drain the node

```bash
kubectl drain k8s-cp-4 --ignore-daemonsets --delete-emptydir-data
```

#### b. Remove from inventory

Remove the node from `[control-plane]` and `[etcd]` in `inventory/<cluster>/hosts.ini`.

#### c. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4
```

#### d. Verify

```bash
kubectl get nodes | grep k8s-cp-4  # Should return nothing
kubectl -n kube-system get etcd-member-list  # Verify quorum intact
```

**Never remove more than one control-plane node at a time** without ensuring quorum remains intact.

### 3. Add Worker Node

#### a. Add to inventory

```ini
[k8s-node]
k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23
```

#### b. Add OS and container runtime

- OS installed from internal mirror
- containerd 2.3.7 installed from internal repository
- SSH access for the Ansible user
- NTP/synchronized time

#### c. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3
```

#### d. Verify

```bash
kubectl get nodes k8s-w-3
kubectl get pods -o wide --field-selector spec.nodeName=k8s-w-3
```

### 4. Remove Worker Node

#### a. Drain the node

```bash
kubectl drain k8s-w-3 --ignore-daemonsets --delete-emptydir-data
```

#### b. Remove from inventory

Remove the node from `[k8s-node]` in `inventory/<cluster>/hosts.ini`.

#### c. Run Kubespray

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3
```

#### d. Verify

```bash
kubectl get nodes | grep k8s-w-3  # Should return nothing
```

### 5. Cordon and Uncordon

#### Cordon (mark unschedulable)

```bash
kubectl cordon k8s-w-3
```

Use before maintenance or when a node is unhealthy.

#### Uncordon (mark schedulable)

```bash
kubectl uncordon k8s-w-3
```

Use after maintenance is complete and the node is healthy.

## F. Auto-Scaling Configuration

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

### 2. Cluster-Autoscaler

The cluster-autoscaler monitors pod pending times and adds/removes worker nodes automatically:

```bash
# Check cluster-autoscaler status
kubectl -n kube-system get deployment cluster-autoscaler -o yaml

# Scale the node group min/max size
kubectl -n kube-system patch deployment cluster-autoscaler -p '{"spec":{"template":{"spec":{"containers":[{"name":"cluster-autoscaler","resources":{"limits":{"cpu":"500m","memory":"512Mi"}}]}}}}'

# Node group scaling (managed by cloud provider or on-prem provisioner)
# See infrastructure-specific documentation for node group configuration
```

**Node group autoscaling rules:**
- Min replicas: 2 (high availability)
- Max replicas: based on infrastructure capacity and SLO error budget
- Scale-down delay: 10 minutes to avoid flapping
- Cooldown period: 5 minutes between scale events

### 3. Manual Scaling Override

To manually override auto-scaling during a window:

```bash
# Scale deployment manually
kubectl scale deployment app-deployment --replicas=5

# HPA resumes control on next metrics reconciliation
```

## G. Error Budget and SLO Considerations

- Node additions that increase API server load must not push latency p99 above the 300ms SLO target.
- HPA/VPA reactions are rate-limited; manual intervention may be required for rapid scaling.
- Cluster-autoscaler scale-out is blocked if the error budget is >80% consumed.
- Scale-in is blocked if pending pods exceed the available capacity threshold.

## H. Cross-References

- `kubernetes/control-plane/index.md` — Control plane decisions and operational boundaries
- `kubernetes/control-plane/ha-topology.md` — HA topology and failure domain design
- `kubernetes/control-plane/scaling-procedures.md` — Existing scaling procedures
- `kubernetes/node-lifecycle.md` — Full node lifecycle procedures (add/remove/reset)
- `addons/vpa.md` — Vertical Pod Autoscaler configuration
- `lifecycle/upgrades/upgrade-procedures.md` — Upgrade procedures and node upgrade sequence
- `addons/metrics-server.md` — Metrics pipeline for HPA calculations
- `monitoring/prometheus-rules.md` — Alerting rules for scaling events