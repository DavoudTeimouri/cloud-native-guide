# Vault/OpenBaa Architecture

## Deployment Modes

| Mode | Description | Use Case |
|---|---|---|
| **Dedicated Linux hosts (3-node)** | Standalone Vault processes on separate VMs/hosts, each running Vault agent in Raft mode. Independent of Kubernetes lifecycle; unseal path does not depend on the cluster. | Recommended production mode — no circular dependency between cluster and secrets. |
| **Inside Management Cluster** | Vault deployed as a Deployment/StatefulSet within the management Kubernetes cluster. HA via built-in Raft storage. | Cheaper, Helm-managed, but cluster loss = secret loss; unseal may require the cluster available. |
| **Kubernetes on a separate small cluster** | Vault runs on a dedicated small K8s cluster. | Middle ground if host count is constrained; still couples secrets to K8s lifecycle. |

**Decision**: Deploy Vault on 3 dedicated Linux hosts outside the Management Cluster (ADR-0025). This eliminates circular dependencies and makes the unseal path independent of cluster availability.

### Topology (3-node Raft)

```
vault-a (active) ── raft ── vault-b (standby) ── raft ── vault-c (standby)
      │
      └─ File storage backend + periodic snapshot to S3 (Ceph RGW) or offline media
```

- One active node, two standby nodes in Raft group.
- Storage backend: integrated Raft (default) with snapshots exported to object storage for disaster recovery.
- TLS on port 8200 for all client communication.

## Storage Backends

| Backend | Characteristics | Recommendation |
|---|---|---|
| **Integrated Raft** | Built-in consensus storage; 3-node cluster provides HA. Snapshots exported to object storage. | Default and recommended for most deployments. |
| **File system** | Simple start-up; not HA. Use only for dev/testing. | ❌ Production |
| **Consul** | External KV store for Vault secrets; requires separate Consul cluster. | Use only if integrating with existing Consul. |
| **S3-compatible (Ceph RGW)** | Periodic snapshot replication to object storage. Enables offline recovery. | ✅ Recommended for DR snapshot storage. |

### Snapshot Strategy

- **Automated snapshots**: `vault operator raft snapshot save` triggered hourly via cron.
- **Retention**: Keep 7 daily + 4 weekly + 6 monthly snapshots offline.
- **Offline storage**: Snapshots copied to S3 (Ceph RGW) or removable media; not in the same region as running nodes.
- **Verification**: `vault operator snapshot-verify` after each snapshot.

## HA Configuration

### 3-node Raft Quorum

- Minimum of 3 nodes required for quorum (`N` nodes, quorum = `⌊N/2⌋ + 1`).
- Node roles: one active, remaining standbys.
- Standby election: if active node fails, a standby is promoted within ~30 seconds.

### TLS

- Server certificate signed by internal CA.
- Client certificate pinning for automated integrations.
- Port 8200 (HTTPS) for API traffic; port 8201 (HTTPS) for telemetry.

### Resource Minimums

| Component | CPU | Memory | Storage |
|---|---|---|---|
| Each Vault node | 2 vCPU | 4 GB | 10 GB (root) + snapshot storage |
| Snapshot host (optional) | 2 vCPU | 4 GB | 100 GB (object storage cache) |

### Resource Limits

- Set memory limits to prevent OOM kills on noisy neighbors.
- CPU limits proportional to request count; enable `maxrequests` per-token to throttle burst.

## Unseal Strategies

| Strategy | Description | Key Management |
|---|---|---|
| **Shamir's Secret Sharing (3 of 5)** | 5 key shares generated; any 3 can unseal. Shares held by separate custodians. | Offline; documented in `secrets-management/vault/recovery/`. |
| **Auto-unseal KMS** | Vault auto-unseals using cloud KMS (AWS KMS, Azure Key Vault, GCP KMS). | Keys stored in KMS; no plaintext keys on disk. |
| **Hybrid** | Shamir shares as fallback; auto-unseal primary. | Both paths documented; tested quarterly. |

**Break-glass unseal**: Shamir key shares (3 of 5) held offline by separate custodians; or a KMS auto-unseal device if available. Both are documented in `secrets-management/vault/recovery/`.

### Unseal Rotation

- Rotate unseal keys annually or after any suspected compromise.
- Regenerate shares; redistribute to custodians.
- Test rotation in staging before production.

## Production Sizing Guidelines

### Core Formula

```
nodes = 3 (minimum for Raft quorum)
cpu_per_node = max(2, ceil(requests_per_second * 0.5)) vCPU
mem_per_node = max(4 GB, requests_per_second * 1 GB) + overhead
snapshot_storage = 100 GB per node (object storage cache)
```

### Example sizing

| Load (auth ops/sec) | Nodes | CPU per node | Memory per node | Snapshot storage |
|---|---|---|---|---|
| < 10 | 3 | 2 vCPU | 4 GB | 100 GB |
| 10–50 | 3 | 4 vCPU | 8 GB | 200 GB |
| 50–200 | 5 | 6 vCPU | 12 GB | 300 GB |
| > 200 | 7+ | 8+ vCPU | 16+ GB | 500 GB+ |

### Sizing Checklist

- [ ] 3+ nodes for Raft quorum
- [ ] CPU: 2 vCPU minimum per node, scale with auth ops/sec
- [ ] Memory: 4 GB minimum per node, scale with auth ops/sec
- [ ] Storage: 10 GB root + 100 GB snapshot cache per node
- [ ] TLS certificates provisioned and renewed automatically
- [ ] Snapshot cron job configured and verified offline
- [ ] Unseal strategy (Shamir or KMS) documented and tested
- [ ] Audit logging shipped to centralized platform
- [ ] Monitoring alerts for: seal status, leadership changes, storage usage, auth failures, snapshot freshness

## Identity Integration

| Consumer | Auth Method | Notes |
|---|---|---|
| Human admins | OIDC via Keycloak | Group → Vault role mapping |
| Ansible automation server | AppRole or JWT | Prefer JWT/OIDC if identity flow allows |
| GitLab CI jobs | OIDC (GitLab ID token) → Vault JWT auth | Fallback = AppRole with short TTL |
| Argo CD | Kubernetes auth (SA token) | Vault's own K8s auth; alternate = External Secrets Operator |
| Applications (in-cluster) | K8s auth (SA token) | Least-privilege per app SA |
| Workload identity (K8s 1.24+ projected tokens) | Vault K8s auth | Short-lived, no static SA secret |

**Key point**: Directory integration is application-level and never automatic. Each service gets its own explicit OIDC or LDAP procedure — see `identity/directory-integration.md`.

## Secret Categories and Storage

| Category | Vault path (example) | Delivery | Rotation |
|---|---|---|---|
| Linux/root creds | `secret/infra/linux/*` | Ansible fetch at runtime | 90d |
| SSH keys | `secret/infra/ssh/*` | Ansible + Vault SSH agent signing | 90d / on use |
| Kubespray bootstrap creds | `secret/infra/kubespray/*` | Ansible vault lookup | 90d |
| K8s app secrets | `secret/apps/<ns>/*` | External Secrets Operator → K8s Secret | 30d |
| DB creds | `database/creds/<role>` | Dynamic (Vault DB engine) | 24h lease |
| Ceph keys | `secret/infra/ceph/*` | Ansible → Ceph | 180d |
| GitLab CI creds | `secret/ci/*` | GitLab CI masked variables or OIDC | 30d |
| Harbor/Nexus auth | `secret/registry/*` | Ansible, containerd registries.conf | 90d |
| Argo CD repo creds | `secret/gitops/*` | Argo CD repo creds via API (not in Git) | 90d |
| Monitoring creds | `secret/observability/*` | External Secrets | 90d |
| Keycloak client secrets | `secret/identity/*` | Ansible / External Secrets | 90d |
| TLS certs + keys | `pki/issue/<role>` | cert-manager via Vault PKI | 30d, auto-renew |
| GPU service creds | `secret/ai/*` | External Secrets | 90d |
| Model API keys | `secret/ai/models/*` | External Secrets | 90d |
| Backup encryption keys | `secret/backup/*` | Ansible, Velero | 180d |
| Root CA private key | `pki/root/ca` (offline storage recommended) | Offline only | long, rotate by re-issue |

## Dynamic Secrets and Rotation

- **Database credentials**: Vault DB engine issues username/password with TTL (default 24h). Application must re-read the credential on renewal. Vault has no control over apps that cache credentials forever — verify per application.
- **SSH certificates**: Vault SSH signer issues short-lived certs; host/user trust against a CA. Requires `sshd` `TrustedUserCAKeys` configuration.
- **PKI**: Vault PKI issues and renews certs; cert-manager consumes it. Root CA private key stored offline; intermediate held in Vault.
- **Cloud/registry**: where the upstream supports dynamic tokens, use them; otherwise rotate static tokens on a schedule.
- **Revocation**: revoke leases, remove policies, rotate the underlying credential. For static credentials, rotation is an external automation action (Ansible job) — not transparent to the application.
- **After compromise**: revoke lease, rotate the credential at the source, re-deploy dependents, verify the new value is in use.

## Secret Delivery to Kubernetes — Comparison

| Method | Mechanism | Persisted in etcd | Rotation behavior | App reload needed | Complexity | Notes |
|---|---|---|---|---|---|---|
| Vault Agent Injector | Sidecar writes file, syncs on renewal | Only if app uses K8s Secret; agent uses memory/file | Agent renews and rewrites file | App must re-read file or SIGHUP | Med | Best for file-based apps |
| Vault Agent templates (no injector) | DaemonSet/Deployment writes templated file | No | Same | Same | Med | Good for static config |
| Secrets Store CSI Driver | Mounts secret as file via CSI | No (unless synced) | Driver refreshes on renew | App must re-read | Med | Needs Vault CSI provider |
| External Secrets Operator | Syncs Vault → K8s Secret | **Yes** | ESO refreshes on interval | App must restart or reload | Low | Operator-agnostic; adds etcd exposure |
| Direct app → Vault API | App authenticates and reads | No | App handles renewal | App-native | Varies | No extra infra; more app work |
| K8s native Secret | Plain etcd secret | **Yes** | Manual | Yes | Low | Baseline only; no dynamic |

**Explicit statement**: External Secrets Operator does **not** eliminate the etcd persistence risk. It centralizes the source of truth and rotation, but the synchronized value still lands in etcd and is readable by anyone with RBAC on that Secret in that namespace. Mitigation: namespace-scoped RBAC, separate namespaces per team, encrypt etcd at rest with a KMS-backed key, restrict `get secrets` audit logging.

## PKI

| Element | Owner | Location |
|---|---|---|
| Root CA (offline) | Vault PKI root | Encrypted Vault entry + offline backup; ideally on separate host/media |
| Intermediate CA | Vault PKI intermediate | Vault only, auto-expiry renewal policy |
| Server certs (ingress, services) | cert-manager | Kubernetes TLS Secrets |
| Client certs (Vault auth, mesh) | cert-manager or Vault | Depends |
| K8s internal PKI (apiserver, kubelet) | Kubespray | `/etc/kubernetes/pki` per node, rotated by Kubespray workflow |

Root CA rotation: issue new intermediate from root, switch issuance, wait for leaf expiry, revoke old intermediate. This is a multi-step, downtime-sensitive process — not a one-line operation. Document the runbook in `secrets-management/pki/root-ca-rotation.md`.

## Recovery

- **Vault backup**: snapshot storage + `vault operator raft snapshot save`; store offline.
- **Unseal**: Shamir shares offline, or auto-unseal KMS.
- **Restore runbook**: `secrets-management/vault/recovery/restore.md`.
- **Recovery order**: Vault first (unseal), then identity (Keycloak), then Management Cluster, then Application Clusters. Argo CD may re-sync applications once Vault is back.
- **Kubernetes backup (Velero)**: does **not** include Vault's data unless Vault runs in-cluster and its storage is included. Our model keeps Vault outside the cluster, so Vault backup is a separate, mandatory procedure.

## Monitoring and audit

**Monitored**: seal status, cluster leadership, replication health, storage usage, request latency and error rate, auth failures, lease/token expiry, certificate expiry, audit device health, backup freshness, rotation failures.

**Audit**: file or syslog device shipped to the logging platform. Audit logs must never contain secret values — Vault's audit log contains request/response metadata; HMAC-request-response mode is available to further protect values.

**Never log**: secret values, tokens, private keys, request payloads containing credentials.

---

*Document version: 1.0 — reviewed quarterly. See `compatibility/version-matrix.md` for license check dates and version tracking.*
