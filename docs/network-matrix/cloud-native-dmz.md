# Cloud-native DMZ — edge segmentation and traffic policy

One exposed segment. Everything else is unreachable from outside.

## Segments

| Segment | CIDR | What lives there |
|---|---|---|
| DMZ | 10.60.0.0/24 | Edge LB nodes only: keepalived + HAProxy/Nginx via Docker Compose. VIP 10.60.0.10/24. |
| Management | 10.10.0.0/24 | Ops workstation, Ansible server, Vault, GitLab, HAProxy stats (8404), SSH. |
| Control plane | 10.20.0.0/24 | Kubespray control plane with stacked etcd; kube-apiserver 10.20.0.100. |
| Storage (public) | 10.40.0.0/24 | Ceph MON/OSD/MDS/RGW public network. |
| Storage (cluster) | 10.41.0.0/24 | Ceph replication/rebalance between OSDs. |
| GPU | 10.50.0.0/24 | GPU workers, DCGM exporter 9400, model store. |

## Edge dataplane

Two nodes (`lb-node-1`, `lb-node-2`), identical stack:

- **keepalived** — VRRP instance `VI_EDGE`, VIP 10.60.0.10, unicast peers (`10.60.0.1` ↔ `10.60.0.2`) because the DMZ VLAN filters multicast `224.0.0.18`; `auth_pass` rendered by Ansible from Vault; health script checks local HAProxy and lowers priority on failure. See `../manifests/external-lb/keepalived.conf`.
- **HAProxy** — binds `0.0.0.0:443` (TCP) → Nginx `127.0.0.1:8443` (L7 ingress tier) and `0.0.0.0:6443` (TCP) → kube-apiserver `10.20.0.100:6443` with `/readyz` check. The dataplane binds the wildcard address, not the VIP, so a VRRP failover needs no container restart. See `../manifests/external-lb/haproxy.cfg`.
- **Stats** — `10.60.0.1:8404` on the **management** address only. Never bound to the DMZ address.

## What crosses the DMZ

| Direction | Flow | Ports | Firewall location |
|---|---|---|---|
| In | Clients / ops workstation → edge LB VIP | 443, 22 | dmz fw |
| In | Edge LB peer → edge LB peer | IP proto 112 (VRRP) | dmz fw |
| Out | Edge LB → kube-apiserver (via itself) | 6443 | dmz fw |
| Out | Edge LB → MetalLB peers (BGP, if used) | 179 | dmz fw |
| In | Everything else to the DMZ | — | dropped |

Nothing terminates directly on the DMZ except the edge:

- **vLLM inference port 8000** is never exposed to the DMZ; clients reach it through the DMZ gateway only (`gpu-ai/inference/llm-serving.md`).
- HAProxy stats never listen on the DMZ address.
- MetalLB is an in-cluster L4 LB; it is not DMZ-exposed.

Services reachable through the DMZ VIP (clients address the VIP, never the backends): Rancher, Argo CD, Keycloak, Grafana, L7 ingress (F5 NGINX IC / NGINX Gateway Fabric / Envoy Gateway), LLM inference via the API gateway. Their backends run in the cluster or management segments.

## Role-specific firewall behavior

| Role | Adds | Removes |
|---|---|---|
| Management cluster | 443 from dmz | — |
| DMZ edge | 443 from outside | Everything else |

Full ruleset skeleton: `network-matrix/firewall-rules-generation.md`; per-flow matrix: `network-matrix/port-requirements.md`.

## Validation

```bash
# From an allowed source (ops workstation / DMZ client)
nmap -Pn -p 22,443,6443 <edge-vip>
# Expect: 22, 443 open; 6443 open only via the edge proxy check below

# From a denied source
nmap -Pn -p 22,443,6443 <edge-vip>
# Expect: filtered

# Ruleset loaded on each node
nft list ruleset
firewall-cmd --list-all   # firewalld hosts only

# Edge health
docker logs edge-keepalived
curl -k https://<vip>:6443/readyz      # expect 200
curl -s http://<lb-mgmt>:8404/         # from management: expect stats page
curl -s http://<vip>:8404/             # from DMZ: expect failure
```

Both nmap results are recorded as evidence for acceptance test B-10.

## Rules never to break

1. Stats bound to `10.60.0.1:8404` (management) only — never the DMZ address.
2. Edge image set is minimal, no shell; VRRP `auth_pass` and TLS keys written by Ansible from Vault.
3. Unicast VRRP peers unless the network team confirms multicast `224.0.0.18` end to end on the DMZ VLAN.
4. vLLM port 8000 never reachable directly from the DMZ.
5. One firewall implementation per host — nftables or firewalld, never both.

## Related

- `network-matrix/external-load-balancer.md` — active/active edge tiers 1–3
- `network-matrix/port-requirements.md` — full server-to-server access matrix
- `network-matrix/firewall-rules-generation.md` — nftables / firewalld generation
- `manifests/external-lb/haproxy.cfg` — edge dataplane config
- `manifests/external-lb/keepalived.conf` — VRRP unicast config
- `manifests/external-lb/nginx.conf` — L7 ingress behind the edge
- `gpu-ai/inference/llm-serving.md` — inference API kept off the DMZ
