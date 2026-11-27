# CNI

## Symptoms
- Pod cannot reach another pod (cross-node)
- Pod cannot reach service (ClusterIP)
- DNS resolution from pod failing
- Node not Ready due to CNI not ready
- cilium-agent crash-looping

## Possible causes
- CNI plugin not installed or misconfigured
- kube-proxy replacement not active (strict mode)
- VXLAN port (UDP 8472) blocked by firewall
- MTU mismatch between underlay and overlay
- Hubble/relay not running
- Node not Ready so CNI not deployed

## Diagnostic commands
```bash
# CNI status
kubectl get pods -n kube-system -l k8s-app=cilium
kubectl get daemonset cilium-agent -n kube-system
cilium status
cilium connectivity test

# Firewall (VXLAN UDP 8472)
nc -zv <node-ip> 8472 -u
nft list ruleset | grep 8472

# Routes
ip route show
ip -6 route show

# MTU
ip link show cilium_host
ip link show eth0
```

## Expected output
- cilium: KubeProxyReplacement true; connectivity test pass
- nc: UDP 8472 open between nodes
- ip route: cilium_host routes present
- MTU: cilium_host MTU = underlay MTU − 50 (VXLAN)

## Investigation procedure
1. Check cilium-agent daemonset status on all nodes
2. Run cilium status and cilium connectivity test
3. Test VXLAN UDP 8472 between nodes
4. Check MTU mismatch (cilium_host vs eth0)
5. Check kube-proxy replacement status

## Resolution
- Restart cilium-agent daemonset
- Open firewall UDP 8472 between nodes
- Correct MTU mismatch
- Fix Cilium config (IPAM, tunneling mode, kube-proxy replacement)

## Verification
- cilium status: KubeProxyReplacement true; connectivity test all pass
- Pod cross-node communication works; DNS from pod works

## Prevention
- Automate Cilium config from templates; monitor agent health
- Monitor VXLAN port reachability between nodes
- Monitor MTU consistency

## Related
- [06 · Kubernetes Infrastructure (6.9 Kubernetes Networking)](../06-kubernetes-infrastructure/6.9-kubernetes-networking.md)
- [Shared network matrix](../shared/network-matrix/index.md)
