# BGP and eBPF Networking

## A. Purpose and scope

Document BGP peering and eBPF datapath considerations for the platform network. Cilium uses eBPF for pod networking and service load balancing; MetalLB uses BGP for external load balancer peering.

## B. BGP (MetalLB)

MetalLB speaks BGP to edge routers to announce service IPs. The platform uses BGP peering on port 179/TCP.

### BGP configuration

| Item | Value |
|------|-------|
| BGP peer port | 179/TCP |
| MetalLB speaker | DaemonSet on edge LB nodes |
| BGP router ID | Node IP |
| ASN | Per-environment (internal ASN) |
| Peer ASN | Edge router ASN |

### BGP ports

Refer to `network-matrix/port-requirements.md` — Edge LB node ↔ MetalLB peers on 179/TCP.

### Failure scenarios

| Scenario | Effect | Recovery |
|----------|--------|----------|
| BGP session down | Edge LB stops announcing service IPs; external traffic blackholes | Check BGP peer config, router ACLs, session state |
| MetalLB speaker not running | No service IP announcement | Restart speaker daemonset |
| Route not accepted by router | Service IP unreachable externally | Check route filters, prefix lists, AS_PATH |

## C. eBPF (Cilium)

Cilium's eBPF datapath replaces iptables-based kube-proxy with XDP/TC-attached BPF programs.

### eBPF requirements

| Item | Requirement |
|------|-------------|
| Kernel | >= 4.19 (5.4+ recommended) |
| Mounts | bpffs at /sys/fs/bpf, debugfs |
| Privileges | NET_ADMIN, SYS_MODULE |
| BTF | Optional, required for some features |

### eBPF failure scenarios

| Scenario | Effect | Recovery |
|----------|--------|----------|
| Kernel too old | Cilium agent fails to start | Upgrade kernel or use Calico fallback |
| bpffs not mounted | eBPF programs cannot load | Mount bpffs: `mount bpffs /sys/fs/bpf -t bpf` |
| BTF missing | Some eBPF features unavailable | Install kernel debuginfo packages |
| eBPF verifier rejects program | Cilium datapath broken | Check kernel version, reduce program complexity |

### Verification

```bash
# Check bpffs mounted
mount | grep bpf

# Check Cilium status
kubectl -n kube-system get pods -l k8s-app=cilium
cilium status

# Check eBPF programs loaded
cilium bpf lb list
cilium bpf policy list

# Check Hubble
cilium hubble status
```

## D. Cross-references

- `kubernetes/networking/cilium.md` — Cilium CNI deployment
- `decisions/ADR-0006-cni-selection.md` — CNI selection (Cilium)
- `network-matrix/port-requirements.md` — Port 179/TCP for BGP
- `network-matrix/cloud-native-dmz.md` — DMZ architecture
