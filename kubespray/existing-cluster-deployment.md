# Existing cluster expansion (join / scale)

[Previous step](../storage/ceph/cephadm-deployment.md) | [Next step](../management-cluster/rancher/rancher.md)

---

## A. Purpose and scope

This document describes joining **new worker nodes** to an already-running Kubernetes cluster. No control-plane reinstall; only worker nodes are added.

Two supported paths:

| Path | When to use |
|------|-------------|
| **kubeadm join** | Cluster was bootstrapped with kubeadm; single new nodes or small batches |
| **kubespray scale playbook** | Cluster was deployed with Kubespray; many new nodes, or need idempotent inventory-driven scale |

## B. Prerequisites

### Existing cluster must have

- Healthy control plane (all API servers ready, etcd quorum)
- Reachable Kubernetes API endpoint (VIP or load balancer)
- `kubeadm` token or certificate rotation capability for new nodes
- Same Kubernetes **minor version** on control plane and new nodes (e.g. both 1.36.x)

### New nodes must have

| Item | Requirement |
|------|-------------|
| OS | Same OS family and version as existing nodes (Ubuntu 24.04 / OL9 / Rocky 9) |
| Container runtime | containerd configured with the **same** internal registry mirror |
| CNI | Cilium (or Calico) binaries and config matching the cluster |
| kubelet | Same version pin as control plane (`v1.36.x`) |
| Network | Can reach API server VIP and all pod/service CIDRs |
| Host baseline | `automation/ansible` playbooks applied (kernel, chrony, firewall, etc.) |

## C. Path 1 — kubeadm join (single or few nodes)

### 1. Generate join token on control plane

```bash
# On any control-plane node
kubeadm token create --print-join-command --ttl=24h
# Output example:
# kubeadm join 10.20.0.100:6443 --token abcdef.0123456789abcdef \
#   --discovery-token-ca-cert-hash sha256:abcd...
```

### 2. Prepare new node

```bash
# On the new node (as root)
# 1. Install same kubelet/kubeadm/kubectl version
yum install -y kubelet-1.36.5 kubeadm-1.36.5 kubectl-1.36.5 --disableexcludes=kubernetes

# 2. Configure containerd with internal registry mirror
cat > /etc/containerd/config.toml <<'EOF'
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.internal"]
  endpoint = ["https://harbor.internal"]
EOF
systemctl restart containerd

# 3. Install CNI binaries (Cilium)
cilium install --version 1.20.3

# 4. Run join command from step 1
kubeadm join 10.20.0.100:6443 --token abcdef.0123456789abcdef \
  --discovery-token-ca-cert-hash sha256:abcd...
```

### 3. Verify

```bash
kubectl get nodes -o wide
kubectl wait --for=condition=Ready node/<new-node-name> --timeout=5m
```

## D. Path 2 — Kubespray scale playbook (many nodes, idempotent)

### 1. Update inventory

Add new worker nodes to `kubespray/inventory/<cluster>/hosts.ini`:

```ini
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11 ip=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12 ip=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13 ip=10.20.0.13

[etcd]
k8s-cp-1
k8s-cp-2
k8s-cp-3

[kube-node]
k8s-w-1 ansible_host=10.20.0.21 ip=10.20.0.21
k8s-w-2 ansible_host=10.20.0.22 ip=10.20.0.22
# NEW NODES BELOW
k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23
k8s-w-4 ansible_host=10.20.0.24 ip=10.20.0.24
```

### 2. Run scale playbook

```bash
cd kubespray
# Use the same virtualenv as the original deploy
source .venv/bin/activate

# Limit to new nodes only (scale playbook is idempotent on existing)
ansible-playbook -i inventory/<cluster>/hosts.ini scale.yml \
  --limit "k8s-w-3,k8s-w-4" \
  -e "ansible_user=ansible"
```

The `scale.yml` playbook:
- Runs host baseline on new nodes only
- Joins them to the existing cluster
- Does **not** touch control plane or existing workers

### 3. Verify

```bash
kubectl get nodes -o wide
# New nodes should show Ready
```

## E. Version matrix

This method uses the same Kubespray releases as the standard Kubespray path. The `kubesprayRelease` value in the guide answers must match the release that built the existing cluster. See `compatibility/version-matrix.md` and the "Kubespray → Kubernetes / etcd" matrix on the Deployment page.

| Constraint | Rule |
|------------|------|
| Kubernetes minor | New nodes **must** match control plane minor (1.36.x → 1.36.x) |
| Kubespray release | Must match the release used for the original deploy |
| containerd | Same version as cluster (pinned by Kubespray release) |
| CNI | Same CNI and version as cluster |

## F. Adding specialized node types

| Node type | Additional steps |
|-----------|------------------|
| **GPU workers** | Install NVIDIA driver + GPU Operator on new nodes before join; label `nvidia.com/gpu.present=true` |
| **Edge workers** | Add to `edge` group in inventory; MetalLB/keepalived config may need update |
| **Ceph OSD** | Not via this path — use cephadm or Rook to add OSDs to storage cluster separately |

## G. Replacing a failed worker

1. Cordon & drain the failed node: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`
2. Delete node: `kubectl delete node <node>`
3. Re-provision replacement with same IP/hostname (or new IP, update inventory)
4. Join via kubeadm or kubespray scale as above

## H. Rollback

- kubeadm join: `kubeadm reset` on the new node, then re-join
- kubespray scale: Re-run scale playbook; it's idempotent

---

**Source of truth**: This document + `kubespray/scale.yml` + `compatibility/version-matrix.md` + guide bundle scripts.