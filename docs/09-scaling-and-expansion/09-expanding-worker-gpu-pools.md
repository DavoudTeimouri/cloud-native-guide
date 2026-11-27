# Expanding Worker & GPU Pools

## Purpose and scope
Expand general and GPU worker pools; node labels/taints, MIG, scheduling.

## Steps
1. Add worker nodes to inventory ([k8s-node] or [gpu-node])
2. Apply OS baseline with GPU drivers if GPU node
3. Run Kubespray limited to new nodes
4. Verify nodes Ready; apply labels/taints

## GPU worker specifics
- NVIDIA H100/H200, driver + CUDA
- MIG for production multi-tenancy; time-slicing for dev
- Node Feature Discovery; GPU Operator

## Implementation
```bash
# Add GPU worker
cat >> inventory/<cluster>/hosts.ini << EOF
[gpu-node]
k8s-gpu-2 ansible_host=10.50.0.12 ip=10.50.0.12 labels='{"accelerator":"nvidia"}'
EOF

ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-gpu-2

# Verify GPU
kubectl get nodes k8s-gpu-2
kubectl get nodes -o wide | grep gpu
nvidia-smi  # on node
```

## Validation
- New nodes Ready; GPU visible via nvidia-smi
- Node Feature Discovery labels present
- GPU Operator managing devices

## Related
- [Kubernetes Infrastructure (6.10 Add-ons)](../06-kubernetes-infrastructure/6.11-kubernetes-add-ons.md) - GPU Operator
- [Kubernetes Infrastructure (6.2 Best Practices)](../06-kubernetes-infrastructure/6.1-kubernetes-architecture.md) - node selectors/taints
