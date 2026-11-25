# Section 2: Operational Readiness Architecture

## Overview

This section defines a reusable readiness model applicable across the Cloud-Native Stack. Each component entry follows a consistent schema to enable automated cross-component readiness assessment, dependency mapping, and recovery planning.

---

### Schema

| Field | Description |
|---|---|
| **Component** | Name of the infrastructure or platform component |
| **Critical Dependencies** | Components that must be functional for this component to operate |
| **Failure Domains** | Scope of impact when this component fails |
| **Health/Readiness Indicators** | Metrics or signals confirming healthy operation |
| **Backup Requirements** | What must be backed up and at what frequency |
| **Recovery Procedure** | Step-by-step restoration process |
| **Recovery Validation** | Checks performed after recovery to confirm functionality |
| **Operational Ownership** | Team or role responsible for the component |
| **Monitoring/Alert Dependencies** | Alerting dependencies and cross-component correlations |

---

### Component Entries

#### 1. Physical / Virtual Infrastructure

| Field | Content |
|---|---|
| **Critical Dependencies** | BIOS/firmware, CPU, memory, storage controllers, network adapters, power supplies, rack infrastructure |
| **Failure Domains** | Node-level; cascading to VMs/containers on the same host |
| **Health/Readiness Indicators** | IPMI status, hardware health polls, fan/power status, thermal thresholds |
| **Backup Requirements** | BIOS configuration backup; host profile snapshots; infrastructure-as-code state |
| **Recovery Procedure** | Replace failed hardware; restore BIOS/config from repository; redeploy VM from golden image; reconcile DNS/hosts |
| **Recovery Validation** | IPMI health all-green; OS boot; node joins cluster; kubelet registers |
| **Operational Ownership** | Platform team / infrastructure |
| **Monitoring/Alert Dependencies** | IPMI alerts; hardware monitoring (e.g., ipmitool, ipmi-exporter); power consumption metrics |

#### 2. OS (Bare Metal / Hardened Node)

| Field | Content |
|---|---|
| **Critical Dependencies** | Kernel, system libraries, systemd, disk partitioning, firewall (nftables/iptables), SELinux/AppArmor |
| **Failure Domains** | Single node; node reboot required for kernel updates |
| **Health/Readiness Indicators** | systemd status; kernel ring buffer (dmesg) for panics; filesystem mount status; swap usage |
| **Backup Requirements** | ETCD snapshots (for cluster state); root filesystem snapshot (pre-upgrade); package database backup |
| **Recovery Procedure** | Reboot into rescue mode; restore root from snapshot; reinstall packages from repo; reseal node if required; rejoin cluster |
| **Recovery Validation** | Node status Ready; kubelet running; core services functional; SELinux enforcing |
| **Operational Ownership** | Platform team |
| **Monitoring/Alert Dependencies** | Node-exporter metrics; systemd unit health; dmesg error rate |

#### 3. Kubernetes Control Plane

| Field | Content |
|---|---|
| **Critical Dependencies** | etcd, kube-apiserver, kube-scheduler, kube-controller-manager, cloud-controller-manager, DNS, NTP |
| **Failure Domains** | Platform-wide; all workloads affected if control plane unavailable |
| **Health/Readiness Indicators** | API server response (200); etcd leader health; controller-manager health; scheduler latency |
| **Backup Requirements** | etcd snapshot (every 4-6h or before changes); API server certs; CA certificates |
| **Recovery Procedure** | Restore etcd from latest snapshot; reload API server certs; restart control plane components; verify etcd index consistency; restart API server |
| **Recovery Validation** | `kubectl get nodes` returns Ready; API server responds; etcd health check green; lease count matches |
| **Operational Ownership** | SRE / Platform team |
| **Monitoring/Alert Dependencies** | etcd exporter; kube-apiserver metrics; alertmanager for control-plane alerts; custom etcd lag alerts |

#### 4. Kubernetes Workers / Nodes

| Field | Content |
|---|---|
| **Critical Dependencies** | kubelet, container runtime (containerd/cri-o), node networking (CNI), disk/FS, kube-proxy |
| **Failure Domains** | Individual node; workloads scheduled on that node affected |
| **Health/Readiness Indicators** | kubelet status; container runtime status; CNI plugin status; disk usage; pod readiness gates |
| **Backup Requirements** | Node root filesystem snapshot (pre-upgrade); runtime state export (if persistent); workload manifests versioned |
| **Recovery Procedure** | Drain node; reboot; rejoin cluster; if OS lost, reimage from golden OS image; verify kubelet config; reapply taints/labels |
| **Recovery Validation** | Node Ready; pods scheduled and running; kube-proxy healthy; CNI operational |
| **Operational Ownership** | SRE / Cluster ops |
| **Monitoring/Alert Dependencies** | node-exporter; kubelet metrics; container runtime metrics; pod disruption budgets |

#### 5. CNI (Container Network Interface)

| Field | Content |
|---|---|
| **Critical Dependencies** | Kernel netfilter, kernel networking stack, IPAM plugin, DNS resolution |
| **Failure Domains** | Node-level or cluster-wide (depending on plugin); all Pod networking affected |
| **Health/Readiness Indicators** | Pod network connectivity; CNI plugin status; IPAM lease availability; network policy evaluation |
| **Backup Requirements** | CNI configuration files; IPAM lease state snapshots; plugin binaries |
| **Recovery Procedure** | Restart CNI plugin daemon; reapply network policies; refresh IPAM leases; replace plugin binary if corrupted; verify overlay network |
| **Recovery Validation** | Pods can reach cluster IP; services are reachable; network policy allows expected traffic; CNI status healthy |
| **Operational Ownership** | Network team / SRE |
| **Monitoring/Alert Dependencies** | CNI plugin metrics; Kubernetes pod network policies; connectivity checks; IPAM exporter |

#### 6. Ceph / Rook-Ceph

| Field | Content |
|---|---|
| **Critical Dependencies** | OSD daemons, MON daemons, MDS daemons, CRUSH map, cluster network, OSD journals |
| **Failure Domains** | Storage layer; data availability impacted; cluster may degrade but not stop serving |
| **Health/Readiness Indicators** | OSD health (HEALTH_OK/HEALTH_WARN/HEALTH_ERR); MON quorum; PG states; MDS status; disk I/O latency |
| **Backup Requirements** | Ceph cluster state; RGW configuration; snapshots of critical data pools; CRUSH map version |
| **Recovery Procedure** | Recover failed OSD from standby; rebalance PGs; add new OSD to cluster; restore from Ceph RGW snapshots if data loss; handle MON quorum loss with keyring restoration |
| **Recovery Validation** | `ceph health OK`; all PGs in active+clean; pool usage matches expected; RGW upload/download test |
| **Operational Ownership** | Storage team / SRE |
| **Monitoring/Alert Dependencies** | Ceph exporter; OSD status; MON quorum alerts; PG state alerts; RGW latency |

#### 7. Rancher

| Field | Content |
|---|---|
| **Critical Dependencies** | Kubernetes cluster(s) managed; etcd of managed clusters; API access; TLS certs |
| **Failure Domains** | Management plane; all managed clusters lose UI/control-plane visibility |
| **Health/Readiness Indicators** | Rancher API responsiveness; UI load; TLS cert validity; etcd health of managed clusters |
| **Backup Requirements** | Rancher etcd snapshot (every 4-6h); Rancher management cluster state; TLS certs and keys |
| **Recovery Procedure** | Restore Rancher etcd from snapshot; verify managed cluster connectivity; regenerate TLS certs if expired; restart Rancher services |
| **Recovery Validation** | Rancher UI loads; managed clusters visible; workloads operational; API access restored |
| **Operational Ownership** | Platform team |
| **Monitoring/Alert Dependencies** | Rancher API metrics; etcd exporter; alertmanager for Rancher alerts; custom health check endpoints |

#### 8. Nexus / Harbor (Container Registry)

| Field | Content |
|---|---|
| **Critical Dependencies** | Underlying storage (disk, S3), TLS certs, database (PostgreSQL for Harbor), token service, artifact metadata |
| **Failure Domains** | Registry layer; push/pull of images fails; CI/CD pipelines blocked |
| **Health/Readiness Indicators** | API responsiveness; storage latency; database connectivity; token service health; image pull-through performance |
| **Backup Requirements** | Registry storage snapshots; Harbor project configuration; PostgreSQL database backup; Trivy cache |
| **Recovery Procedure** | Restore PostgreSQL from backup; restore object storage if needed; reconfigure registry endpoints; reimport metadata; verify image accessibility |
| **Recovery Validation** | Image push/pull test; project metadata restored; token service healthy; storage usage matches expected |
| **Operational Ownership** | DevOps / Platform team |
| **Monitoring/Alert Dependencies** | Registry exporter; PostgreSQL metrics; storage latency alerts; artifact scan status |

#### 9. HAProxy / Nginx / Keepalived

| Field | Content |
|---|---|
| **Critical Dependencies** | Backend services, VIP assignment, TLS termination certs, health check targets |
| **Failure Domains** | Load balancer level; traffic routed away from failed instance; failover to standby |
| **Health/Readiness Indicators** | Process status; health check response; TLS handshake; connection throughput; backend availability |
| **Backup Requirements** | Configuration files; TLS certs/keys; VIP assignment state |
| **Recovery Procedure** | Restart proxy service; verify health check targets; rebalance backend load; if VIP lost, restore Keepalived arp_sync; rotate certs if expired |
| **Recovery Validation** | VIP active on primary; health checks pass; backend services reachable; traffic flows through proxy |
| **Operational Ownership** | Network team / SRE |
| **Monitoring/Alert Dependencies** | Proxy process metrics; health check results; backend service status; Keepalived state changes |

#### 10. Prometheus / Grafana / Alertmanager / Thanos

| Field | Content |
|---|---|
| **Critical Dependencies** | Time-series database (local TSDB or remote); storage for rules; external labels; notification handlers |
| **Failure Domains** | Observability layer; alerts not firing; dashboards unavailable; historical data lost |
| **Health/Readiness Indicators** | TSDB compaction status; rule evaluation latency; Alertmanager receiver connectivity; Thanos querier availability; Grafana datasource health |
| **Backup Requirements** | Prometheus TSDB snapshot (honest export); Alertmanager configuration; Grafana dashboards and alerts provisioning; Thanos sidecar data |
| **Recovery Procedure** | Restore Prometheus from Honest TSDB export; reapply Alertmanager config; reimport Grafana dashboards; restart Thanos components; verify rule evaluation resumes |
| **Recovery Validation** | Metrics appear in Grafana; alerts fire for known conditions; retention policy respected; Thanos storegateway serving range queries |
| **Operational Ownership** | SRE |
| **Monitoring/Alert Dependencies** | node-exporter; process monitoring; alertmanager notification tests; Thanos replication factor |

#### 11. Loki / Fluent Bit

| Field | Content |
|---|---|
| **Critical Dependencies** | Fluent Bit output (Loki, S3, TLS); log collection config; disk space for local buffer |
| **Failure Domains** | Logging layer; logs lost or delayed; debugging capacity reduced |
| **Health/Readiness Indicators** | Fluent Bit forwarder status; Loki query responsiveness; log retention; disk usage on collectors |
| **Backup Requirements** | Fluent Bit configuration; Loki chunks index; custom log labels/tags definition |
| **Recovery Procedure** | Restart Fluent Bit daemon; verify output connectivity to Loki; reapply log parsing rules; if Loki down, restart with `--config-verify`; clear local buffers if corrupted |
| **Recovery Validation** | Log entries appear in Loki; searchable; retention policy; Fluent Bit forwarder healthy; no log loss alerts |
| **Operational Ownership** | SRE / DevOps |
| **Monitoring/Alert Dependencies** | Fluent Bit metrics; Loki query latency; disk usage on collectors; log throughput |

#### 12. Vault / OpenBao / Keycloak

| Field | Content |
|---|---|
| **Critical Dependencies** | Storage backend (Consul/etcd/PostgreSQL); TLS certs; seal status; token renewal |
| **Failure Domains** | Secrets management; authentication fails; services cannot obtain credentials |
| **Health/Readiness Indicators** | Seal status (unsealed); token TTL; authentication success rate; storage backend health; renewal lag |
| **Backup Requirements** | Vault sealed storage; encryption key backup; Keycloak user/realm config; TLS certs and CRL |
| **Recovery Procedure** | Unseal Vault with existing keys; restore encryption key from backup; reinitialize Keycloak from realm backup; rotate TLS certs if compromised; restart services |
| **Recovery Validation** | Vault unsealed; secrets accessible; Keycloak login functional; token renewal within TTL; storage backend healthy |
| **Operational Ownership** | SRE / Security team |
| **Monitoring/Alert Dependencies** | Vault seal status; Keycloak authentication success; storage backend health; token TTL expiry |

#### 13. Argo CD / Ingress / cert-manager

| Field | Content |
|---|---|
| **Critical Dependencies** | Kubernetes API server; etcd; cluster-network-operator; TLS cert issuance; repo server accessibility |
| **Failure Domains** | GitOps drift; ingress traffic unavailable; cert renewal fails |
| **Health/Readiness Indicators** | Argo CD app health; ingress controller responsiveness; cert-manager certificate issuance; repo sync status |
| **Backup Requirements** | Argo CD application definitions; ingress configuration; cert-manager Issuer/Certificate custom resources; Git repo state |
| **Recovery Procedure** | Restore Argo CD server from etcd snapshot; reapply ingress resources; reissue certs via cert-manager; sync Git repo; resolve drift |
| **Recovery Validation** | Argo CD UI loads; apps healthy; ingress routes traffic; certificates valid and auto-renewing; Git sync succeeds |
| **Operational Ownership** | Platform team / SRE |
| **Monitoring/Alert Dependencies** | Argo CD app metrics; ingress controller health; cert-manager webhook; Git repo accessibility; sync controller logs |

#### 14. Security / Admission Policy (OPA/Gatekeeper)

| Field | Content |
|---|---|
| **Critical Dependencies** | Kubernetes API server; OPA sidecar; Gatekeeper controller; Constraint templates; Constraint bindings |
| **Failure Domains** | Admission control; pods may be accepted or rejected based on policy state |
| **Health/Readiness Indicators** | OPA gate health; constraint synthesis; constraint violation count; API server admission latency |
| **Backup Requirements** | Constraint templates; Constraint bindings; OPA server configuration; policy version history |
| **Recovery Procedure** | Restart OPA/Gatekeeper; reapply constraint templates from backup; verify constraint bindings; check API server admission review logs; if policy broke cluster, revert to last known-good policy set |
| **Recovery Validation** | Pods accept/block per policy; OPA health; no admission errors in API server logs; constraint violations logged appropriately; policy audit trail intact |
| **Operational Ownership** | Security team / SRE |
| **Monitoring/Alert Dependencies** | OPA gate metrics; constraint violation alerts; API server admission review queue; policy compilation errors |

---

### Platform-Wide vs Individual Component Recovery

| Aspect | Platform-Wide Recovery | Individual Component Recovery |
|---|---|---|
| **Scope** | Entire cluster or service mesh unavailable | Single node, service, or subsystem |
| **Trigger** | Control plane failure; catastrophic data loss; major network partition | Node crash; service restart; config drift |
| **Recovery Steps** | Restore etcd; rejoin nodes; rebuild control plane; validate cluster-wide health; restart all workloads in order | Restart affected component; restore from component-specific backup; validate local health; reintegrate |
| **Validation** | Full cluster audit; all SLOs within target; all services reachable; error budget assessment | Component-level health checks; dependent services unaffected; no cascading failures |
| **Ownership** | Platform SRE + security + storage leads | Individual component owner; SRE coordination for cluster-level steps |

---

### Cross-Component Monitoring Dependencies

| Dependency | Description |
|---|---|
| **etcd → All K8s components** | Cluster state; all health checks depend on etcd consistency |
| **API Server → Admission, ingress, kubectl** | All operations require API availability |
| **Network → CNI, ingress, service mesh** | All pod communication depends on network plane |
| **Storage → Ceph, Registry, PV/PVC** | All stateful workloads depend on storage availability |
| **Time Sync (NTP) → All components** | Certificate validity; lease timers; distributed tracing timestamps |
| **DNS → Service discovery, ingress** | All FQDN resolution for internal and external services |

---