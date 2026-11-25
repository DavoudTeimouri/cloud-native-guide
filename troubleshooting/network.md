# Network Troubleshooting

## Common Issues

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

### Service Connectivity Issues

**Symptoms**: Pods cannot reach services.

**Likely Causes**:
- Service not created or selector mismatch
- Endpoints not populated
- NetworkPolicy blocking traffic
- CNI not working
- kube-proxy not running

**Diagnosis**:
```bash
kubectl get svc -A
kubectl get endpoints -A
kubectl get endpoints <svc> -n <ns>
kubectl get pods -n kube-system -l k8s-app=kube-proxy
kubectl exec -it <pod> -- curl -v <svc>.<ns>.svc.cluster.local
```

**Resolution**:
- Verify service selector matches pod labels
- Check NetworkPolicy rules
- Restart kube-proxy if needed
- Check CNI pods status

### MetalLB Issues

**Symptoms**: LoadBalancer services stuck in Pending.

**Likely Causes**:
- MetalLB not installed/configured
- IPAddressPool exhausted
- L2Advertisement not configured
- Speaker pods not running

**Diagnosis**:
```bash
kubectl get ipaddresspool -n metallb-system
kubectl get l2advertisement -n metallb-system
kubectl get pods -n metallb-system
kubectl describe svc <svc> -n <ns>
```

**Resolution**:
- Verify IPAddressPool has available IPs
- Check L2Advertisement configuration
- Ensure speaker pods are running on worker nodes

### CNI Issues (Cilium)

**Symptoms**: Pod network connectivity broken.

**Likely Causes**:
- Cilium pods not ready
- BPF maps full
- MTU mismatch
- BPF filesystem not mounted

**Diagnosis**:
```bash
kubectl get pods -n kube-system -l k8s-app=cilium
cilium status
cilium bpf lb list
cilium bpf policy get
```

**Resolution**:
- Restart Cilium pods
- Check MTU settings (underlay MTU >= overlay MTU + 50)
- Ensure BPF filesystem mounted: `mount | grep bpf`

---

*Status: DRAFT | Owner: Network Team | Last reviewed: 2026-11-23*