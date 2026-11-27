# BGP Peering Configuration

## Overview

This document covers BGP peering configuration for Kubernetes networking using MetalLB in BGP mode. MetalLB provides load-balancer IP addresses for `type: LoadBalancer` services in bare-metal Kubernetes clusters by speaking BGP to edge routers.

## MetalLB BGP Mode

MetalLB operates in two modes:

- **L2 mode**: Uses ARP to assign the VIP on the local segment. No router configuration required.
- **BGP mode**: Announces the VIP via BGP peering with configured routers. Required for routed segments.

BGP mode configuration requires:

- IPAddressPool defining the VIP range
- BGPAdvertisement defining the peering peers
- Router ACLs permitting TCP port 179

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-pool
  namespace: metallb-system
spec:
  addresses:
    - 10.61.0.10-10.61.0.30

apiVersion: metallb.io/v1beta1
kind: BGPAdvertisement
metadata:
  name: default-bgp
  namespace: metallb-system
spec:
  ipAddressPools:
    - default-pool
  peers:
    - my-asn: 64500
      peer-asn: 64500
      peer-address: 10.20.0.1
      peer-port: 179
      my-router-id: 10.20.0.11
      password:
        secretKeyRef:
          name: bgp-credentials
          key: password
```

## BGP Peer Selection

Peer selection determines which routers MetalLB will establish BGP sessions with. Key considerations:

| Factor | Requirement |
|--------|-------------|
| **Peer ASN** | Must match the router's ASN |
| **Peer address** | Must be reachable from the node's network namespace |
| **My router ID** | Typically the node's BGP-facing IP |
| **Password/secret** | Stored in a Kubernetes secret if not plain-text |
| **Port** | Default 179/TCP, configurable per-peer |

Multiple peers can be configured for high availability. MetalLB will attempt to peer with each in order, and will failover if a session drops.

### Peer Configuration Fields

| Field | Description | Required |
|-------|-------------|--------|
| `my-asn` | Local ASN for this BGP speaker | Yes |
| `peer-asn` | Peer router's ASN | Yes |
| `peer-address` | Router's BGP listen address | Yes |
| `peer-port` | TCP port for BGP session | No (default 179) |
| `my-router-id` | Router ID for BGP sessions | Recommended |
| `password` / `password-secret` | Authentication password | Optional, depends on router |

## Route Advertisement

Route advertisement is the process by which MetalLB announces the service VIP over BGP. The `BGPAdvertisement` resource controls this behavior.

### Single vs Multiple Peers

- **Single peer**: One BGP session. If it drops, all VIPs are withdrawn.
- **Multiple peers**: HA setup. MetalLB advertises to all peers; router converges on the best path.

### Route Withdrawal

When a `LoadBalancer` service is deleted, MetalLB withdraws the associated routes. This happens via:

1. Withdraw from all configured peers
2. Wait for router to withdraw its announcement
3. Service EXTERNAL-IP becomes pending until reconfigured

### Advertisement Liveness

MetalLB periodically checks that routes are still advertised. If a peer becomes unreachable, the routes are withdrawn and re-advertised when connectivity is restored.

## BGP Session Health

Monitor BGP session health using MetalLB's built-in metrics and logs.

### Metrics

| Metric | Purpose |
|--------|---------|
| `metallb_bgp_sessions` | Current BGP session states (established, openconfirm, openmessage, etc.) |
| `metallb_bgp_routes_advertised` | Number of routes currently advertised |
| `metallb_bgp_routes_withdrawn` | Number of routes withdrawn |

### Checking Session State

```bash
# View speaker logs for BGP session events
kubectl -n metallb-system logs ds/speaker -f | grep -i "bgp\|session\|peer"

# Check BGPAdvertisement status
kubectl -n metallb-system get bgpadvertisement default-bgp -o yaml

# View MetalLB IP pool and advertisement status
kubectl -n metallb-system get ipaddresspool,ippools,l2advertisements,bgpadvertisements
```

### Healthy Session Indicators

- Sessions transition to `Established` state
- Regular KEEPALIVE messages exchanged
- Routes being advertised and withdrawn as expected
- No log errors about TCP connections or authentication

### Unhealthy Session Signs

- Session stuck in `Idle`, `Connect`, or `OpenConfirm` states
- TCP connection failures (port 179 blocked by firewall)
- Authentication mismatches (password/secret mismatch)
- Route reflector misconfiguration
- AS_PATH or prefix-list filtering on the router

## Troubleshooting Common BGP Issues

### 1. BGP Session Fails to Establish

**Symptoms**: Service EXTERNAL-IP stays pending; logs show connection timeouts.

**Causes and fixes**:

| Cause | Fix |
|-------|-----|
| Router ACL blocking TCP 179 | Allow traffic from node IPs to router peer-address:179 |
| Wrong peer-address in BGPAdvertisement | Verify the router's BGP listen IP; check node routing table |
| ASN mismatch | Confirm `my-asn` and `peer-asn` match router configuration |
| Password/auth mismatch | Check `password` vs secret key; ensure base64 encoding if applicable |
| Node not reachable from router | Verify return path; test with `telnet <peer-address> 179` |

### 2. Routes Not Accepted by Router

**Symptoms**: VIP assigned but externally unreachable; router logs show "prefix filtered" or "AS_PATH too long".

**Causes and fixes**:

| Cause | Fix |
|-------|-----|
| Prefix-list filtering routes | Add the IP pool range to the router's advertised prefix-list |
| AS_PATH policy rejecting routes | Adjust AS_PATH prepend or acceptance policy on the router |
| Maximum-prefix limit exceeded | Increase or disable the router's maximum-prefix threshold |
| Route reflector client misconfig | Ensure MetalLB speakers are configured as clients if using a route reflector |

### 3. Session Drops Intermittently

**Symptoms**: BGP session flaps; traffic blackholes during reconvergence.

**Causes and fixes**:

| Cause | Fix |
|-------|-----|
| Link instability between node and router | Check physical/cable, SFP modules, switch logs |
| Router resource exhaustion (CPU/memory) | Scale router resources; optimize BGP routing table |
| MTU mismatch path MTU discovery issues | Ensure consistent MTU across link; adjust if needed |
| keepalive/holdtimers mismatch | Align `keepalive` and `holdtime` between MetalLB and router |

### 4. VIP Not Reachable After Failover

**Symptoms**: After a node loss, the VIP becomes unreachable.

**Causes and fixes**:

| Cause | Fix |
|-------|-----|
| Single peer without HA | Configure multiple BGP peers for session diversity |
| Router not converging fast enough | Tune router's BGP timers; reduce withdraw/advertise delay |
| ARP cache stale on clients | Clear ARP caches; BGP mode avoids this vs L2 mode |

### 5. MetalLB Speaker Not Announcing

**Symptoms**: No BGP routes visible; speaker pod restarting.

**Causes and fixes**:

| Cause | Fix |
|-------|-----|
| Speaker DaemonSet not scheduled on edge nodes | Use node selectors/affinities to place speaker on edge LB nodes |
| Insufficient IP addresses in pool | Expand the IPAddressPool address range |
| RBAC preventing speaker from advertising | Ensure service account has `metallb.io/speaker` permissions |
| IP conflict in the pool range | Verify no other entity uses addresses from the pool range |

## Commands Summary

```bash
# Install MetalLB with BGP
helm repo add metallb https://metallb.github.io/metallb/charts
helm install metallb metallb/metallb \
  --namespace metallb-system --create-namespace \
  --version 0.16.1

# Create IP pool
kubectl apply -f - <<'EOF'
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-pool
  namespace: metallb-system
spec:
  addresses:
    - 10.61.0.10-10.61.0.30
EOF

# Create BGP advertisement with peers
kubectl apply -f - <<'EOF'
apiVersion: metallb.io/v1beta1
kind: BGPAdvertisement
metadata:
  name: default-bgp
  namespace: metallb-system
spec:
  ipAddressPools:
    - default-pool
  peers:
    - my-asn: 64500
      peer-asn: 64500
      peer-address: 10.20.0.1
      peer-port: 179
      my-router-id: 10.20.0.11
      password:
        secretKeyRef:
          name: bgp-credentials
          key: password
EOF

# Check BGP status
kubectl -n metallb-system get bpga
kubectl -n metallb-system logs ds/speaker | grep -E "BGP|session|peer"

# Test traffic flow
kubectl -n default expose deployment nginx --port=80 --type=LoadBalancer
kubectl -n default get svc nginx
curl http://<EXTERNAL-IP>
```

## Related Documentation

- `kubernetes/networking/metallb.md` — MetalLB installation and basic configuration
- `kubernetes/networking/bgp-ebpf.md` — BGP and eBPF interaction notes
- `network-matrix/port-requirements.md` — Port 179/TCP requirements
- MetalLB official documentation: https://metallb.universe.tf
