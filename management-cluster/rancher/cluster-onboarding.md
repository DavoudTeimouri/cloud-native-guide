# Rancher Cluster Onboarding

## A. Purpose and scope

Document cluster onboarding: importing existing clusters, provisioning new clusters, cluster registration, and validation procedures. Cross-references `management-cluster/rancher/rancher.md`, `management-cluster/rancher/cluster-lifecycle.md`, `management-cluster/rancher/fleet-integration.md`.

## B. Importing existing clusters

### In-cluster registration

The Rancher agent is deployed inside the target cluster. The target cluster must be reachable from Rancher.

```bash
# In the Application Cluster
kubectl -n cattle-system create secret generic cattle-cluster-agent \
  -n cattle-system --from-literal="token=<token>" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f https://releases.rancher.com/rancher-agent/v2.15/rke2-k3s.yaml   # for RKE2
```

For a Kubespray-built (kubeadm) cluster, use the `rke2` agent manifest only if the cluster is RKE2. For kubeadm clusters, Rancher supports the "import existing" flow with the agent applied by hand:

```bash
# Import existing cluster via agent manifest
kubectl apply -f https://releases.rancher.com/rancher-agent/v2.15/agent.yaml
```

The exact manifest path must be confirmed against the pinned Rancher release before use.

### Out-of-cluster registration

Rancher deploys the agent using kubeconfig. Use this when firewalls prevent Rancher from reaching the target cluster's API.

```bash
# Generate registration token in Rancher UI
# Or via API: rancher cluster-token create <cluster-name>

# Join cluster nodes
curl -sLf https://ranchermirror.internal/rancher/v3/cluster-registration-token | \
  bash -s -- --etcd --controlplane --worker
```

## C. Provisioning new clusters

### Kubespray deployment

New clusters are provisioned using Kubespray with the same OS baseline as the management cluster. Three workers is the default; one is acceptable for a lab and gives no rollout headroom for the Rancher upgrade itself.

```bash
# Generate hosts inventory
python3 contrib/inventory_builder.py -i <inventory_name> --etcd --control-plane --worker

# Apply Kubespray
ansible-playbook -i <inventory> site.yml --tags=rke-cluster
```

### RKE2 cluster provisioning

```bash
# RKE2 install via systemd
systemctl enable rke2
systemctl start rke2

# Verify cluster status
rke2ctl get-cluster-token
kubectl get nodes
```

### K3s cluster provisioning

```bash
# K3s install
curl -sfL https://get.k3s.io | sh -

# Verify cluster status
kubectl get nodes
```

## D. Cluster registration

### Registration models

| Model | How | Use |
|---|---|---|
| In-cluster registration | The agent is deployed inside the target cluster by Rancher | The target cluster is reachable from Rancher |
| Out-of-cluster registration | Rancher deploys the agent using kubeconfig | Firewalls prevent Rancher from reaching the target cluster's API |

### Registration token flow

```bash
# 1. Generate token in Rancher UI or API
rancher cluster-token create <cluster-name>

# 2. Join cluster nodes with token
curl -sLf https://ranchermirror.internal/rancher/v3/cluster-registration-token | \
  bash -s -- --etcd --controlplane --worker
```

### Agent-based import for kubeadm clusters

```bash
# Apply the Rancher agent manifest
kubectl apply -f https://releases.rancher.com/rancher-agent/v2.15/agent.yaml
```

Confirm the exact manifest path against the pinned Rancher release before use.

## E. Validation procedures

### Rancher is up

```bash
# Check Rancher pods
kubectl -n cattle-system get pods

# Health check
curl -k https://rancher.internal/v3/health
```

### Managed cluster registration and nodes visible

```bash
# Rancher UI: Cluster Management -> the cluster -> Nodes
```

### From the Rancher API

```bash
curl -sk -u "$RANCHER_TOKEN:$RANCHER_TOKEN" \
  https://rancher.internal/v3/clusters | jq '.data[] | {name, state}'
```

Expected: `state: "active"` and the node count matching the cluster.

### Post-onboarding verification

```bash
# Verify Fleet integration
kubectl get gitrepo -n fleet-default

# Verify baseline add-ons are synced
kubectl get bundle -n fleet-default

# Check cluster resources
kubectl -n cattle-system get clusters | jq '.data[] | {name, phase, health}'
```

## F. Cross-references

- `management-cluster/rancher/rancher.md` — Rancher deployment
- `management-cluster/rancher/cluster-lifecycle.md` — Cluster upgrade, backup, restore
- `management-cluster/rancher/fleet-integration.md` — Fleet integration
- `lifecycle/disaster-recovery/management-cluster.md` — Management cluster recovery

---
**Rancher Cluster Onboarding**: Importing existing clusters, provisioning new clusters, cluster registration, and validation procedures
**Onboarding Date**: $(date +%Y-%m-%d)
**Registration**: Fully documented with import, provision, and validation procedures
