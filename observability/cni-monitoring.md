# CNI Monitoring

## Monitoring Spec Table

| Aspect | Details |
|---|---|
| **Health** | CNI plugin agent health; endpoint connectivity; policy enforcement; IPAM address space availability; BPF program integrity; Hubble flow visibility |
| **Metrics** | `hubble_observability_flow_sent_total`, `hubble_observability_flow_received_total`, `hubble_observability_flow_dropped_total`, `hubble_observability_flow_allowed_total`, `cni_network_policy_drop_total`, `pod_network_reachable{destination!="",source!=""} 1`, `cilium_endpoint_state{endpoint!=""}`, `cilium_identity_state{identity!=""}`, `bpf_map_entries{map="cilium_flow"}`, `cilium_drops_total{direction="in"}`, `cilium_drops_total{direction="out"}`, `cilium_ipam_total_addresses`, `cilium_ipam_free_addresses`, `node_network_receive_bytes_total`, `node_network_transmit_bytes_total` |
| **Collection** | `cilium` DaemonSet logs; `hubble` relay and observability components; Cilium-prometheus metrics endpoint (`/metrics`); `cilium agent` health API (`/health`); `cilium identity` allocation pool; BPF introspection via `ls /sys/fs/bpf/`; `kube-proxy` metrics; `cilium policymap` dump |
| **Dashboards** | Cilium endpoint health and state; identity allocation and usage; BPF map pressure and load; policy drop trends; flow send/receive rates; dropped vs allowed packets; IPAM address space heatmap; node-to-node and pod-to-service connectivity heatmap; Hubble flow latency and direction |
| **Alerts** | `CNIConnectivityLoss` (hubble_observability_flow_dropped_total increase for 5m), `BPFMapPressure` (bpf_map_entries{map="cilium_flow"} / bpf_map_max_entries{map="cilium_flow"} > 0.85), `PolicyDrop` (cilium_drops_total{direction="in"} > 0 or cilium_drops_total{direction="out"} > 0 for 5m), `IPAMExhaustion` (cilium_ipam_free_addresses == 0), `EndpointStale` (cilium_endpoint_state{state="stale"} > 0), `IdentityNotReady` (cilium_identity_state{state!="ready"} > 0), `NodeToNodeDisruption` (hubble_observability_flow_received_total decrease for 5m), `DNSConnectivityFailure` (hubble_dns_query_failure_total > 0) |
| **SLI/SLO** | Connectivity success SLO: 99.9% of pod-to-service connections succeed over 30d; BPF map utilization SLO: < 85% over 30d; IPAM availability SLO: > 10% free addresses over 30d; policy drop SLO: 0 drops over 30d; endpoint health SLO: 100% endpoints ready over 30d; node-to-node connectivity SLO: 99.9% over 30d; DNS resolution SLO: 99.9% over 30d |
| **Tuning** | BPF program JIT and load adjustment; cilium-agent resource requests/limits; policy rule complexity and number limits; IPAM pool size and renewal; hubble relay bandwidth and retention; kernel BPF sysctl parameters (`kernel.bpf_jit_harden`, `net.core.bpf_jit_factor`) |
| **Troubleshooting** | `cilium status`; `cilium agent status`; `cilium endpoint list`; `cilium endpoint describe <id>`; `cilium bpf map dump`; `cilium bpf tunnel list`; `kubectl get ciliumpolicy -A`; `kubectl describe node <node>`; `hubble observe --iscsi` or `hubble tcp dump`; `ethtool -S <interface>` for driver-level counters |
| **Recovery** | Restart Cilium DaemonSet: `kubectl rollout restart daemonset/cilium -n kube-system`; increase IPAM pool size via CiliumConfig; adjust BPF map size or restart agent to reclaim; fix NetworkPolicy rules causing drops; reset BPF programs if JIT compilation failed; add node CIDR or expand cluster network if exhaustion; promote replica or restart hubble relay if stale |
| **Dependencies** | Cilium DaemonSet running in kube-system; kube-apiserver reachable for Cilium API calls; kubelet reachable on port 10248 for agent; BPF filesystem available (`/sys/fs/bpf/`); kernel version supports required BPF features; network plugin is Cilium (not alternative CNI) |

## Validation Commands (independent of Prometheus)

| Check | Command | Expected Output |
|---|---|---|
| Cilium agent health | `cilium status` | `Controller: Running`, `Agent: Ready`, `ClusterHealth: Good` |
| Endpoint list | `cilium endpoint list` | All endpoints listed with IP, ready state, and node assignment |
| Endpoint describe | `cilium endpoint describe <id>` | Endpoint details: IPAM, ready/labels, associated pod |
| BPF map dump | `cilium bpf map dump` | BPF map entries listed; map sizes reported |
| Policy drops check | `cilium bpf endpoint dump` | Drop counts per endpoint; `cilium_drops_total` metrics |
| IPAM free addresses | `cilium ipam show` | Free address pool and allocation summary |
| Hubble flow observe | `hubble observe --of=json` | Flow events streamed; drop events visible |
| CNI network policy | `kubectl get networkpolicy -A` | NetworkPolicy rules listed and active |
| Node-to-node connectivity | `hubble tcp dump --node=<node1>--node=<node2>` | Packet flow between nodes; latency and drops |
