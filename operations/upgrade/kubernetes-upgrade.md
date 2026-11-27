# Kubernetes Upgrade

### Purpose
Upgrade Kubernetes minor version via Kubespray.

### Prerequisites
- Current cluster healthy
- Backup etcd and Velero completed
- New Kubespray release compatible with target Kubernetes version

### Execution
```bash
# Update Kubespray version in inventory
sed -i 's/kubespray_version=v2.32.0/kubespray_version=v2.33.0/' inventory/production/group_vars/k8s_cluster/k8s-cluster.yml
sed -i 's/kube_version=v1.36.5/kube_version=v1.37.0/' inventory/production/group_vars/k8s_cluster/k8s-cluster.yml

# Run upgrade
cd /opt/kubespray
ansible-playbook -i inventory/production/inventory.ini upgrade-cluster.yml \
  -e kube_version=v1.37.0 \
  -e kubespray_version=v2.33.0

# Verify
kubectl get nodes
kubectl get pods -A
```

### Validation
- All nodes Ready
- etcd healthy
- All pods Running/Completed
- No API downtime during upgrade