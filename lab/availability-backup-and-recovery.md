# Availability, Failure Domains and Backup (TASK 006)

## 1. Purpose
Define failure domains, HA targets, backup destinations, and recovery dependencies for the Lab. Do not claim HA merely because multiple replicas exist. All figures are planning estimates.

## 2. Failure domains
| Domain | Lab tolerance | Mitigation |
|---|---|---|
| Physical host | One host loss | Workers spread across hosts; control-plane on separate hosts |
| Hypervisor host | One hypervisor loss | VMs distributed across hypervisors; Ceph OSD on separate physical hosts |
| Rack | Not assumed multi-rack in Lab | Single rack; acknowledge as single point of failure |
| Network | ToS/switch loss | Redundant NICs where hardware allows; document single-switch risk |
| Storage node | One OSD loss | Ceph replica 3; MON quorum (3) |
| Kubernetes control plane | One control-plane loss | etcd quorum (3 members); kube-apiserver behind LB VIP |
| Management cluster | Cluster loss | Independent etcd snapshot + Kubespray rebuild path, **but** per ADR-0025 the restore order is Vault first, then identity (Keycloak), then the Management Cluster — management cluster restore is therefore dependent on Vault being restored first |
| External load balancer | One LB loss | Keepalived VIP Active/Passive across 2 LB servers |
| Repository/registry | Nexus or Harbor loss | Underlying storage backup; image layers mirrored from upstream |
| Identity/secrets | Keycloak or Vault loss | Keycloak: PostgreSQL backup; Vault: Vault storage snapshot + offline unseal material + root token (Velero does not include Vault data) |

## 3. Single points of failure (SPOF) and mitigation
| SPOF | Mitigation option | Residual risk |
|---|---|---|
| Single hypervisor | Add second hypervisor; distribute VMs | Not mitigated in Small Lab |
| Single LB server | Keepalived Active/Passive with 2nd LB | Brief VIP failover window |
| Single Nexus/Harbor | Regular backup of underlying storage; upstream mirror | Restore time > 0 |
| Single etcd (if 1-node) | Use 3-node quorum (default) | N/A with quorum |
| Vault unseal keys | Offline custodian shares | Loss of shares = loss of secrets |
| Keycloak PostgreSQL | Database backup/restore procedure | Restore time > 0 |

## 4. HA vs replication
Multiple replicas or servers do not automatically equal HA. True HA requires:
- Automatic failover (Keepalived VIP, etcd leader election, Ceph MON quorum).
- No single point of failure in the data path.
- Tested recovery procedures.

The Lab should validate HA by simulating failure (lab-safe/staging-only, per P11.7 `testing/ha-failure-recovery-tests.md`), not by counting replicas.

## 5. Backup destinations and recovery dependencies
| Component | Backup destination | Recovery dependency | RTO/RTO class |
|---|---|---|---|
| etcd | Snapshot to off-cluster storage | etcd binary, snapshot file | Hours (illustrative) |
| Kubernetes resources | Velero to object storage (RGW/S3) | K8s API, Velero, object storage | Hours |
| Ceph RADOS | Ceph native backup / filesystem mirror | Ceph cluster, MON quorum | Hours-days |
| Nexus | Underlying storage backup | Nexus app, storage | Hours |
| Harbor | DB + registry storage backup | Harbor, PostgreSQL, object storage | Hours |
| Keycloak | PostgreSQL dump | Keycloak, PostgreSQL | Hours |
| Vault | Vault storage snapshot + offline unseal material + root token | Vault dedicated hosts, unseal custodians | Hours (illustrative) |

RPO/RTO figures in this project are illustrative only (per P11.5) — not production commitments. Do not commit to numeric targets without lab measurement.

## 6. Recovery dependency ordering (recommended)
1. Verify OS layer: network, DNS, NTP, repo connectivity.
2. Verify Kubernetes control-plane: etcd quorum, API server health.
3. Verify CNI: Cilium/CoreDNS ready.
4. Verify storage: Ceph cluster healthy, CSIs registered.
5. Verify platform services: Rancher, Harbor, Argo CD.
6. Verify observability: Prometheus → Alertmanager → Grafana.
7. Verify security: Gatekeeper → Falco → Cosign → Vault/Keycloak.

Do not start recovery at step 5 if step 2 is unhealthy.

## 6.1 Recovery dependency table

| Recovery domain | Recovery dependency | Restore order (per ADR-0025) | Notes |
|---|---|---|---|
| Vault | Vault storage snapshot + offline unseal material + root token | 1st | Vault is on dedicated hosts with integrated Raft (ADR-0016), independent of etcd. Restore before anything that needs secrets. |
| Identity (Keycloak) | PostgreSQL dump | 2nd | Depends on Vault being available for secrets/certs. |
| Management cluster | etcd snapshot + Kubespray rebuild | 3rd | Requires Vault and Keycloak restored first (ADR-0025). |
| Application clusters | etcd snapshot + Kubespray rebuild | 4th | Each cluster rebuilt independently via its Kubespray inventory. |
| Storage (Ceph/Rook) | Ceph native backup / filesystem mirror | Independent | Ceph recovers independently of K8s; CSI provisioning needs CNI + control plane. |
| Repository/registry (Nexus/Harbor) | Underlying storage backup; upstream mirror | Independent | Harbor needs PostgreSQL + storage; Nexus needs underlying storage. |
| Observability | Prometheus TSDB; object storage for Thanos | After control plane | Monitoring depends on K8s API scrape targets. |

## 6.2 High-level recovery sequence by scenario

### Scenario 1 — Management cluster unavailable
Workload clusters keep running (data plane unaffected). Operators can:
- Reach the Workload Cluster API directly via its control-plane VIP (`<LB_VIP_1>`) using `kubectl` with a static admin kubeconfig (break-glass credentials), not via Rancher/Argo CD.
- Authenticate with static admin credentials; Keycloak OIDC is unavailable until the management cluster is restored, so OIDC-based login does not work during the outage.
- Access hypervisor/physical infrastructure management independently (BMC/IPMI, out-of-band network), which is outside the management cluster.
- Inspect and recover control-plane and worker nodes directly via SSH/kubectl on the workload cluster.
- Access bootstrap artifacts and container images from Nexus/Harbor (running on dedicated infrastructure outside the clusters, per ADR-0010) — the management-hosted registry is not a single point of failure for image pulls.
- Access Ceph storage management and recovery interfaces directly (Ceph is independent of the management cluster).
- Restore the Management Cluster later: restore Vault first (secrets), then Keycloak (identity), then rebuild the Management Cluster via Kubespray etcd snapshot. Workload cluster recovery is **not** dependent on the Management Cluster.

### Scenario 2 — Workload cluster unavailable
The independent Management Cluster remains available and can:
- Provide Rancher management, Argo CD GitOps, Keycloak identity, and observability.
- Access the workload infrastructure API endpoint (`<LB_VIP_1>`) when the control plane is healthy.
- Support recovery by re-applying Argo CD applications and Rancher cluster registration — but Rancher and Argo CD **cannot** replace Kubernetes control-plane recovery. If the workload cluster's etcd/control plane is lost, it must be rebuilt via its own Kubespray inventory and etcd snapshot; Argo CD only re-deploys applications onto an already-recovered cluster.

### Scenario 3 — Both clusters unavailable
Independent recovery path:
- Hypervisor or bare-metal access via BMC/IPMI (out-of-band, outside both clusters).
- Independent DNS/NTP and network connectivity (confirm `<MGMT_SUBNET>`, DNS, NTP are reachable from the recovery host).
- External or independently accessible backups (etcd snapshots, Ceph backups, Nexus/Harbor artifact mirrors stored off-cluster).
- Offline repository and registry bootstrap artifacts (OS images, Kubespray inventory, control-plane container images) on the bootstrap node/internal mirror.
- Direct Kubernetes recovery: rebuild each control plane via Kubespray `kubeadm init` + etcd snapshot restore, then CNI, then storage.
- Direct storage recovery: restore Ceph via its native tools; Rook-Ceph only after the control plane + CNI are healthy.

Rancher cannot recover a completely unavailable Kubernetes API server. Argo CD cannot recover a cluster when its API server is unavailable. Management-plane recovery, Kubernetes control-plane recovery, storage recovery, and application recovery are distinct and must not be circularized.

## 7. Open questions

1. What backup target (NFS, S3, RGW, external object store) is available for the Lab?
2. Is there an existing backup schedule/retention policy to align with?
3. Who owns etcd snapshot scheduling and restoration testing?
4. Is backup restoration tested on a disposable lab cluster, or never?
