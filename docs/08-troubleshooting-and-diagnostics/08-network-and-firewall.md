# Network and Firewall

## Symptoms
- Service unreachable from another node/cluster
- VIP failover not occurring
- Port unreachable from remote host
- Load balancer not distributing traffic
- Cross-node pod communication failing

## Possible causes
- Firewall blocking required port
- Security group / network policy denying traffic
- VIP misconfigured or not floating
- Route missing between segments
- CNI misconfiguration (VXLAN, MTU)

## Diagnostic commands
```bash
# Connectivity
ping -c 3 <target-ip>
nc -zv <target> <port>
curl -vk https://<target>:<port>

# Routes
ip route get <target-ip>
ip addr show

# Firewall (nftables/nft)
nft list ruleset
firewall-cmd --list-all   # firewalld
ufw status               # Ubuntu

# VIP
ip addr show | grep <vip>
keepalived status

# CNI
kubectl get pods -n kube-system -l k8s-app=cilium
cilium status
cilium connectivity test
```

## Expected output
- ping: 0% packet loss
- nc: open port
- curl: HTTP 200 / TLS handshake
- nft: rules present allowing traffic
- ip addr: VIP present on active node
- cilium: KubeProxyReplacement true, connectivity test pass

## Investigation procedure
1. Test basic L3 reachability (ping)
2. Test L4 reachability (nc/curl) to target port
3. Check firewall ruleset for allow rule
4. Verify route to target segment
5. Verify VIP on correct node (keepalived)
6. Check CNI status and connectivity test

## Resolution
- Add missing firewall allow rule
- Correct VIP assignment / failover configuration
- Add missing route
- Fix CNI configuration (VXLAN, MTU, kube-proxy replacement)

## Verification
- ping 0% loss; nc open; curl HTTP 200; cilium connectivity test pass; VIP on active node

## Prevention
- Automate firewall rules from network matrix
- Monitor VIP ownership; alert on failover
- Monitor CNI health; alert on connectivity test failure

## Related
- [Shared network matrix](../shared/network-matrix/index.md)
- [Load Balancers and Traffic Management](../05-load-balancers/index.md)
