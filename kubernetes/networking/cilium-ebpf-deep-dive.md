# Cilium eBPF Deep Dive

## A. XDP (eXpress Data Path)

XDP is the fastest packet processing hook in the Linux kernel, positioned at the network driver's TX ring entry point. Cilium leverages XDP to provide wire-speed networking with sub-microsecond latency.

| Feature | Details |
|---|---|
| **Hook point** | `XDP_DATA`, at driver level, before the kernel network stack |
| **Program type** | `XDP_PROG_TYPE_XDP` — attached via `bpftool` or Cilium agent |
| **Capability** | Drop, redirect, pass-through, generic offload |
| **eBPF program format** | Compiled to BPF bytecode, verified by kernel verifier |
| **Cilium usage** | Packet filtering, port redirect, load distribution across CPUs |

### XDP Flow

```text
NIC driver → XDP hook (program loaded by Cilium) → kernel network stack →
```

XDP programs in Cilium typically implement:
- **Allow/deny filtering** based on BPF maps (IDs, labels)
- **Port redirect** — redirect intercepted traffic to a userspace proxy (CiliumEnvoy)
- **Load distribution** — hash-based distribution across CPUs using `bpf_lxc_load_hash`

### XDP Attachment

```bash
# Load and attach XDP program
sudo bpftool prog load xdp_kern.o /sys/fs/bpf/xdp0 attach xdp

# Via Cilium agent (automatic)
cilium agent run — XDP programs are programs loaded and attached by the agent
```

## B. Load Balancing

Cilium's layer 4 load balancer operates in eBPF, replacing kube-proxy's iptables-based approach. It programs BPF maps for destination NAT and load distribution.

### LB Modes

| Mode | Description | Pros | Cons |
|---|---|---|---|
| **l4-nat** | NAT destination IP to backend pods | Simple, no pod CIDR routing needed | Loses original destination IP |
| **l4-fair** | Per-flow NAT with hash-based distribution | Preserves client IP better | Still NAT, moderate CPU |
| **l4-transparent** | Transparent proxy, no DNAT | Full original IP preservation | Requires IPVS or eBPF redirect |

### LB Architecture

```text
Client → Cilium LB eBPF program → Backend pod (selected by hash)
```

The LB eBPF program maintains:
- **Endpoint maps** — maps service VIP → ready endpoints
- **Connection tracking** — ensures stickiness for existing flows
- **Health checks** — probe endpoints via Hubble or integrated checks

### LB Configuration

```yaml
# CiliumService LB configuration
apiVersion: cilium.io/v2
kind: CiliumService
metadata:
  name: api-service
spec:
  selector:
    app: api
  ports:
    - port: 443
      protocol: TCP
  sessionAffinity: "source-ip"
```

### LB Commands

```bash
# List LB entries
cilium bpf lb list

# Show service load balancing details
kubectl get ciliumservices -A
```

## C. Routing

Cilium implements two primary routing modes: native routing (no encapsulation) and tunnel routing (VXLAN). The mode is selected based on whether the underlay network can route the pod CIDR.

### Native Routing

- **Condition**: Underlay network has routes for the pod CIDR pointing at node IPs
- **Mechanism**: eBPF programs attached to XDP/TC redirect traffic based on destination IP prefix
- **MTU**: Physical MTU (no encapsulation overhead)
- **Requirement**: Router/switch must have pod CIDR routes

### Tunnel Routing (VXLAN)

- **Condition**: Underlay cannot route pod CIDR, or multi-cluster connectivity needed
- **Mechanism**: VXLAN encapsulation, VTEP tunnel endpoints in the kernel
- **MTU**: Physical MTU - 50 (VXLAN header overhead)
- **Encapsulation**: UDP port 4789

### Route Resolution

```text
Pod IP → eBPF routing lookup → Node IP (native) or VXLAN tunnel (encapsulated)
```

### Routing Commands

```bash
# Check routing mode
cilium status --verbose

# Show BPF programs related to routing
cilium bpf endpoint list

# Verify native routing
ip route show <pod-cidr>
```

## D. NAT

Cilium provides several NAT modes for service exposure and pod connectivity. The NAT mode is configured per-cluster and affects both service load balancing and pod egress.

### Service NAT (l4-nat mode)

- **Destination NAT**: VIP → backend pod IP:port
- **Source NAT**: Optional masquerade for pod egress
- **Masquerade**: `bpf.masquerade=true` — uses eBPF for fast MASQUERADE, avoids iptables overhead

### Egress NAT

- **Default**: No egress NAT; pods use pod IP directly
- **With masquerade**: All pod egress goes through the node's external IP
- **Use case**: When pod IP space cannot be routed on the underlay

### NAT Configuration

```yaml
# BPF masquerade setting
--set bpf.masquerade=true

# Verify masquerade
cilium bpf nat list
iptables -t nat -L -n -v
```

### NAT Performance

- **eBPF NAT**: Near-line speed, minimal CPU overhead compared to iptables
- **Connection tracking**: Stored in BPF maps, not kernel conntrack table
- **Scale**: Millions of concurrent connections possible with sufficient BPF map size

## E. Performance Considerations

### Key Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Packet processing latency** | < 10µs per hop | `perf stat`, `bpftrace` |
| **CPU overhead per Gbps** | < 1% eBPF overhead | `pidstat`, `mpstat` |
| **Connection setup rate** | > 1M conn/s | `haproxy`, custom benchmark |
| **BPF map lookup latency** | < 1µs | `bpftool map dump` |

### Performance Tuning

| Tuning knob | Effect | Recommended value |
|---|---|---|
| **BPF map size** | Affects lookup performance, memory usage | `map_entries` ≥ expected concurrent connections × 2 |
| **XDP mode** | `XDP_PASS`, `XDP_DROP`, `XDP_REDIRECT` | Use `XDP_REDIRECT` for LB, `XDP_DROP` for deny |
| **Program complexity** | Verifier rejection risk, runtime performance | Keep XDP programs under 4KB BPF instructions |
| **CPU pinning** | Ensures LB programs run on dedicated cores | Pin Cilium agent pods to separate CPU set |

### Common Performance Pitfalls

1. **XDP attachment failure** — Ensure kernel supports XDP on the device; check `dmesg` for attachment errors
2. **BPF verifier rejects program** — Reduce instruction count, use BTF for type safety
3. **BPF map contention** — High concurrency on a single map; shard maps by CPU/core
4. **MTU mismatches** — VXLAN: physical MTU - 50; native: physical MTU; verify with `ping -M do -s <size> <dest>`
5. **CPU saturation** — eBPF programs run in interrupt context; monitor `softirq` and `si` steal

### Verification Commands

```bash
# Check BPF program loads and CPU attachment
cilium bpf lb list

# Show XDP program stats
sudo bpftool prog info /sys/fs/bpf/xdp0

# Monitor eBPF performance
perf stat -e cpu-clock,cache-references,cache-misses sudo cilium bpf lb list

# Check map sizes and utilization
cilium bpf map list
```

## F. Cross-References

- [`cilium.md`](cilium.md) — Cilium CNI deployment overview
- [`../../network-matrix/external-load-balancer.md`](../../network-matrix/external-load-balancer.md) — External load balancer and MetalLB integration
- [`../../network-matrix/network-communication-matrix.md`](../../network-matrix/network-communication-matrix.md) — Inter-pod communication patterns and topology
- [`../../network-matrix/port-requirements.md`](../../network-matrix/port-requirements.md) — Required ports for Cilium eBPF features
- [`../../decisions/ADR-0006-cni-selection.md`](../../decisions/ADR-0006-cni-selection.md) — CNI selection rationale (Cilium chosen)