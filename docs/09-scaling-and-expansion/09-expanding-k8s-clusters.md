# Expanding Kubernetes Clusters

## Purpose and scope
Add control-plane and worker nodes to an existing cluster; preserve etcd quorum; one node at a time.

## Steps
1. Add node to inventory ([control-plane]/[etcd] or [k8s-node])
2. Apply OS baseline
3. Run Kubespray limited to new node
4. Verify node Ready; etcd quorum preserved (control plane)

## Implementation
```bash
# Add control-plane node
cat >> inventory/<cluster>/hosts.ini << EOF
[control-plane]
k8s-cp-4 ansible_host=10.20.0.14 ip=10.20.0.14

[etcd]
k8s-cp-4
EOF

ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4

# Add worker node
cat >> inventory/<cluster>/hosts.ini << EOF
[k8s-node]
k8s-w-4 ansible_host=10.30.0.14 ip=10.30.0.14
EOF

ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-4
```

## Rules
- Scale control plane one node at a time to preserve etcd quorum (3 members required)
- Never remove/add more than one control-plane node in a single run
- Verify all remaining nodes Ready before the next change

## Validation
- kubectl get nodes: all Ready
- etcdctl endpoint health --cluster: all healthy

## Related
- [Kubernetes Infrastructure (6.5 Application Cluster Deployment)](../06-kubernetes-infrastructure/6.5-app-cluster-deployment.md)
- [Troubleshooting (08-kubernetes.md)](../08-troubleshooting-and-diagnostics/08-kubernetes.md)
