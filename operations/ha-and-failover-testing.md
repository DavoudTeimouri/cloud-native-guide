# Section 10: HA & Failover Testing

## Guiding Principles

- **Non-destructive simulations only** — Use safe injection methods (config manipulation, mock services, circuit breaking) before considering any live failover.
- **Distinguish lab-only vs production-safe** — Lab scenarios may use cluster shutdown or network partitioning; production scenarios must use controlled, gradual failover with rollback built in.
- **Never perform live injection** on production without explicit SRE sign-off and a tested rollback path.
- **All failure scenarios below are described for documentation purposes; no live action is taken.**

---

## Control-Plane Nodes

| Field | Content |
|---|---|
| **Preconditions** | Multi-node control plane (3+ nodes); etcd quorum intact; API server available on at least one node |
| **Failure Injection Method (Safe Simulation)** | `kubectl drain` a control-plane node with `--ignore-daemonsets--purge-local-data`; simulate etcd leadership loss by pausing a member via etcdctl; reduce API server replica count via manual scaling (reversible) |
| **Expected Behavior** | Remaining control-plane nodes maintain quorum; API server stays up; workloads continue scheduling on healthy nodes; drained node's pods rescheduled elsewhere |
| **Monitoring Signals** | API server latency; etcd leader election logs; kube-controller-manager health; node status transitions |
| **Recovery Procedure** | Undo drain; node rejoins cluster; verify etcd member status; restart kubelet; confirm API server responds |
| **Success Criteria** | All control-plane nodes Ready; etcd quorum > 50% + 1; API server responds within SLO; no split-brain etcd state |
| **Rollback/Abort Conditions** | etcd quorum lost; split-brain detected; more than one control-plane node drained simultaneously; API server unresponsive after 10m |

---

## Worker Nodes

| Field | Content |
|---|---|
| **Preconditions** | Cluster with ≥ 2 worker nodes; workloads distributed across nodes; taints/tolerations in place where applicable |
| **Failure Injection Method (Safe Simulation)** | `kubectl drain` a worker node; simulate kubelet crash by stopping the kubelet process; network partition via iptables rules on the node (lab-only) |
| **Expected Behavior** | Node marked NotReady; pods rescheduled to remaining workers; no data loss; drain completes only if all pods are terminated or moved |
| **Monitoring Signals** | Node NotReady status; pod distribution; kubelet metrics; eviction rates |
| **Recovery Procedure** | Undo drain; node rejoins cluster; verify kubelet service; pods resume on node if assigned |
| **Success Criteria** | Node Ready; pods scheduled and running; no backlog of unscheduled pods; resource usage balanced |
| **Rollback/Abort Conditions** | Node fails to rejoin after 15m; etcd lag spikes; pod disruption budget violations; manual intervention required |

---

## Network Paths / Load Balancers

| Field | Content |
|---|---|
| **Preconditions** | External LoadBalancer or ingress controller; HAProxy/Nginx/Keepalived fronting services; backend services healthy |
| **Failure Injection Method (Safe Simulation)** | Suspend Keepalived `vrrp_instance` on the primary; iptables DROP on the VIP; redirect DNS TTL short-term; use `tc` to add latency/jitter (lab only) |
| **Expected Behavior** | Failover to standby LB instance; clients reconnect via new VIP; existing connections may terminate (expected) |
| **Monitoring Signals** | VIP availability; Keepalived state changes; backend health check status; client connection counts |
| **Recovery Procedure** | Restore Keepalived primary state; remove iptables rules; verify DNS resolution; health checks pass |
| **Success Criteria** | VIP active on primary; health checks passing; traffic flows through LB; no client-facing errors for > SLA window |
| **Rollback/Abort Conditions** | Standby LB fails to take VIP; iptables rules persist; DNS TTL too long; health checks fail on both nodes |

---

## Ceph MON / OSD

| Field | Content |
|---|---|
| **Preconditions** | Ceph cluster with ≥ 3 MONs; multiple OSDs per host; cluster in HEALTH_OK state |
| **Failure Injection Method (Safe Simulation)** | `systemctl stop ceph-mon` on a MON node (lab); `ceph osd out` an OSD safely; fill-up flag simulation via `rados -p <pool> size <n>` (reversible) |
| **Expected Behavior** | Remaining MONs maintain quorum; OSD out completes PG rebalancing; cluster remains functional at reduced ratio |
| **Monitoring Signals** | MON quorum status; OSD health; PG state; cluster health; PG recovery throughput |
| **Recovery Procedure** | Restart MON service; `ceph osd in` the OSD; verify PGs return to active+clean; check CRUSH map version |
| **Success Criteria** | `ceph health OK`; quorum of MONs active; all PGs active+clean; no OSD backfill errors |
| **Rollback/Abort Conditions** | Quorum lost (< 3 MONs with 3 deployed); OSD out/in oscillates; PG stuck in recovery for > 30m; data corruption detected |

---

## Registry Frontends / Backends (Harbor / Nexus)

| Field | Content |
|---|---|
| **Preconditions** | Registry cluster running; backend storage available; TLS termination operational |
| **Failure Injection Method (Safe Simulation)** | Restart registry container/deployment; simulate storage latency via `tc` (lab only); pull-through cache miss injection; tag deletion test |
| **Expected Behavior** | Push/pull failovers to replica if multi-replica setup; cached layers remain accessible; metadata serves from remaining instance |
| **Monitoring Signals** | API response latency; push success/failure rate; pull latency; storage I/O wait; TLS certificate validity |
| **Recovery Procedure** | Restart registry from persistent volume; verify storage accessibility; reinitialize if config lost; re-sync metadata from backup |
| **Success Criteria** | Image push succeeds; image pull succeeds; registry API responsive; storage usage matches expected; no orphaned layers |
| **Rollback/Abort Conditions** | Storage corrupted; metadata index lost; all replicas failed; push pipeline blocked for > RTO target |

---

## Identity Services (Keycloak / Vault)

| Field | Content |
|---|---|
| **Preconditions** | Identity cluster running; TLS certs valid; user store (LDAP/DB) reachable; tokens within TTL |
| **Failure Injection Method (Safe Simulation)** | Restart Keycloak pod; revoke all active sessions; simulate DB latency; toggle TLS cert expiration (reversible) |
| **Expected Behavior** | Authentication degrades to cached/fallback mode; new sessions cannot be created until recovery; existing sessions remain valid until TTL |
| **Monitoring Signals** | Auth success/failure rate; token TTL expiry; DB connection pool usage; TLS handshake errors |
| **Recovery Procedure** | Restart identity service; re-seal/unseal Vault if applicable; refresh TLS certs from backup; re-sync user store if drift detected |
| **Success Criteria** | Login succeeds; token issuance functional; user provisioning matches expected; no auth failures for > 5m |
| **Rollback/Abort Conditions** | User store unreachable after 10m; TLS cert revoked; all sessions expired; authentication stack offline for > RTO target |

---

## Monitoring Stack (Prometheus / Grafana / Alertmanager)

| Field | Content |
|---|---|
| **Preconditions** | Multi-node Prometheus deployment; Alertmanager with receivers; Grafana datasources healthy |
| **Failure Injection Method (Safe Simulation)** | `kubectl scale` Prometheus deployment to 0 (then back); kill a single Prometheus instance; simulate TSDB compaction lag; pause Alertmanager routing rules |
| **Expected Behavior** | Remaining instances absorb scrape targets; Alertmanager queues notifications; Grafana shows last-known data with staleness indicator |
| **Monitoring Signals** | Scrape success/failure; alert firing latency; receiver connectivity; TSDB query latency; datasource error state |
| **Recovery Procedure** | Restart Prometheus from TSDB; reapply Alertmanager config; verify datasource connectivity; refresh Grafana cache |
| **Success Criteria** | Scrapes resume; alerts fire for known conditions; notifications sent; Grafana loads dashboards; TSDB retention honored |
| **Rollback/Abort Conditions** | TSDB data loss detected; alertqueue backs up for > 1h; remaining instances overwhelmed; config drift > 5m |

---

## DNS / Time Sync

| Field | Content |
|---|---|
| **Preconditions** | Internal DNS server(s); NTP/PTP time sources; cluster DNS configmap; external DNS provider |
| **Failure Injection Method (Safe Simulation)** | `systemctl stop` dnsmasq/local DNS; add static wrong A record (lab only); simulate NTP stratum loss; flush DNS cache |
| **Expected Behavior** | External resolution falls back to configured secondary/fallback; internal services use cached entries; time drift limited by NTP stratum 2+ sources |
| **Monitoring Signals** | DNS query latency/errors; NTP offset; system clock drift; resolver errors in logs |
| **Recovery Procedure** | Restart DNS service; remove incorrect records; clear cache; re-sync time via NTP; verify resolution |
| **Success Criteria** | DNS resolves correctly; time offset < 1s; services authenticate; certificates not rejected due to clock skew |
| **Rollback/Abort Conditions** | DNS cache poisoned; NTP source unreachable for > 1h; clock skew causes cert expiry; external DNS provider outage |

---