# Network Troubleshooting

## Symptoms

- Pods cannot communicate across nodes
- Service endpoints not reachable
- `ping -c3 <target-ip>` returns 100% loss
- `nc -zv <target> <port>` connection refused or timeout
- `curl -vk https://<target>` hangs

## Likely causes

- CNI plugin not running or misconfigured
- Network policy blocking traffic
- Security group or firewall rules dropping packets
- MTU mismatch between overlay and underlay
- Node IP not in pod CIDR range
- IP forwarding disabled on nodes

## Diagnostic commands

```bash
# Layer 3: Is target reachable at all?
ping -c3 <target-ip>

# Layer 4: Is port open?
nc -zv <target> <port>

# Layer 5/7: Is service responding?
curl -vk https://<target>

# CNI status
kubectl get daemonset -n kube-system -l k8s-app=cilium
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent

# Node IP forwarding
cat /proc/sys/net/ipv4/ip_forward

# MTU
ip link show | grep mtu
ip route show

# Network policies
kubectl get networkpolicy -A

# Routes
ip route get <target-ip>
```

## Expected healthy state

- `ping -c3 <target-ip>` returns 0% loss
- `nc -zv <target> <port>` reports "Connection succeeded"
- `ip_forward` = 1 on all nodes
- CNI daemonset pods all Running
- No network policies blocking the path

## Remediation

- Restart CNI daemonset: `kubectl -n kube-system rollout restart daemonset/cilium`
- Fix network policy rules blocking the traffic
- Update security group/firewall rules
- Correct MTU mismatch (lower overlay MTU to match underlay)
- Enable IP forwarding: `sysctl -w net.ipv4.ip_forward=1`
- Verify node IP is within configured pod CIDR

## Risks

- Changing MTU can cause temporary connectivity loss
- Removing network policies exposes services to unintended traffic
- Changing firewall rules can lock out management access

## Verification

```bash
ping -c3 <target-ip>
nc -zv <target> <port>
curl -sf https://<target> && echo "OK"
kubectl get --raw='/readyz?verbose'```
