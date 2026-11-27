# Kubernetes Troubleshooting

This runbook covers common Kubernetes issues and their resolutions.

## Common Issues

### API Server Unavailable

**Symptoms**: `kubectl` commands timeout or return connection refused.

**Likely Causes**:
- Control plane nodes down
- etcd quorum lost
- kube-apiserver pod crashed
- Network partition

**Diagnosis**:
```bash
# Check control plane pods
kubectl get pods -n kube-system | grep -E "apiserver|controller|scheduler|etcd"

# Check etcd health
kubectl exec -n kube-system etcd-<node> -- etcdctl endpoint health --cluster

# Check kubelet logs
journalctl -u kubelet -f
```

**Resolution**:
- Restart failed control plane pods
- Restore etcd quorum if lost
- Check network connectivity between control plane nodes

### Pods Stuck in Pending

**Symptoms**: Pods remain in `Pending` state indefinitely.

**Likely Causes**:
- Insufficient resources (CPU, memory, GPU)
- PVC not bound (storage class missing, PVC unbound)
- Node selector/affinity not matching
- Taints/tolerations mismatch
- Scheduler not running

**Diagnosis**:
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl describe node <node-name>
```

**Resolution**:
- Add resources or scale cluster
- Check storage class and PVC binding
- Verify node selectors/affinity/taints
- Ensure scheduler is running

### Pods Stuck in ContainerCreating

**Symptoms**: Pods stuck in `ContainerCreating` state.

**Likely Causes**:
- Image pull failure (wrong registry, auth, image not found)
- CNI not ready (pod network not configured)
- Volume mount failure (PVC not bound, mount path issue)
- Runtime error (containerd/cri-o issue)

**Diagnosis**:
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> -c <container>
crictl ps -a
crictl logs <container-id>
```

**Resolution**:
- Verify image exists in registry and credentials correct
- Check CNI pods (Cilium/Calico/Flannel) are Running
- Verify PVC bound and volume mount paths correct
- Restart container runtime if needed

### Node NotReady

**Symptoms**: Node status shows `NotReady`.

**Likely Causes**:
- Kubelet not running
- Disk pressure
- Memory pressure
- PID pressure
- Network partition
- Kubelet certificate expired

**Diagnosis**:
```bash
kubectl describe node <node-name>
systemctl status kubelet
df -h /
free -h
ps aux | grep kubelet
```

**Resolution**:
- Restart kubelet: `systemctl restart kubelet`
- Free disk/memory space
- Renew kubelet certificates if expired
- Check network connectivity to API server

### DNS Resolution Failures

**Symptoms**: Pods cannot resolve service names.

**Likely Causes**:
- CoreDNS pods down
- Upstream DNS servers unreachable
- NetworkPolicy blocking DNS
- CoreDNS configmap incorrect

**Diagnosis**:
```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
kubectl exec -it <pod> -- nslookup kubernetes.default.svc.cluster.local
```

**Resolution**:
- Restart CoreDNS pods: `kubectl rollout restart deployment/coredns -n kube-system`
- Check upstream DNS in CoreDNS configmap
- Verify NetworkPolicy allows DNS traffic

## Troubleshooting Commands Reference

```bash
# Cluster overview
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events --sort-by=.metadata.creationTimestamp

# Node diagnostics
kubectl describe node <node>
ssh <node> "journalctl -u kubelet -f"
ssh <node> "crictl ps -a"

# Pod diagnostics
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns> --previous
kubectl exec -it <pod> -n <ns> -- /bin/sh

# Network diagnostics
kubectl run nettest --rm -it --image=nicolaka/netshoot -- /bin/bash
kubectl exec -it <pod> -- nslookup <service>.<namespace>.svc.cluster.local

# Storage diagnostics
kubectl get pvc -A
kubectl describe pvc <pvc> -n <ns>
kubectl get pv
ceph -s  # if using Ceph

# Certificate issues
kubectl get csr
kubectl certificate approve <csr-name>
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -text -noout
```

## Log Locations

| Component | Log Location |
|---|---|
| kubelet | `journalctl -u kubelet` |
| kube-apiserver | `/var/log/pods/kube-system_kube-apiserver-*/kube-apiserver/*.log` |
| kube-controller-manager | `/var/log/pods/kube-system_kube-controller-manager-*/kube-controller-manager/*.log` |
| kube-scheduler | `/var/log/pods/kube-system_kube-scheduler-*/kube-scheduler/*.log` |
| etcd | `journalctl -u etcd` or `/var/log/etcd/` |
| kube-proxy | `journalctl -u kube-proxy` |
| container runtime | `journalctl -u containerd` or `/var/log/containers/*.log` |
| CNI (Cilium) | `cilium logs` or `kubectl logs -n kube-system -l k8s-app=cilium` |
| CoreDNS | `kubectl logs -n kube-system -l k8s-app=kube-dns` |

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*