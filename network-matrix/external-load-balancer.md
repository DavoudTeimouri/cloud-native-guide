# External Load Balancer Architecture

This document describes the external load balancer architecture for the Cloud-Native Stack.

## Overview

Two load balancer nodes in Active/Passive configuration provide HA for ingress traffic.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DMZ / Edge                                │
│                                                                   │
│   ┌─────────────────┐         ┌─────────────────┐               │
│   │   LB Primary    │ ◀────▶ │   LB Standby    │               │
│   │  (Active)       │ VRRP   │  (Standby)      │               │
│   └────────┬────────┘         └────────┬────────┘               │
│            │                           │                          │
│            ▼                           ▼                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Internal Network (10.60.0.0/24)             │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Active/Passive Configuration

### Why Active/Passive

- **Simplicity**: No split-brain risk, no session synchronization complexity
- **Deterministic failover**: VRRP provides sub-second failover
- **L4 load balancing**: MetalLB in layer 2 mode, VIP owned by primary
- **L7 ingress**: NGINX Gateway Fabric runs inside cluster, LB only does L4

### VRRP Configuration

```yaml
# keepalived.conf (primary)
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass <secure-password>
    }
    virtual_ipaddress {
        10.60.0.100/24 dev eth0
    }
}

# keepalived.conf (standby)
vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 90
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass <secure-password>
    }
    virtual_ipaddress {
        10.60.0.100/24 dev eth0
    }
}
```

### MetalLB Integration

```yaml
# MetalLB IPAddressPool
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: production
  namespace: metallb-system
spec:
  addresses:
    - 10.61.0.10-10.61.0.30
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: production
  namespace: metallb-system
spec:
  ipAddressPools:
    - production
```

## TLS Termination

### Options Evaluated

| Option | TLS Termination | Pros | Cons |
|---|---|---|---|
| LB terminates | LB | Simple, central cert management | LB becomes TLS bottleneck |
| Ingress terminates | Ingress controller | End-to-end encryption, cert-manager integration | More complex |
| Passthrough | Backend pods | End-to-end, no cert management at LB | No L7 routing at LB |

**Decision**: Ingress controller terminates TLS. LB passes TCP traffic.

### cert-manager Integration

```yaml
# ClusterIssuer for internal CA
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: internal-ca
spec:
  vault:
    server: https://vault.internal:8200
    path: pki/sign/platform
    auth:
      kubernetes:
        role: cert-manager
        mountPath: /v1/auth/kubernetes
        secretRef:
          name: cert-manager-vault-token
          key: token
```

## HAProxy Alternative

If keepalived + HAProxy is preferred over MetalLB + VRRP:

```haproxy
# haproxy.cfg
global
    log /dev/log local0
    maxconn 4096
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    tcp
    option  tcplog
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000

frontend https_in
    bind *:443
    mode tcp
    default_backend k8s_ingress

backend k8s_ingress
    mode tcp
    balance roundrobin
    option tcplog
    server k8s-cp-1 10.20.0.11:6443 check inter 2000 rise 2 fall 3
    server k8s-cp-2 10.20.0.12:6443 check inter 2000 rise 2 fall 3
    server k8s-cp-3 10.20.0.13:6443 check inter 2000 rise 2 fall 3
```

## Failover Testing

### Test Procedure

1. **Graceful failover**: Stop keepalived on primary → VIP moves to standby
2. **Network partition**: Disconnect primary network → standby takes over
3. **Service impact**: Measure failover time (target < 5 seconds)

### Validation Commands

```bash
# Check VRRP state
ip addr show | grep 10.60.0.100

# Check MetalLB
kubectl get ipaddresspool -n metallb-system
kubectl get l2advertisement -n metallb-system

# Test failover
systemctl stop keepalived  # on primary
# Verify VIP moved to standby
ip addr show | grep 10.60.0.100
```

## Security

- **TLS**: All LB traffic encrypted
- **Authentication**: mTLS between LB and ingress (optional)
- **WAF**: ModSecurity or Coraza on LB (optional)
- **Rate limiting**: HAProxy stick-tables or NGINX rate limiting

## Monitoring

| Metric | Source | Alert |
|---|---|---|
| VRRP state changes | keepalived logs | Alert on unexpected transition |
| VIP availability | ICMP/TCP probe | Alert if VIP unreachable |
| Backend health | MetalLB/HAProxy stats | Alert if all backends down |
| Connection count | LB metrics | Alert if near maxconn |

## References

- [MetalLB Documentation](https://metallb.universe.tf/)
- [keepalived Documentation](https://www.keepalived.org/doc/)
- [HAProxy Documentation](https://www.haproxy.org/documentation.html)

---

*Status: DRAFT | Owner: Network Team | Last reviewed: 2026-11-23*