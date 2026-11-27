# OS Migration

### Purpose
Migrate OS to newer major version (e.g., OL8 to OL9, Ubuntu 22.04 to 24.04).

### Prerequisites
- Node drained (if worker)
- Velero backup of workloads
- New OS image available in internal registry
- Maintenance window

### Execution
```bash
# Rebuild node with new OS image
# 1. Drain node
kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data

# 2. Re-provision via Ansible
ansible-playbook -i inventory/production/inventory.ini playbooks/os-reprovision.yml -l $NODE

# 3. Rejoin cluster
# Kubespray handles this automatically if node name/IP unchanged
ansible-playbook -i inventory/production/inventory.ini cluster.yml -l $NODE

# 4. Uncordon
kubectl uncordon $NODE
```

### Validation
- Node rejoins cluster
- All pods Running
- No alerting