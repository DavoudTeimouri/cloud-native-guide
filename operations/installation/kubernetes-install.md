# Kubernetes Install

### Purpose
Deploy Kubernetes cluster via Kubespray with offline images.

### Prerequisites
- Phase 6 storage (or node prep)
- Phase 4 automation ready
- Phase 2 images mirrored to Harbor
- Internal registry configured

### Execution
```bash
# Prepare inventory
cp inventories/production/inventory.ini /opt/kubespray/inventory/production/

# Configure group vars
cp group_vars/k8s_cluster/k8s-cluster.yml /opt/kubespray/inventory/production/group_vars/k8s_cluster/

# Run Kubespray
cd /opt/kubespray
ansible-playbook -i inventory/production/inventory.ini cluster.yml \
  -e container_manager=containerd \
  -e kube_network_plugin=cilium \
  -e kube_version=v1.36.5 \
  -e kubespray_version=v2.32.0 \
  -e container_manager=containerd \
  -e docker_registry=harbor.internal:5000 \
  -e kube_image_repo=harbor.internal/k8s

# Verify
kubectl get nodes
kubectl get pods -A
```

### Validation
- `kubectl get nodes` shows 3 control-plane Ready
- etcd 3/3 healthy
- Control-plane node loss does not interrupt API via VIP
- Worker can be removed/re-added by Kubespray
- No `imagePullBackOff` with internet disabled
- `kubectl get pods -A` all Running/Completed
