# Node Lifecycle

## A. Purpose and scope

Document Kubernetes node lifecycle procedures for clusters managed by Kubespray: add/remove nodes, cordon/uncordon, drain, taint/toleration, and node health monitoring. Cross-references `kubespray/kubespray-deployment.md` §Node lifecycle, `kubespray/kubespray-deployment.md` §Inventory, `lifecycle/upgrades/kubernetes.md` §Node upgrade sequence.

## B. Node types

| Type | Groups | Purpose |
|------|--------|---------|
| Control-plane | `[control-plane]`, `[etcd]` | API server, scheduler, controller-manager, stacked etcd |
| Worker | `[k8s-node]` | Application pods |
| GPU worker | `[k8s-node]`, `[gpu-node]` | GPU-accelerated workloads |

## C. Add worker

### 1. Add to inventory

```ini
[k8s-node]
k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23
```

### 2. Add OS and container runtime

The node must have:

- OS installed from internal mirror (Oracle Linux or Ubuntu)
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

## D. Add control-plane

### 1. Add to inventory

```ini
[control-plane]
k8s-cp-4 ansible_host=10.20.0.14 ip=10.20.0.14

[etcd]
k8s-cp-4
```

### 2. Add OS and container runtime

Same requirements as worker, plus etcd data directory storage (local SSD/NVMe).

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

**One control-plane node at a time** — never add all control-plane nodes simultaneously during a rebuild.

## E. Remove worker

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

## F. Replace worker

Replace = drain + remove + rebuild + re-add:

1. Drain: `kubectl drain k8s-w-3 --ignore-daemonsets --delete-emptydir-data`
2. Remove from inventory
3. Rebuild the host (Terraform + Ansible, or manual reinstall)
4. Re-add to inventory with same or new name
5. Run Kubespray: `cluster.yml -b --limit k8s-w-3`
6. Verify: node is Ready

## G. Cordon and uncordon

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

## H. Taint and toleration

### Add taint to control-plane nodes (default)

Control-plane nodes have the `node-role.kubernetes.io/control-plane:NoSchedule` taint applied by Kubespray. This prevents application pods from being scheduled on control-plane nodes unless they have a matching toleration.

### Add a dedicated taint for specialized workloads

```bash
kubectl taint node k8s-cp-5 dedicated=gpu:NoSchedule
```

### Add matching toleration to pod spec

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: gpu-workload
      image: gpu-image:latest
  tolerations:
    - key: dedicated
      operator: Equal
      value: gpu
      effect: NoSchedule
```

### Remove a taint

```bash
kubectl taint node k8s-cp-5 dedicated:NoSchedule-
```

## I. Node health monitoring

### Golden signals to monitor

| Signal | Tool | Alert condition |
|--------|------|-----------------|
| Latency | `kubectl top node`, Prometheus | Node response time > 500ms sustained |
| Traffic | Prometheus `node_network_receive_bytes_total` | Sudden drop > 90% |
| Errors | kubelet logs, Prometheus `kubelet_volume_errors_total` | Disk error rate spikes |
| Saturation | Prometheus `node_cpu_seconds_total`, `node_memory_Active_bytes` | CPU > 80% or memory > 85% for 5m |

### Health check commands

```bash
# Node status
kubectl get nodes -o wide

# Node conditions
kubectl describe node k8s-w-3 | grep -A 10 "Conditions:"

# Node allocatable
kubectl get nodes k8s-w-3 -o jsonpath='{.status.allocatable}'

# Kubelet status
systemctl status kubelet

# Node heartbeat
kubectl get nodes --request-timeout=5s

# Disk usage on node
ssh k8s-w-3 "df -h /var/lib/kubelet/pods"
```

### Node drain safety checks

Before draining, verify:

- No critical pods are DaemonSet-managed
- Pods are not stuck in `Terminating` state
- DaemonSet pods will be rescheduled to other nodes
- Pod disruption budgets (PDBs) allow eviction

```bash
kubectl drain k8s-w-3 --ignore-daemonsets --delete-emptydir-data --force
```

### Node reset (Kubespray)

Use Kubespray's `reset.yml` playbook to remove Kubernetes from a node:

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini reset.yml -b --limit k8s-w-3
```

**Warning:** `reset.yml` removes Kubernetes from the node. Only use on nodes that will be rebuilt or decommissioned. Never run `rm -rf /etc/kubernetes` manually — use `reset.yml` instead.

After reset, the node can be re-added with `cluster.yml`.

## J. Cross-references

- `kubespray/kubespray-deployment.md` §I — Node lifecycle
- `kubespray/kubespray-deployment.md` §D — Inventory grouping rules
- `lifecycle/upgrades/kubernetes.md` §E — Node upgrade sequence
- `compatibility/version-matrix.md` — Version pins
- `kubernetes/control-plane/index.md` §Failure scenarios — Control-plane failure scenarios