# Network Observability Runbook

## Cilium Hubble

### Purpose
Hubble provides network visibility and observability for Cilium-managed clusters. It exposes L3-L7 networking data via eBPF, enabling flow inspection, security policy verification, and troubleshooting.

### Accessing Hubble

```bash
# Port-forward Hubble UI (port 12000)
kubectl -n kube-system port-forward deployment/hubble-ui 12000:12000

# Access at http://localhost:12000

# Or use CLI
kubectl hubble observe
kubectl hubble top
```

### Hubble Commands

| Command | Description |
|---|---|
| `kubectl hubble status` | Check Hubble connectivity and status |
| `kubectl hubble ls` | List observed flows |
| `kubectl hubble watch` | Watch flows in real-time |
| `kubectl hubble resolve <pod>` | Resolve pod IP to node |
| `kubectl hubble ls --oflow <pod>` | Show outbound flows from pod |
| `kubectl hubble ls --iflow <pod>` | Show inbound flows to pod |

### Health Checks

```bash
# Verify Hubble components are running
kubectl -n kube-system get pods -l k8s-app=hubble

# Check Hubble relay
kubectl -n kube-system get pods -l k8s-app=hubble-relay

# Verify eBPF dataplane
kubectl exec -n kube-system daemonset/cilium -- hubble status
```

### Common Hubble Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| No flows displayed | Hubble not enabled or relay disconnected | Enable Hubble: `cilium hubble enable`; check relay connectivity |
| Partial flows | eBPF load limitations or kernel version | Verify kernel version supports required eBPF features; check Cilium pod logs |
| Hubble UI not loading | Port-forward conflict or service not exposed | Ensure port 12000 is free; use `hubble ui` service exposure |

## Flow Logs

### Flow Log Configuration

Flow logs capture network traffic metadata for Cilium-managed pods. They are exported via eBPF and can be shipped to external systems.

### Enable Flow Logs

```bash
# Via CiliumConfig
apiVersion: cilium.io/v2
kind: CiliumConfig
metadata:
  name: default
spec:
  flowLog:
    enabled: true
    aggregation:
      timeout: 30s
    formats:
      - json
    destinations:
      - type: kafka
        broker: kafka.internal:9092
        topic: cilium-flow-logs
      - type: syslog
        address: syslog.internal:514
```

### Flow Log Fields

| Field | Description |
|---|---|
| `timestamp` | Flow start timestamp (RFC3339) |
| `src_ip` | Source pod IP |
| `dst_ip` | Destination pod/IP or service VIP |
| `src_port` | Source port |
| `dst_port` | Destination port |
| `protocol` | IP protocol (tcp/udp/icmp) |
| `packets` | Number of packets in flow |
| `bytes` | Number of bytes in flow |
| `action` | Allow/deny (based on policy) |
| `source_namespace` | Pod namespace |
| `destination_namespace` | Target namespace |

### Troubleshooting Flow Logs

| Issue | Check | Resolution |
|---|---|---|
| No flow logs appearing | Flow log not enabled in CiliumConfig | Enable `flowLog.enabled: true`; verify Cilium restart |
| Logs missing fields | Aggregation timeout too short | Increase `aggregation.timeout`; verify flow completeness |
| Cannot consume logs | Kafka/Syslog destination misconfigured | Verify broker connectivity; check TLS certs; test with `kubectl exec` |
| High cardinality | Too many label combinations | Tighten aggregation rules; reduce label set |

### Verifying Flow Logs

```bash
# Check flow log pod
kubectl -n kube-system get pods -l app=flow-logs

# View recent flow logs from Kafka
kubectl -n kube-system logs -l app=flow-logs -c kafka

# Verify flow log endpoint
curl -s http://localhost:9999/flowlogs | head -20
```

## Connectivity Troubleshooting

### Golden Signals for Network Health

- **Latency** — End-to-end request duration (p99 < 300ms)
- **Errors** — Connection refused, timeout, policy denied (rate < 0.1%)
- **Traffic** — Requests per second, flow volume per namespace
- **Saturation** — eBPF map memory, flow table entries, connection tracking

### Layered Diagnostic Approach

#### Layer 3: Reachability

```bash
# Pod-to-pod connectivity
kubectl exec -it <src-pod> -- ping -c3 <dst-pod-ip>

# Service reachability
kubectl exec -it <pod> -- nc -zv <service> <port>

# Cross-node connectivity
kubectl exec -it <pod> -- ip route get <dst-ip>
```

#### Layer 4: Port & Protocol

```bash
# TCP connect test
kubectl exec -it <src-pod> -- nc -zv <dst-service> <port>

# UDP test
kubectl exec -it <src-pod> -- nc -u -zv <dst-service> <port>

# Port forwarding for inspection
kubectl port-forward svc/<service> <local-port>:<port>
```

#### Layer 5/7: Application Layer

```bash
# HTTP(S) health check
kubectl exec -it <pod> -- curl -sf http://<service>/healthz

# TLS verification
kubectl exec -it <pod> -- openssl s_client -connect <service>:<port> -servername <hostname>

# DNS resolution
kubectl exec -it <pod> -- getent host <service>
```

### Cilium-Specific Commands

```bash
# Endpoint status
cilium endpoint status

# Network policy check
cilium policy get

# Debug connectivity between endpoints
cilium connectivity test --src-ip <src-ip> --dst-ip <dst-ip> --proto tcp

# Verify security identity
cilium identity list

# BPF dataplane check
cilium bpf config dump
```

### Common Connectivity Issues

| Symptom | Root Cause | Verification | Fix |
|---|---|---|---|
| Pods cannot communicate | CNI not ready | `kubectl get daemonset -n kube-system cilium` | Restart Cilium daemonset |
| Connection denied by policy | Network policy blocks traffic | `kubectl get networkpolicy -A`; `cilium policy get` | Adjust policy rules |
| High latency | MTU mismatch or congestion | `ip link show mtu`; `cilium bpf latency` | Lower overlay MTU; investigate hot paths |
| DNS not resolving | CoreDNS not reachable | `nslookup <service> <coredns-ns>` | Check CoreDNS service; verify kube-dns ConfigMap |
| Intermittent drops | Connection tracking table full | `cat /proc/sys/net/nf_conntrack_max`; `cilium bpf conn track show` | Increase conntrack size; optimize flows |

### Automated Connectivity Checks

```bash
# Run Hubble-based connectivity validation
kubectl hubble ls --oneline --oflow <pod> | grep ESTABLISHED

# Check for policy denies
cilium policy list --l7

# Verify service mesh connectivity (if applicable)
kubectl get endpoints <service> -o wide
```

### Runbook Index

- [Cilium Hubble](#cilium-hubble)
- [Flow Logs](#flow-logs)
- [Connectivity Troubleshooting](#connectivity-troubleshooting)