# Kubespray Migration

### Purpose
Migrate between Kubespray releases.

### Prerequisites
- Backup etcd and Velero
- New Kubespray release tested in staging
- Maintenance window

### Execution
```bash
# Create new inventory from template
cp -r inventory/production inventory/production-new

# Update versions
sed -i 's/kubespray_version=v2.32.0/kubespray_version=v2.33.0/' inventory/production-new/group_vars/k8s_cluster/k8s-cluster.yml
sed -i 's/kube_version=v1.36.5/kube_version=v1.37.0/' inventory/production-new/group_vars/k8s_cluster/k8s-cluster.yml

# Run migration
cd /opt/kubespray
ansible-playbook -i inventory/production-new/inventory.ini cluster.yml \
  -e kube_version=v1.37.0 \
  -e kubespray_version=v2.33.0

# Verify and switch
# Update DNS/load balancer to new control plane IPs if changed
```

### Validation
- All nodes Ready
- etcd healthy
- All pods Running
- No data loss
