# DNS Troubleshooting

## Symptoms

- `kubectl` commands hang or fail with "no such host"
- Pods cannot resolve service names
- `dig +short <name>` returns no answer
- `curl` to service DNS name fails with "Could not resolve host"

## Likely causes

- CoreDNS pods not running or crash-looping
- kubelet `--cluster-dns` pointing to wrong address
- `/etc/resolv.conf` on nodes missing cluster DNS entry
- Network policy blocking DNS port (53/TCP, 53/UDP)
- Upstream resolvers unreachable from cluster nodes

## Diagnostic commands

```bash
# Is CoreDNS running?
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system logs -l k8s-app=kube-dns -c coredns

# Can we reach CoreDNS directly?
kubectl run -it --rm debug --image=registry.internal/tools/dnstools:1.0 -- \
  dig @<coredns-ip> kubernetes.default.svc.cluster.local +short

# Is node DNS config correct?
cat /etc/resolv.conf
systemctl status systemd-resolved

# Is DNS port reachable?
nc -zv <coredns-ip> 53
nc -zvu <coredns-ip> 53

# Test from inside a pod
kubectl exec -it <pod> -- cat /etc/resolv.conf
kubectl exec -it <pod> -- dig kubernetes.default.svc.cluster.local +short
```

## Expected healthy state

- CoreDNS pods: Running, 0 restarts
- `dig kubernetes.default.svc.cluster.local +short` returns cluster IP
- `/etc/resolv.conf` contains `nameserver <cluster-dns-ip>`
- `kubectl get --raw='/readyz?verbose'` returns all checks ok

## Remediation

- Restart CoreDNS: `kubectl -n kube-system rollout restart deployment/coredns`
- Fix kubelet `--cluster-dns` flag if nodes point to wrong address
- Update `/etc/resolv.conf` on nodes if missing cluster DNS entry
- Add network policy rule allowing DNS port 53/TCP and 53/UDP
- Verify upstream resolvers in CoreDNS ConfigMap

## Risks

- Restarting CoreDNS briefly interrupts all cluster DNS resolution
- Changing kubelet flags requires node drain and rejoin
- Modifying `/etc/resolv.conf` on nodes is overwritten by cloud-init unless corrected at source

## Verification

```bash
kubectl run -it --rm dns-test --image=registry.internal/tools/dnstools:1.0 -- \
  dig kubernetes.default.svc.cluster.local +short
kubectl run -it --rm dns-test --image=registry.internal/tools/dnstools:1.0 -- \
  dig google.com +short
kubectl get --raw='/readyz?verbose'
```
