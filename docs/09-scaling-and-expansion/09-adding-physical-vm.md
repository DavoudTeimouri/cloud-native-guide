# 09 · Adding Physical Servers & VMs

## Purpose and scope
Add physical servers and VMs to the stack: hardware/VM prep, OS baseline, join to cluster.

## Steps
1. Provision hardware/VM (PXE, template, cloud-init)
2. Apply OS baseline (role-specific)
3. Join to Kubernetes cluster (Kubespray)
4. Verify node Ready; apply labels/taints

## Prerequisites
- Internal OS mirror reachable
- Internal CA certificate trusted
- SSH access for Ansible user
- Inventory updated with new host

## Implementation
```bash
# Add to inventory
cat >> inventory/<cluster>/hosts.ini << EOF
[control-plane]
k8s-cp-4 ansible_host=10.20.0.14 ip=10.20.0.14

[etcd]
k8s-cp-4
EOF

# Deploy Kubespray limited to new node
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4

# Verify
kubectl get nodes k8s-cp-4
kubectl -n kube-system get pods -l component=etcd --field-selector spec.nodeName=k8s-cp-4
```

## Validation
- Node Ready in kubectl get nodes
- etcd member healthy
- Pods scheduling to new node

## Related
- [02 · Operating Systems (2.5 OS Preparation by Role)](../02-components/2.5-os-prep-by-role.md)
- [06 · Kubernetes Infrastructure (6.5 Application Cluster Deployment)](../06-kubernetes-infrastructure/6.5-app-cluster-deployment.md)
