# Kubernetes

## Symptoms
- Pod not scheduling / Pending
- Node NotReady
- Control plane API unreachable
- etcd quorum lost
- CrashLoopBackOff
- DNS resolution from pod failing

## Possible causes
- Insufficient resources (CPU/memory/disk)
- Node taint not tolerated by pod
- kubelet not running or misconfigured
- etcd member down / quorum lost
- API server certificate expired
- CNI misconfigured / node not Ready
- Image pull failure (auth, network, image missing)

## Diagnostic commands
```bash
# Cluster state
kubectl get nodes
kubectl get pods -A
kubectl get events --sort-by=.lastTimestamp
kubectl describe pod <pod>

# Control plane
kubectl get --raw='/readyz?verbose'
kubectl get --raw='/healthz'
etcdctl endpoint health --cluster \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key

# Node
kubectl describe node <node>
ssh <node> 'systemctl status kubelet; journalctl -u kubelet -n 50'
ssh <node> 'crictl info'

# Image
kubectl describe pod <pod> | grep -A5 Events
skopeo inspect docker://<image>
```

## Expected output
- kubectl get nodes: all Ready
- readyz: all ok
- etcdctl: all healthy
- kubelet: active (running)
- crictl: runtime info returned
- skopeo: manifest digest returned

## Investigation procedure
1. Check kubectl get nodes and pods; identify failing pod/node
2. Check readyz and etcd health for control plane issues
3. Check kubelet status on affected node
4. Check pod events for image pull/scheduling errors
5. Check CNI status if networking failing

## Resolution
- Add resources or tolerate taints; restart kubelet
- Replace failed control-plane node (one at a time to preserve quorum)
- Restore etcd from snapshot if quorum lost
- Fix image pull secret or image tag; ensure image in internal Harbor
- Fix CNI configuration; restart cilium-agent

## Verification
- All nodes Ready; all pods Running; readyz all ok; etcd healthy

## Prevention
- Monitor node/pod health; alert on NotReady
- Monitor etcd quorum; alert on member down
- Monitor certificate expiry; auto-renew via cert-manager
- Ensure images mirrored to internal Harbor; pin by digest

## Related
- [06 · Kubernetes Infrastructure](../06-kubernetes-infrastructure/index.md)
- [08 · Troubleshooting (08-cni.md)](08-cni.md)
- [08 · Troubleshooting (08-csi.md)](08-csi.md)
