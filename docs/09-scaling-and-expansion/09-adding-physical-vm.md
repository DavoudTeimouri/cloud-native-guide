# Adding Physical Servers & VMs

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

- [Operating Systems (2.5 OS Preparation by Role)](../02-components/2.5-os-prep-by-role.md)
- [Kubernetes Infrastructure (6.5 Application Cluster Deployment)](../06-kubernetes-infrastructure/6.5-app-cluster-deployment.md)

## Automation: scaling playbook

Add nodes via Terraform + Ansible:

```bash
# 1. Provision VM via Terraform
cd automation/terraform
terraform apply -var-file=terraform.tfvars -target=vsphere_virtual_machine.new_node -auto-approve
terraform output new_node_ips

# 2. Add node to Ansible inventory
cat >> automation/ansible/inventories/production/hosts.ini << EOF
[k8s-workers]
k8s-worker-<N> ansible_host=<new_node_ip> ip=<new_node_ip>
EOF

# 3. Apply OS baseline via Ansible
ansible-playbook -i automation/ansible/inventories/production/hosts.ini \
  automation/ansible/playbooks/os-prep-worker.yml --limit k8s-worker-<N>

# 4. Join to Kubernetes via Kubespray
ansible-playbook -i automation/ansible/inventories/production/hosts.ini \
  automation/ansible/playbooks/kubernetes.yml --limit k8s-worker-<N>

# 5. Verify
kubectl get nodes k8s-worker-<N>
kubectl -n kube-system get pods -o wide | grep k8s-worker-<N>
```

**Inventory update** — After `terraform output new_node_ips`, add the IPs to `automation/ansible/inventories/production/hosts.ini` under the correct group (`k8s-workers`, `control-plane`, `etcd`, `ceph-nodes`, `lb-nodes`).

**Customization variables** (`automation/ansible/group_vars/all/main.yml` and `automation/terraform/terraform.tfvars`) — see sections 2.4 and 2.5.
