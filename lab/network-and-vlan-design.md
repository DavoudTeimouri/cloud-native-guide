# Lab — Network and VLAN Design

**Section 8** of the Cloud-Native Stack Lab architecture planning. This document provides logical network segmentation, CIDR planning, routing/firewall boundaries, and IP allocation templates for the lab environment. All subnets use placeholder addresses; do not invent concrete VLAN IDs or IP ranges.

---

## 1. Network Segmentation Overview

The following networks/VLANs are evaluated for logical separation. Not every network requires a dedicated physical NIC or VLAN — trade-offs are noted per network.

| # | Network | Purpose | Dedicated NIC/VLAN Required? | Trade-offs |
|---|---------|---------|------------------------------|------------|
| 1 | **Management** | Out-of-band admin access, CSP, automation, SSO, CI/CD pipelines | Yes — typically a separate physical/virtual switch | Isolation of admin traffic; risk of mgmt plane saturation if mixed with data traffic |
| 2 | **OOB / BMC** | IPMI/iDRAC/LOM, server health monitoring, out-of-band power/boot control | Often shares physical infrastructure with mgmt; separate VLAN recommended | Headless servers may have no other network; VLAN offload saves NIC ports |
| 3 | **K8s API / Control Plane** | Kubernetes API server VIP, etcd peer traffic, control-plane health checks | Yes — typically a dedicated VIP subnet; separate from node traffic | Protects control plane; must be routable/firewall-filtered; MTU considerations for jumbo frames |
| 4 | **K8s Node & Pod Traffic** | Node-to-node, pod-to-pod, kubelet, CNI overlay | Depends on CNI: Cilium overlay may use a dedicated pod CIDR; direct-routing shares node IP | Overlay (Cilium/Flannel) adds encapsulation overhead; direct-routing requires sufficient node IP space |
| 5 | **Service Traffic** | ClusterIP, NodePort, LoadBalancer VIPs | Often co-located with node traffic via kube-proxy / Cilium IPVS | Service VIPs may need separate LB/VIP network (see below) |
| 6 | **Ceph Public / Client** | Ceph MON API, RGW, client read/write workloads | Yes — dedicated VLAN/subnet for Ceph public traffic | Separation of client and cluster traffic; Ceph scale-out requires bandwidth headroom |
| 7 | **Ceph Cluster / Replication** | OSD-to-OSD, MON-to-MON, MDS-to-MDS replication | Yes — typically separate from public; iSCSI/TCP data plane | Replication traffic can saturate shared links; separate NIC/port prevents starvation |
| 8 | **Storage Client Access** | iSCSI, NFS, Fibre Channel front-ends for PV provisioning | Often converges with Ceph public or uses separate storage VLAN | Converges savings vs. separate physical isolation; multipath failover complexity |
| 9 | **LB / VIP** | External and internal load balancer VIPs, ingress points | Yes — dedicated VIP subnet; often fronted by metalLB/haproxy/NGINX | VIPs must not overlap with node/subnet CIDRs; ARP/domain separation |
| 10 | **Ingress / DMZ** | Ingress controllers, reverse proxies, external-facing services | Yes — separate zone; firewall-filtered from internal networks | Defense-in-depth; must restrict inbound protocols/ports |
| 11 | **Repository & Registry** | Harbor, Nexus, Docker registry, yum/apt mirrors | Often shares mgmt or LB/VIP network; separate VLAN if scale demands | Registry traffic can be bursty; separate reduces impact on mgmt |
| 12 | **Backup** | Velero, off-site backup targets, restic repositories | Often shares mgmt or a small dedicated VLAN | Backup windows may overlap with production; separate avoids interference |
| 13 | **Monitoring / Logging** | Prometheus, Alertmanager, Grafana, Loki, ELK | Often co-located with mgmt; separate VLAN if traffic isolation needed | Metrics scrapes are chatty; separate VLAN prevents noise on admin plane |
| 14 | **External Egress** | Internet-bound traffic, external API calls, package downloads | Typically shared via default route; separate egress IP if policy required | NAT or egress gateway; firewall policy must allow required outbound |

---

## 2. CIDR Placeholders and Assignment

Use the following placeholders. Do **not** invent concrete VLAN IDs or subnet allocations. Replace with site-specific values consistent with existing production infrastructure.

| Placeholder | Meaning | Typical Usage |
|-------------|---------|---------------|
| `<MGMT_SUBNET>` | Management/OOB VLAN CIDR | mgmt, BMC, automation, SSH |
| `<K8S_NODE_SUBNET>` | Worker / node subnet CIDR | node IPs, kubelet, CNI overlay |
| `<POD_CIDR>` | Pod CIDR range | pod-to-pod traffic, Cilium overlay |
| `<SERVICE_CIDR>` | Service CIDR range | ClusterIP/NodePort, kube-proxy |
| `<CEPH_PUBLIC_SUBNET>` | Ceph client/public traffic CIDR | RGW, MON API, client read/write |
| `<CEPH_CLUSTER_SUBNET>` | Ceph cluster/replication CIDR | OSD-to-OSD, MON-to-MON replication |
| `<LB_VIP>` | Load balancer / ingress VIP CIDR | MetalLB, ingress controller VIPs, external LB |

**CIDR overlap risks** — ensure no two placeholders share address space. In particular:

- `<POD_CIDR>` must not overlap `<K8S_NODE_SUBNET>` or `<SERVICE_CIDR>`
- `<CEPH_PUBLIC_SUBNET>` must not overlap `<CEPH_CLUSTER_SUBNET>` or any K8s CIDR
- `<LB_VIP>` must not overlap `<MGMT_SUBNET>`, `<K8S_NODE_SUBNET>`, or `<POD_CIDR>`
- If using `<LB_VIP>` in the same address space as `<MGMT_SUBNET>`, distinguish by host bits (e.g., VIPs on .1/.2, mgmt on .10+)

---

## 3. Routing and Firewall Boundaries

| Network | Routing Boundary | Firewall Policy | Notes |
|---------|-----------------|-----------------|-------|
| `<MGMT_SUBNET>` | Router/firewall to `<K8S_NODE_SUBNET>` and `<CEPH_PUBLIC_SUBNET>` | Inbound: restricted to admin IPs/ bastion Outbound: unrestricted to internet via egress gateway | Management plane isolation; console access via out-of-band |
| `<K8S_NODE_SUBNET>` | Router to `<LB_VIP>`, `<CEPH_PUBLIC_SUBNET>`, `<SERVICE_CIDR>` | Allow: K8s API (6443), NTP (123), DNS (53) Deny: all other inbound | Node-to-node traffic filtered by Cilium network policy or host firewall |
| `<LB_VIP>` | Direct-routing to nodes; no inter-VLAN routing required if MetalLB L2 mode | Allow: inbound from `<MGMT_SUBNET>` and `<INFRA_DMZ>` on 443/80; BGP peering (7474/4789) if MetalLB BGP | VIPs are anycast or per-node; ARP-limited to same L2 or routed via L3 |
| `<CEPH_PUBLIC_SUBNET>` | Router to K8s nodes (RBD, RGW) and storage clients | Allow: MON (6789), RGW (7480), OSD data (6800-7568) Deny: all other inter-network traffic | Separate from `<CEPH_CLUSTER_SUBNET>`; bandwidth ≥ 10 Gbps recommended |
| `<CEPH_CLUSTER_SUBNET>` | Internal router only; no northbound exposure | Allow: OSD replication (6800-7568), MON raft (2380/2379) Deny: all management/admin traffic | Often on dedicated physical NICs; latency < 1 ms intra-rack preferred |
| `<INFRA_DMZ>` (Ingress/DMZ) | Router to untrusted; firewall enforces default-deny inbound | Allow: HTTP (80), HTTPS (443) from `<MGMT_SUBNET>` source IPs only; rate-limit; log all Deny: all other inbound | Defense-in-depth; separate physical or VLAN isolation from internal networks |
| `<BACKUP_SUBNET>` | Router to backup targets (Velero, off-site) | Allow: TCP 443 (Velero API), 587 (SMTP relay), 8081 (Nexus) Deny: all other | Schedule-backup window coordination with production loads |
| `<MONITORING_SUBNET>` | Router to scraping targets and backends | Allow: TCP 9090 (Prometheus), 5044 (Logstash), 9200 (OpenSearch) Deny: all other inbound | Metrics volumes can be high; separate VLAN avoids mgmt-plane saturation |
| `<EGRESS_SUBNET>` | Default route exit point; NAT to internet | Policy: allow outbound 80/443, DNS 53, NTP 123; block inbound from internet | May use proxy or direct NAT; firewall logs all egress |

---

## 4. MTU Requirements

| Network | Recommended MTU | Notes |
|---------|----------------|-------|
| `<MGMT_SUBNET>` | 1500 (standard) | Jumbo frames not typically needed for admin traffic |
| `<K8S_NODE_SUBNET>` | 1500 (standard) | If Cilium with VXLAN/Geneve, MTU may drop to 1400; account for overhead |
| `<POD_CIDR>` | 1400–1450 (if overlay) | Cilium VXLAN/Geneve adds ~50–100 bytes; verify with `ip path show` |
| `<SERVICE_CIDR>` | 1500 (standard) | kube-proxy/IPVS does not encapsulate |
| `<CEPH_PUBLIC_SUBNET>` | 9000 (jumbo frames) | Ceph delivers high throughput; jumbo frames reduce CPU overhead. Confirm switch/ NIC support. |
| `<CEPH_CLUSTER_SUBNET>` | 9000 (jumbo frames) | Replication/backfill benefits from large frames; same NIC/switch constraints apply |
| `<LB_VIP>` | 1500 (standard) | L4/L7 load balancers; jumbo frames not required |
| `<INFRA_DMZ>` | 1500 (standard) | Ingress traffic may include jumbo frames from uploads; validate end-to-end |
| `<BACKUP_SUBNET>` | 1500 (standard) | Varies; verify backup software and targets |
| `<MONITORING_SUBNET>` | 1500 (standard) | Metrics over UDP; no fragmentation typically |
| `<EGRESS_SUBNET>` | 1500 (standard) | Internet traffic; may traverse VPN or proxy with varying MTU |

**Cilium overlay note**: If using Cilium with `mode: "routing"` (direct-routing), MTU remains 1500 because traffic is forwarded at L3 without encapsulation. If using `mode: "overlay"` (VXLAN/Geneve), subtract the encapsulation overhead (50 bytes VXLAN, 20 bytes Geneve) from the physical MTU to determine the effective pod MTU. A physical MTU of 9000 with VXLAN yields ~8900 effective pod MTU — verify application compatibility.

---

## 5. DNS Requirements

| Network | DNS Forwarder/Resolver | Search Domains | Notes |
|---------|----------------------|----------------|-------|
| `<MGMT_SUBNET>` | `<dns.internal>` | `mgmt.internal` | Static resolver config on switch/L3; forward to AD DNS |
| `<K8S_NODE_SUBNET>` | K8s CoreDNS (cluster IP `10.20.0.10` placeholder) | `cluster.local`, `<INFRA_DMZ>` | Verify CoreDNS config maps to API VIP |
| `<LB_VIP>` | External DNS provider or internal split-horizon | `internal`, `example.com` | Ingress VIPs must resolve from both inside and outside |
| `<CEPH_PUBLIC_SUBNET>` | Ceph MON DNS (`ceph-mon-1.<namespace>.svc.cluster.local`) | `cluster.local` | May use external DNS for RGW if multi-region |
| `<INFRA_DMZ>` | Internal AD DNS + external resolver | `internal`, `dmz.internal` | Split-horizon for external-facing services |
| `<BACKUP_SUBNET>` | Velero/backup target DNS | `backup.internal` | May use S3-compatible endpoint DNS |
| `<MONITORING_SUBNET>` | Prometheus/Alertmanager self-discovery | `monitoring.internal` | Service discovery via K8s labels or static config |
| `<EGRESS_SUBNET>` | ISP DNS or corporate resolver | `corp.internal` | May use DNS-over-HTTPS if policy requires |

---

## 6. NTP Requirements

| Network | NTP Source | Notes |
|---------|-----------|-------|
| `<MGMT_SUBNET>` | `ntp.internal` | Management workstations; typically LAN-synchronized |
| `<K8S_NODE_SUBNET>` | `ntp.internal` | Node clocks synchronize; critical for K8s security (token TTL, cert expiry) |
| `<LB_VIP>` | N/A | VIPs do not run NTP; underlying nodes do |
| `<CEPH_PUBLIC_SUBNET>` | `ntp.internal` | Ceph daemons benefit from synchronized time for log correlation |
| `<CEPH_CLUSTER_SUBNET>` | `ntp.internal` | Same as public; MON cluster requires time sync for quorum |
| `<INFRA_DMZ>` | `ntp.internal` | Ingress nodes; synchronize if logging is centralized |
| `<BACKUP_SUBNET>` | `ntp.internal` | Backup servers; time stamps critical for audit |
| `<MONITORING_SUBNET>` | `ntp.internal` | Monitoring agents; correlated logs across hosts |
| `<EGRESS_SUBNET>` | N/A | Exit nodes sync via default NTP config |

---

## 7. Required Ports and Traffic Direction

Key ports per network flow. Verify against component documentation for the pinned release.

| # | Source | Destination | Proto | Port(s) | Direction | Firewall / Host |
|---|--------|-------------|-------|---------|-----------|-----------------|
| 1 | Any admin workstation | `<MGMT_SUBNET>` | TCP | 22, 443 | in | mgmt firewall |
| 2 | Any node | `<MGMT_SUBNET>` | UDP | 123 | out | NTP |
| 3 | Any node | DNS | UDP/TCP | 53 | out | resolv.conf |
| 4 | K8s API VIP | Nodes | TCP | 6443 | out | cp firewall |
| 5 | Nodes | K8s API VIP | TCP | 6443 | in | cp firewall |
| 6 | Nodes | etcd peer | TCP | 2380 | both | cp firewall |
| 7 | Nodes | etcd client | TCP | 2379 | out | cp firewall |
| 8 | Clients | `<LB_VIP>` / ingress | TCP | 80, 443 | in | dmz firewall |
| 9 | Clients | `<INFRA_DMZ>` | TCP | 443 | in | dmz firewall |
| 10 | Ceph clients | `<CEPH_PUBLIC_SUBNET>` | TCP | 6789 (MON) | out | storage firewall |
| 11 | Ceph clients | `<CEPH_PUBLIC_SUBNET>` | TCP | 7480 (RGW) | out | storage firewall |
| 12 | Ceph clients | `<CEPH_PUBLIC_SUBNET>` | TCP | 6800–7568 (OSD data) | out | storage firewall |
| 13 | OSD | `<CEPH_CLUSTER_SUBNET>` | TCP | 6800–7568 (replication) | both | storage firewall (internal) |
| 14 | OSD | `<CEPH_CLUSTER_SUBNET>` | UDP | 2380/2379 (MON raft) | both | storage firewall (internal) |
| 15 | Monitoring agents | `<MONITORING_SUBNET>` | TCP | 9100, 9090, 443 | out | mgmt firewall |
| 16 | Users | `<INFRA_DMZ>` / Grafana | TCP | 443 | in | dmz firewall |
| 17 | Automation server | `<MGMT_SUBNET>` | TCP | 22 (SSH) | in | mgmt firewall |
| 18 | Automation server | Vault/AD | TCP | 8200/389/636 | out | mgmt firewall |
| 19 | Users | SMTP relay | TCP | 587 | out | mgmt firewall |
| 20 | Nodes | External egress | UDP/TCP | 53, 80, 443 | out | egress firewall / NAT |

---

## 8. Cilium Overlay vs Direct-Routing Considerations

| Aspect | Cilium Overlay (VXLAN/Geneve) | Direct-Routing (L3 routing) |
|--------|-------------------------------|------------------------------|
| **MTU** | Physical MTU − 50 (VXLAN) or − 20 (Geneve). Effective pod MTU ~ 8500–9000 if physical = 9000. | Physical MTU 1500 remains 1500; no encapsulation overhead. |
| **Control plane** | Cilium CRDs, BPF maps, cluster mesh. Requires `cilium-agent` on every node. | Kube-proxy (IPVS or nftables); no additional agent per node (if using native kube-proxy). |
| **Scalability** | Excellent for > 500 nodes; supports cluster mesh, IPv4/IPv6. | Scales well; kernel BPF/nftables performance is high; state is in user-space or kernel. |
| **Observability** | Built-in eBPF flow tracking, service mesh features, security policies. | Requires separate tooling (sflow, mirroring, kube-proxy metrics). |
| **Node-to-node latency** | Slightly higher due to encapsulation (∼0.1–0.3 ms per hop). | Lower latency; direct L3 forwarding. |
| **Pod-to-pod across nodes** | Traffic routed through Cilium agent on source node, then encapsulated. | Traffic forwarded at L3 via routing table; may use node’s default gateway. |
| **Requirements** | Requires sufficient node IP space for pod CIDR; overlays may needPromiscuous mode on hypervisor. | Requires node CIDR not overlapping pod CIDR; routing table entries per pod range. |
| **Recommendation for this lab** | Use direct-routing (`mode: "routing"`) if node IP space allows, for simplicity and MTU consistency. Use overlay only if cluster mesh or multi-tenant isolation is needed. | |

---

## 9. Ceph Latency and Bandwidth Considerations

| Metric | Recommended | Rationale |
|--------|-------------|-----------|
| **Public (client) bandwidth** | ≥ 10 Gbps per OSD pool | RBD read/write and RGW S3 traffic can be bursty; 10 Gbps headroom avoids head-of-line blocking. |
| **Cluster (replication) bandwidth** | ≥ 25 Gbps or 100 Gbps depending on cluster size | OSD-to-OSD replication, backfill, and scrub can consume significant bandwidth; separate NIC/VLAN prevents starving client traffic. |
| **Public latency** | < 2 ms intra-rack, < 5 ms inter-rack | Ceph tolerates some latency, but high latency reduces effective IOPS and throughput, especially for small-object workloads. |
| **Cluster latency** | < 1 ms intra-rack | Replication and quorum (MON raft) are sensitive to latency; inter-rack deployment requires careful design (e.g., WAN replication is not recommended for critical data). |
| **Network topology** | Rack-mounted OSDs with dedicated 10/25/40 GbE or RoCE v2 | Converged ethernet (RoCE) can unify client and replication traffic, but requires lossless DCB; separate physical NICs are simpler for a lab. |
| **Jumbo frames** | MTU 9000 on all Ceph links | Confirmed switch/ NIC support required; mixed MTU domains cause packet fragmentation and performance degradation. |

---

## 10. IP Allocation Template

The following tables provide a reusable template. Replace placeholder subnets with concrete values from `<MGMT_SUBNET>`, `<K8S_NODE_SUBNET>`, etc. All IPs are illustrative; do not apply directly without subnet assignment.

### 10.1 Control-Plane Nodes (CP)

| Role | IP Assignment | Notes |
|------|--------------|-------|
| API VIP | `<LB_VIP>/24` — e.g., `<LB_VIP>.10/32` | Anycast or per-node; depends on MetalLB/LB solution |
| etcd member 1 | `<K8S_NODE_SUBNET>.2/32` | First usable node IP |
| etcd member 2 | `<K8S_NODE_SUBNET>.3/32` | |
| etcd member 3 | `<K8S_NODE_SUBNET>.4/32` | |
| Control-plane master 1 | `<K8S_NODE_SUBNET>.10/32` | |
| Control-plane master 2 | `<K8S_NODE_SUBNET>.11/32` | |
| Control-plane master 3 | `<K8S_NODE_SUBNET>.12/32` | HA set |

### 10.2 Worker Nodes

| Role | IP Assignment | Notes |
|------|--------------|-------|
| Worker 1 | `<K8S_NODE_SUBNET>.50/32` | |
| Worker 2 | `<K8S_NODE_SUBNET>.51/32` | |
| Worker 3 | `<K8S_NODE_SUBNET>.52/32` | |
| … | … | Assign sequentially from the `<K8S_NODE_SUBNET>` range |

### 10.3 BMC Interfaces (OOB)

| Host | IP Assignment | Notes |
|------|--------------|-------|
| Server 1 BMC | `<MGMT_SUBNET>.10/24` | Out-of-band mgmt; separate VLAN from OS traffic |
| Server 2 BMC | `<MGMT_SUBNET>.11/24` | |
| Server 3 BMC | `<MGMT_SUBNET>.12/24` | |
| Server 4 BMC | `<MGMT_SUBNET>.13/24` | |
| … | … | |

### 10.4 Load Balancers and VIPs

| Service | IP Assignment | Notes |
|---------|--------------|-------|
| MetalLB speaker | `<LB_VIP>.20/32` | BGP peering or L2 mode |
| Ingress VIP | `<LB_VIP>.21/32` | External-facing; DNS points here |
| Internal service VIP | `<LB_VIP>.22/32` | For internal-only services |
| RGW S3 VIP | `<LB_VIP>.23/32` | If external RGW access needed |
| … | … | Do not overlap `<K8S_NODE_SUBNET>` or `<POD_CIDR>` |

### 10.5 Storage Nodes (Ceph)

| Role | IP Assignment | Notes |
|------|--------------|-------|
| MON 1 | `<CEPH_PUBLIC_SUBNET>.10/24` | Public API endpoint |
| MON 2 | `<CEPH_PUBLIC_SUBNET>.11/24` | |
| MON 3 | `<CEPH_PUBLIC_SUBNET>.12/24` | |
| OSD 1 | `<CEPH_PUBLIC_SUBNET>.50/24` + `<CEPH_CLUSTER_SUBNET>.10/24` | Public + cluster dual-homed |
| OSD 2 | `<CEPH_PUBLIC_SUBNET>.51/24` + `<CEPH_CLUSTER_SUBNET>.11/24` | |
| OSD 3 | `<CEPH_PUBLIC_SUBNET>.52/24` + `<CEPH_CLUSTER_SUBNET>.12/24` | |
| OSD 4–N | … | Assign from remaining space in both subnets |

### 10.6 Infrastructure Services

| Service | IP Assignment | Notes |
|---------|--------------|-------|
| Harbor registry | `<LB_VIP>.30/32` or `<MGMT_SUBNET>.50/24` | May share LB VIP or have dedicated IP |
| Nexus repository | `<MGMT_SUBNET>.60/24` | In-band mgmt or separate |
| GitLab instance | `<MGMT_SUBNET>.70/24` | |
| Keycloak / SSO | `<MGMT_SUBNET>.80/24` | |
| Prometheus | `<MONITORING_SUBNET>.10/24` | |
| Grafana | `<MONITORING_SUBNET>.20/24` | |
| Velero server | `<BACKUP_SUBNET>.10/24` | |
| AD/LDAP | `<MGMT_SUBNET>.100/24` | If Windows AD integrated |

---

## 11. Existing Infrastructure Classification

| Category | Description | Network Assignment |
|----------|-------------|-------------------|
| **Existing production infrastructure** | Live production networks, VLANs, firewalls, IPAM. | Do not re-use IP ranges from production without explicit coordination. Placeholder `<MGMT_SUBNET>` etc. must be distinct. |
| **Existing virtualized Ceph** | If an existing Ceph cluster is in scope, its CIDRs and VLANs are already allocated. | Reference existing `<CEPH_PUBLIC_SUBNET>` and `<CEPH_CLUSTER_SUBNET>` from the production ADR or infrastructure docs. New lab Ceph must use separate subnets to avoid overlap. |
| **Proposed Lab resources** | Fresh allocations for this lab environment. | Use the placeholder template above; document final assigned values in the lab inventory. |
| **Available-but-unconfirmed resources** | Infrastructure that may be available (spare NICs, unused VLANs) but whose allocation is not yet confirmed. | Mark as "TBD" in the lab inventory; do not commit until confirmed with the infra team. |

---

## 12. Summary and Next Steps

- **Documented**: 14 network/VLAN categories with purpose, NIC/VLAN trade-offs, routing/firewall boundaries, MTU, DNS, NTP, port requirements, Cilium overlay vs direct-routing considerations, Ceph latency/bandwidth, and IP allocation templates.
- **Placeholders only**: `<MGMT_SUBNET>`, `<K8S_NODE_SUBNET>`, `<POD_CIDR>`, `<SERVICE_CIDR>`, `<CEPH_PUBLIC_SUBNET>`, `<CEPH_CLUSTER_SUBNET>`, `<LB_VIP>` — do not replace with concrete values without IPAM coordination.
- **CIDR overlap review**: Ensure no two placeholders share address space; verify against existing production and existing Ceph allocations.
- **Recommended**: Walk the IPAM with the team, assign concrete /24 or larger blocks, then finalize the VLAN mapping and physical NIC plan.
- **Deliverable**: This file (`lab/network-and-vlan-design.md`) is the Section 8 output. No live infrastructure deployed or modified.

**File created**: `/workspace/project/github/public-repository/cloud-native-guide-next/lab/network-and-vlan-design.md`

**Sections covered**: 1 (segmentation overview), 2 (CIDR placeholders), 3 (routing/firewall), 4 (MTU), 5 (DNS), 6 (NTP), 7 (ports), 8 (Cilium overlay vs direct-routing), 9 (Ceph latency/bandwidth), 10 (IP allocation template), 11 (existing infrastructure classification), 12 (summary/next steps).