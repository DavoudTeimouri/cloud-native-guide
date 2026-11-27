# Rancher Node Pool Management

[Previous step](../rancher/rancher.md) | [Next step](../../kubespray/kubespray-deployment.md)

## A. Purpose and scope

Node pools control the lifecycle of node groups within the management cluster and application clusters. Proper node pool management ensures capacity availability, enables rolling upgrades without downtime, and prevents workloads from being scheduled on nodes undergoing maintenance. This document covers the full node pool lifecycle: creation, scaling, auto-scaling, taints/labels, drain/cordon, and upgrade strategies.

## B. Node pool creation

### 1. Identify the purpose

- **Baseline worker pool**: General-purpose nodes running application workloads.
- **Dedicated pool**: Nodes with specialized hardware (GPU, storage) or security requirements.
- **Upgrade pool**: Nodes targeted for a rolling upgrade batch.

### 2. Create via Rancher UI

1. Navigate to **Cluster Management** → target cluster → **Nodes** → **Node Pools** → **Add node pool**.
2. Specify a **Name** (e.g., `general`, `gpu`, `upgrade-batch-1`).
3. Select the **Instance type**, **OS image**, and **Root disk size**.
4. Set the **Initial replica count** (minimum 2 for high availability).
5. Click **Create**.

### 3. Create via `kubectl` / `rancher-cli` (GitOps)

```bash
# Example: add a general worker pool via the Rancher API
curl -sk -u "$RANCHER_TOKEN:$RANCHER_TOKEN" \
  -X POST "https://rancher.internal/v3/cluster-api-providers/capa/aws/nodepools" \
  -d '{
    "name": "general",
    "labels": {"node-role.kubernetes.io/general": ""},
    "taints": [{"key": "node-type", "value": "general", "effect": "NoSchedule"}],
    "capacity": "on-demand",
    "instance_type": "m5.large",
    "desired_capacity": 4,
    "max_capacity": 8,
    "min_capacity": 2
  }'
```

### 4. RKE2-specific: add node pool with rke2

```bash
# Create a node pool using the Rancher agent manifest
kubectl apply -f https://releases.rancher.com/rancher-agent/v2.15/rke2-k3s.yaml
# Then in the Rancher UI, the new nodes will appear under the cluster's node pools.
```

### 5. Verification

```bash
# List all node pools in the cluster
kubectl -n cattle-system get nodepools -A

# Confirm the new pool is present and its desired/replica counts
kubectl -n cattle-system describe nodepools <pool-name>
```

## C. Scaling node pools

### 1. Manual scaling (Rancher UI)

1. Go to **Cluster Management** → target cluster → **Nodes** → **Node Pools**.
2. Click the **⋮** menu → **Edit** on the target pool.
3. Adjust the **Desired** replica count.
4. Save changes. The ASG (Auto Scaling Group) will reconcile within the provider's reconciliation interval.

### 2. Manual scaling (CLI)

```bash
# Scale a node pool desired count
kubectl -n cattle-system scale nodepool <pool-name> --replicas=6

# Verify
kubectl -n cattle-system get nodepools <pool-name> -o yaml | grep -E "desired|replicas"
```

### 3. Scaling rationale

| Scenario | Action |
|---|---|
| Adding capacity for a new feature flag | Increase desired by the expected workload size |
| Removing underutilized nodes | Decrease desired; verify drain completes first |
| Preparing for an upgrade | Scale up the upgrade pool before draining the old batch |

### 4. Cloud provider auto-scaling group bounds

When scaling via the underlying ASG, verify `min_capacity`, `desired_capacity`, and `max_capacity` are set appropriately:

```bash
# Describe the ASG linked to the node pool
aws autoscaling describe-auto-scaling-groups \
  --filter "Name=tag:Name,Values=<pool-name>*" \
  --query "AutoScalingGroups[0].{Min: MinSize, Desired: DesiredCapacity, Max: MaxSize}"
```

## D. Auto-scaling node pools

### 1. Enable cluster-autoscaler

The Cluster Autoscaler works with the ASG to grow/shrink node pools based on pod scheduling needs.

```bash
# Deploy the Cluster Autoscaler (Rancher-managed cluster example)
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm install cluster-autoscaler rancher-stable/cluster-autoscaler \
  --namespace cattle-system \
  --set awsRegion=us-east-1 \
  --set nodeGroupSelector=nodepool-name=<pool-name> \
  --set scaleDown.enabled=true \
  --set scaleDown.unneededTime=6m \
  --set scaleDown.skipNodesWithLocalStorage=true
```

### 2. Auto-scaling configuration

Configure the Cluster Autoscaler deployment with these parameters:

| Parameter | Recommended value | Description |
|---|---|---|
| `--scale-down-unneeded-time` | `6m` | Nodes unneeded for 6 minutes are candidates for scale-down |
| `--scale-down-skips-nodes-with-local-storage` | `true` | Prevents losing ephemeral local data |
| `--node-group-auto-discovery` | `tag` | Auto-discovers node groups by tag |
| `--scale-down-after-transition` | `5m` | Wait 5m after a scale-up before considering scale-down |

### 3. Pod disruption budget (PDB) considerations

Ensure PDBs allow nodes to be removed:

```yaml
# Example PDB that allows 1 unavailable during scale-down
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: app-ns
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: my-app
```

### 4. Auto-scaling troubleshooting

```bash
# Check Cluster Autoscaler logs
kubectl -n cattle-system logs deployment/cluster-autoscaler

# Manual node addition/removal is blocked if the autoscaler is active.
# To manually add a node, temporarily disable the autoscaler or use a
# separate ASG not managed by the autoscaler.
```

## E. Taints and labels

### 1. Purpose of taints

- **NoSchedule**: Pods without a matching toleration are not scheduled onto the node.
- **PreferNoSchedule**: Pods without a matching toleration are preferred not to be scheduled, but may still be placed if no other node is available.
- **NoExecute**: Pods already running on the node are evicted if they don't have a matching toleration; also blocks new scheduling.

### 2. Common taint patterns

| Taint | Use case |
|---|---|
| `key=value:NoSchedule` | Dedicated pools (GPU, storage, isolated workloads) |
| `key=value:NoExecute` | Draining nodes for upgrade; taint-added automatically during drain |
| `node-role.kubernetes.io/control-plane:NoSchedule` | Control-plane nodes only (Rancher sets this automatically) |

### 3. Add/remove taints via Rancher UI

1. Go to **Cluster Management** → target cluster → **Nodes**.
2. Click the **⋮** menu on the target node → **Edit taints**.
3. Add a new taint with **Key**, **Value**, and **Effect**.
4. Click **Save**.

### 4. Add/remove taints via CLI

```bash
# Add a taint to a node
kubectl taint nodes <node-name> key=value:NoSchedule

# Remove a specific taint (keep others)
kubectl taint nodes <node-name> key=value:NoSchedule-

# Remove all taints
kubectl taint nodes <node-name> -

# List current taints
kubectl describe node <node-name> | grep Taints
```

### 5. Common label patterns

| Label | Typical value | Purpose |
|---|---|---|
| `node-role.kubernetes.io/<role>` | `` | Identifies the node role |
| `nodepool-name/<name>` | `<pool-name>` | Links node to its pool |
| `cluster-name/<cluster>` | `<cluster>` | Identifies the cluster ownership |
| `failure-domain.beta.kubernetes.io/zone` | `<zone>` | AZ awareness for scheduler |

### 6. Bulk label/taint application on node pool creation

When creating a node pool, apply labels and taints at the pool level so all nodes inherit them automatically. This avoids per-node operations and ensures consistency across scale-out events.

## F. Drain and cordon

### 1. Cordon a node (prevent new scheduling)

```bash
# Mark node as unschedulable
kubectl cordon <node-name>

# Verify
kubectl describe node <node-name> | grep -i schedulable
# Output: ...
#        Schedulable: true  # becomes "false" after cordon
```

### 2. Drain a node (evict pods safely)

```bash
# Drain with PDB awareness and graceful deletion
kubectl drain <node-name> \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --timeout=300s \
  --grace-period=30
```

**Flags explained:**

| Flag | Purpose |
|---|---|
| `--ignore-daemonsets` | Skips DaemonSet pods (they are recreated elsewhere) |
| `--delete-emptydir-data` | Removes emptyDir volumes |
| `--timeout` | Maximum time to wait for pod eviction |
| `--grace-period` | Seconds of grace given to each pod before force-delete |

### 3. Drain during node pool upgrade

The standard upgrade pattern is:

```bash
# 1. Cordon the node (optional, if using --delete-emptydir-data)
kubectl cordon <node-name>

# 2. Drain the node (evicts pods respecting PDBs)
kubectl drain <node-name> --ignore-daemonsets --timeout=300s

# 3. (Optional) If the node comes back, taint it for the upgrade
kubectl taint nodes <node-name> key=upgrade-effect:NoSchedule

# 4. After upgrade completes, remove the taint
kubectl taint nodes <node-name> key=upgrade-effect:NoSchedule-
```

### 4. Re-enable scheduling after drain

```bash
# Mark node as schedulable again
kubectl uncordon <node-name>
```

### 5. Bulk cordon/drain via node pool

Since cordon/drain operate on individual nodes, use the node pool as a loop:

```bash
# List nodes in a pool and cordon each
kubectl get nodes -l nodepool-name=<pool-name> -o name | while read -r node; do
  kubectl cordon "$node"
done
```

## G. Node pool upgrade strategies

### 1. Rolling upgrade (recommended)

The safest approach for production clusters: upgrade one node pool at a time, maintaining enough capacity for workloads throughout.

```bash
# Step 1: Scale up the new node pool (or create a new pool with the target version)
kubectl -n cattle-system scale nodepool <pool-name> --replicas=2

# Step 2: Taint the new nodes so existing workloads are not disrupted
kubectl taint nodes -l nodepool-name=<pool-name> version=upgraded:NoSchedule

# Step 3: Drain and upgrade old nodes one at a time
for node in $(kubectl get nodes -l nodepool-name=<pool-name> -o name); do
  kubectl drain "$node" --ignore-daemonsets --timeout=300s
  # Node is removed from the pool; new node with updated OS/image joins
done

# Step 4: Scale down to desired count
kubectl -n cattle-system scale nodepool <pool-name> --replicas=<desired>
```

### 2. Canary upgrade (for risky OS / kernel updates)

1. Create a **new** node pool with the target OS/image version.
2. Set a small **desired capacity** (e.g., 1-2 nodes).
3. Deploy a canary workload that exercises the new environment.
4. If the canary passes, scale up the new pool and drain the old one.
5. If the canary fails, roll back by deleting the new pool.

### 3. Blue-green at the node-pool level

| Phase | Action |
|---|---|
| **Blue** | Existing node pool running the current version |
| **Green** | New node pool spun up on the target version |
| **Shift traffic** | Gradually move workloads to the green pool (via PDBs, re-deploys, or service ingress changes) |
| **Retire blue** | Drain and delete the old node pool |

### 4. Upgrade rollback

If an upgrade fails mid-stream:

```bash
# Identify the last known-good node pool configuration
kubectl -n cattle-system get nodepools -o yaml > /tmp/before-upgrade.yaml

# Re-apply the previous desired count and taints
kubectl -n cattle-system scale nodepool <pool-name> --replicas=<previous-count>

# Restore taints that were in effect before the upgrade
kubectl taint nodes -l nodepool-name=<pool-name> <previous-taints>
```

### 5. Post-upgrade verification

```bash
# Confirm all nodes report the expected OS version / Rancher agent version
kubectl get nodes -o wide | grep -E "VERSION|AgentVersion"

# Run the health check from rancher.md §G
curl -k https://rancher.internal/v3/health

# Verify fleet sync is healthy after the node pool change
fleetctl get clusters -o wide
```

### 6. Upgrade checklist

- [ ] Backup etcd and critical cluster records
- [ ] Confirm sufficient capacity in the remaining node pools
- [ ] Verify PDBs allow drain of target nodes
- [ ] Taint new nodes before draining old ones
- [ ] Execute drain one node at a time; wait for pod reconciliation
- [ ] Confirm no `NotReady` nodes remain longer than the `cluster-autoscaler` grace period
- [ ] Run integration smoke test against the upgraded nodes
- [ ] Document the upgrade in the change log

---
[Previous step](../rancher/rancher.md) | [Next step](../../kubespray/kubespray-deployment.md)