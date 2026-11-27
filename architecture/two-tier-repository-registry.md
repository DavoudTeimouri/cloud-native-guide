# Two-Tier Repository & Registry Architecture (TASK 004-P11.2)

## 1. Overview

This document defines a two-layer repository and registry architecture for restricted and offline environments. The architecture separates **External Upstream** (controlled Internet access) from **Internal Repository/Registry Manager** (internal distribution), with a stable service endpoint layer that provides consistent DNS-addressable endpoints regardless of backend changes.

The design explicitly does **not** claim full air-gap readiness. It assumes a connected staging path for artifact acquisition and synchronization, with controlled, audited transfer into the offline environment.

---

## 2. Layer 1 — External Upstream (Controlled Internet Access)

### 2.1 Responsibilities

- Connect to public OS package repositories and public container registries on behalf of the internal environment.
- Retrieve **approved** artifacts only, as defined by an allowlist.
- Cache/sync packages and images from approved upstream sources.
- Apply controlled sync policies (scheduled, on-demand, or pull-based).
- Verify checksums and signatures where supported by the upstream source.
- Maintain sync logs and audit events for every sync operation.
- **Prevent internal nodes from direct public Internet access**; all egress must flow through the External Upstream layer.

### 2.2 Connectivity & Firewall Rules

| Direction | Source | Destination | Ports | Purpose |
|---|---|---|---|---|
| Outbound | External Upstream host | Public package repos (yum, apt, PyPI, npm) | 80, 443 | Retrieve packages |
| Outbound | External Upstream host | Public container registries (docker.io, ghcr.io, quay.io, registry.k8s.io) | 443 | Pull container images |
| Outbound | Internal clients | External Upstream (restricted) | 80, 443 | Indirect access via proxy |
| Inbound | Public Internet | External Upstream | 80, 443 | Artifact sources |
| Deny | Internal nodes | Public Internet | All | Egress prevention |

### 2.3 Trust Boundaries

- **External Upstream** sits in a DMZ or hardened subnet with egress limited to approved URLs/IP ranges.
- **Internal nodes** (worker nodes, CI runners, automation hosts) have **no outbound Internet access**. All artifact retrieval must go through the Internal Repository/Registry Manager.
- Sync is performed only by the External Upstream host, which is the sole permitted connector to public registries.

### 2.4 Sync Flow

1. **Upstream sync initiation** (scheduled or on-demand) from the External Upstream host.
2. **Fetch** approved artifacts from public registries/repositories.
3. **Verify** checksums (SHA-256, GPG/RPM signatures, deb checksums) where available.
4. **Verify** signatures (cosign, notary, Docker Content Trust) where upstream provides them.
5. **Store** verified artifacts in the External Upstream's local cache.
6. **Publish** approved artifacts to the Internal Repository/Registry Manager over the internal network.
7. **Record** sync status, checksums, signatures, and audit events in a durable log.

### 2.5 Checksum and Signature Verification

| Capability | Native | Needs additional component | Needs commercial edition | Unverified |
|---|---|---|---|---|
| SHA-256 checksum verification | ✓ (all package managers) | — | — | — |
| GPG/RPM signature verification | ✓ (yum/dnf) | — | — | — |
| Debian .dsc/.changes signature | ✓ (apt) | — | — | — |
| cosign signature verification | ✓ (OCI images) | — | — | — |
| Notary/Signix image signing | — | ✓ | — | — |
| SBOM/provenance verification | — | ✓ | — | — |

### 2.6 Sync Failure Handling

- Sync failures are logged with error details and upstream HTTP status code.
- Retry policy: exponential backoff, maximum 5 attempts, then alert.
- On permanent failure, the sync is marked **FAILED** in the audit log and the artifact is flagged **PENDING** in the internal matrix.
- Recovery: manual re-trigger or investigate upstream availability.

---

## 3. Layer 2 — Internal Repository/Registry Manager

Layer 2 consists of two logical sub-layer types: **Proxy/Cached** and **Hosted**. They serve different use cases and are not interchangeable.

### 3.1 Proxy / Cached Repositories

**Use case**: Proxy approved public repositories/registries so that internal clients never touch the public upstream.

| Aspect | Description |
|---|---|
| **Purpose** | Cache mirrors of approved public repos/registries at predictable internal endpoints. |
| **Upstream connection** | Outbound only from the proxy component; internal clients are **prohibited** from reaching public upstream directly. |
| **Artifact flow** | Public upstream → External Upstream proxy → Internal cached repo → Internal clients. |
| **OCI registry access** | Harbor proxy-cache from upstream (connected staging only). |
| **Package formats** | Nexus proxies for rpm/deb/pypi/npm/helm/raw. |
| **Predictable endpoints** | `/repository/rpm-oraclelinux/`, `/repository/deb-ubuntu/`, `/repository/pypi/`, etc. |
| **Authz propagation** | Authz headers from upstream are not forwarded; internal auth is managed locally. |
| **Checksum behavior** | Proxy preserves upstream metadata checksums; Nexus re-generates repomd for RPM/DEB. |
| **Large image uploads/downloads** | Not applicable — proxy is read-only from the client perspective. |
| **Timeouts / body-size limits** | Configured per-proxy; Nexus defaults apply, adjustable per repository. |
| **Health checks / backend failover** | Proxy component reports health; failover to secondary proxy node. |
| **HA / load balancing** | DNS round-robin or LB VIP pointing to proxy pair; each node caches independently. |
| **Logging / metrics / alerting** | Sync events, cache hit/miss, error rates. |
| **Backup / recovery** | Repository metadata backed up; artifact blobs stored in attached storage. |

**Proxy vs Hosted distinction**: Use **Proxy** when the goal is to mirror an approved public source. Use **Hosted** when the goal is to allow internal teams to publish and consume their own artifacts.

### 3.2 Hosted Repositories / Registries

**Use case**: Internal teams publish and consume their own artifacts, separated by team/project/namespace.

| Aspect | Description |
|---|---|
| **Purpose** | Internal teams publish/consume own artifacts; separation by teams/projects/namespaces. |
| **RBAC / service-accounts** | Per-namespace or per-project roles: read, write, delete, admin. Service-accounts for CI pipelines. |
| **Quotas** | Storage quota per project/namespace (e.g., max GB per team). |
| **Retention / cleanup** | Configurable retention policies: keep N versions, keep versions older than X days, or immutability tags. |
| **Audit logging** | Every read, write, and delete operation logged with user/service-account, artifact, and timestamp. |
| **Backup / restore** | Daily snapshots of registry database + artifact blobs; point-in-time restore tested quarterly. |
| **HA / failure recovery** | Active-passive or active-active cluster; VIP failover; state replication for Nexus; Harbor replication support. |
| **Image lifecycle / artifact ownership** | Ownership tracked per project; lifecycle policies auto-delete unused artifacts after grace period. |
| **OCI compatibility** | Full OCI API support: push, pull, delete, tag, manifest, blob listing. |
| **Large image uploads/downloads** | Supported with configurable chunked upload and body-size limits (Harbor: up to 10GB per blob). |
| **OCI Registry API compatibility** | Native — Harbor implements the full OCI Registry API (v2). |
| **Package metadata / checksum behavior** | Nexus generates repomd, group metadata, and checksum files for rpm/deb/pypi/npm. |
| **Timeouts / body-size limits** | Nexus: adjustable per repository; Harbor: chunked upload for large OCI blobs. |
| **Health checks / backend failover** | Harbor: `/health` and `/api/v2.0/health` endpoints; Nexus: JMX/REST status. |
| **Logging / metrics / alerting** | Structured logs, Prometheus metrics, alert rules for quota exhaustion, failed auth. |
| **Backup / recovery** | Harbor: offline export/import, database snapshot; Nexus: blobstore backup, configuration export. |

### 3.3 Layer 2 Summary: Proxy vs Hosted

| Decision factor | Proxy / Cached | Hosted / Registry |
|---|---|---|
| Who owns the artifact | Approved public upstream | Internal team/project |
| Direction of flow | Inward (public → internal) | Bidirectional (team → internal, internal → team) |
| Authz model | Read-only from internal; authz managed upstream | Per-project/namespace RBAC |
| Quotas | Not typically enforced | Enforced per project/namespace |
| Retention | Mirror of upstream policy | Configurable lifecycle policies |
| API compatibility | Partial — metadata proxying | Full OCI Registry API (Harvest) or package-manager native (Nexus) |
| Client access pattern | `internal.repo/pkg` (never touches upstream) | `internal.registry/team/project` |

---

## 4. Stable Service Endpoint Layer (Reverse Proxy)

A reverse proxy (HAProxy or Nginx) provides a **stable service endpoint layer** in front of the actual backend repository/registry nodes. All internal consumers use stable DNS names, not backend hostnames.

### 4.1 Core Properties

| Capability | Description |
|---|---|
| **Stable DNS names** | `nexus.internal`, `harbor.internal`, `harbor.internal/oci/`, `harbor.internal/charts/`, `harbor.internal/platform/`, etc. DNS CNAME records point to the LB VIP; backend IPs may change without client impact. |
| **TLS termination / passthrough** | TLS termination at the reverse proxy; certs managed by internal CA. Passthrough mode available for end-to-end TLS to the backend if required. |
| **Cert trust / renewal** | Internal CA signs proxy certs; renewal automated via short-lived certs (e.g., Cert-Manager with internal CA). Client trust stores trust the internal CA. |
| **Authz propagation** | Authz headers (e.g., X-Forwarded-Auth, correlation IDs) are preserved and forwarded to the backend. |
| **Path preservation / rewrite** | Paths are preserved through the proxy (e.g., `/repository/rpm-oraclelinux/...`). Reverse proxy rewrite rules map stable paths to backend node paths. |
| **HTTP methods / headers / streaming** | Full HTTP method support; custom headers forwarded; streaming support for large OCI blobs. |
| **OCI Registry API compatibility** | Proxy preserves OCI API paths (manifests, blobs, tags, v2/status). Large image uploads/downloads work through the proxy with appropriate body-size limits. |
| **Package metadata / checksum behavior** | Proxy preserves `repomd.xml`, `content.json`, `metadata.json`, and checksum files. |
| **Timeouts / body-size limits** | Configurable at the proxy layer; defaults: 30s connect, 300s read, 100MB max body (adjustable). |
| **Health checks / backend failover** | Proxy checks `/health` or `/service/rest/v1/status` on each backend; failed backends are removed from rotation immediately. |
| **HA / load balancing** | HAProxy/Nginx pair in VRRP/keepalived configuration; LVS or cloud LB VIP; round-robin or least-connections scheduling. |
| **Logging / metrics / alerting** | Proxy access logs, response time metrics, error rates; alert on 5xx rate > 1% or sustained latency > 2s. |
| **Backup / recovery** | Proxy config is declarative (HAProxy cfg, Nginx conf); recovery re-proxy from backed-up config + current backend state. |

### 4.2 Backend Migration Contract

- **Requirement**: Backend migration must not require mass client changes if the endpoint contract is preserved.
- **Contract elements**: DNS name, TLS, API surface (HTTP methods, paths, response codes), authz mechanism.
- **Migration path**: Add new backend nodes, update DNS CNAME, drain old nodes. Clients continue using the same stable DNS name.
- **Verification**: End-to-end pull/install test from a clean client using the stable endpoint after migration.

---

## 5. Product Responsibilities

The following table maps capabilities to products. **"Native"** means the product supports it out of the box. **"Needs additional component"** means a plug-in, extension, or secondary product is required. **"Needs commercial edition"** means the feature is restricted to the commercial/paid version. **"Unverified"** means the capability has not been validated in this architecture.

| Capability | Nexus Repository | Harbor | Reverse Proxy (HAProxy/Nginx) |
|---|---|---|---|
| **OS package repo management** | | | |
| rpm/deb proxy/cache | Native | — | Native (preserves metadata) |
| rpm/deb hosted/published | Native | — | — |
| Language/package repos | | | |
| PyPI proxy/cache | Native | — | Native |
| PyPI hosted/published | Native | — | — |
| npm proxy/cache | Native | — | Native |
| npm hosted/published | Native | — | — |
| pypi/npm hosted/published | Native | — | — |
| Go modules proxy/cache | Native | — | Native |
| **OCI image proxy/cache** | | | |
| OCI proxy/cache | — | Native (Harbor proxy) | Native (path preservation) |
| OCI hosted/published | — | Native | — |
| **Internal hosted OCI publishing** | | | |
| Team/project namespace isolation | — | Native (Harbor projects/teams) | — |
| RBAC / service-accounts | — | Native | — |
| Quotas | — | Needs commercial edition (Harbor Enterprise) | — |
| Retention / cleanup | — | Native (lifecycle policies) | — |
| Audit logging | — | Native | — |
| Backup / restore | — | Native (export/import) | Config files |
| HA / failure recovery | — | Native (replication) | Native (VRRP/keepalived) |
| Image scanning / signing | — | Native (Trivy, Notary) | — |
| Image lifecycle / artifact ownership | — | Native | — |
| **Stable endpoint / traffic management** | | | |
| Stable DNS names | — | — | Native |
| TLS termination / passthrough | — | — | Native |
| Cert trust / renewal | — | — | Native (internal CA) |
| Authz propagation | — | — | Native |
| Path preservation / rewrite | — | — | Native |
| HTTP methods / headers / streaming | — | — | Native |
| OCI Registry API compatibility | Partial (via proxy) | Native | Native |
| Large image uploads/downloads | — | Native | Native (with body-size limits) |
| Package metadata / checksum behavior | Native | Partial (via proxy) | Native |
| Timeouts / body-size limits | Native | Native | Native |
| Health checks / backend failover | Native | Native | Native |
| HA / load balancing | Native (cluster) | Native (replication) | Native (VRRP/keepalived) |
| Logging / metrics / alerting | Native | Native | Native |
| Backup / recovery | Native | Native | Config files |

**Notes on product assignments**:
- **Nexus Repository**: Native capability for OS package management (rpm, deb, pypi, npm, go), language/package repos, and raw artifact storage. Proxy mode for public repos. Hosted mode for internal team packages. Checksum and metadata generation is native.
- **Harbor**: Native capability for OCI image proxy/cache, internal hosted OCI publishing, team/project namespace isolation, RBAC, image scanning, signing, lifecycle/artifact ownership, large image uploads/downloads, OCI Registry API compatibility, HA/replication, logging/metrics/alerting, backup/restore. Quotas require Harbor Enterprise edition.
- **Reverse Proxy (HAProxy/Nginx)**: Native capability for stable service endpoint layer — TLS termination, cert trust/renewal, authz propagation, path preservation/rewrite, HTTP methods/headers/streaming, OCI Registry API compatibility, large image uploads/downloads, package metadata/checksum behavior, timeouts/body-size limits, health checks/backend failover, HA/load balancing, logging/metrics/alerting. Backup is config-file based.

---

## 6. Controlled Upstream Sync & Supply Chain

### 6.1 Approved Upstream Sources

- All upstream sources are defined in an **allowlist** managed by the Platform Team.
- Upstream sources are verified for integrity before artifacts are accepted.
- No arbitrary Internet fetch from internal nodes; all fetches go through the External Upstream host.

### 6.2 Sync / Cache on External Upstream

1. **External Upstream host** initiates sync from approved upstream sources (public registries, package repos).
2. **Artifacts are cached** in the External Upstream's local repository/registry.
3. **Checksum verification**: SHA-256 checksums are validated for every artifact. For RPM, GPG signature verification is performed. For DEB, `.dsc` and `.changes` signature verification. For OCI images, digest verification (`sha256:` in manifest).
4. **Signature verification**: where upstream provides signatures (cosign for OCI, GPG for RPM, apt-key for DEB), these are validated. **Integrity** (checksum) confirms the file has not been altered; **authenticity** (signature) confirms the source.
5. **Trust management**: integrity is verified by checksum; authenticity is verified by signature. If only a checksum is available, integrity is confirmed but authenticity is unverified and the artifact is marked **AUTHENTICITY_UNVERIFIED** in the audit log.

### 6.3 Transfer to Internal

- Approved artifacts are transferred from External Upstream to the Internal Repository/Registry Manager over the **internal network only** (no public Internet path).
- Transfer methods: `skopeo copy` for OCI images, `curl --upload-file` for Nexus packages, `helm push` for charts.
- Artifact allowlists are enforced at the transfer step — only allowlisted versions/names are transferred.

### 6.4 Publish into Internal Repository/Registry Manager

- Transferred artifacts are published into the appropriate internal repository/registry (Proxy cached or Hosted).
- **Validate internal availability+metadata**: pull test from a client node; verify metadata is readable (`repomd.xml` for RPM/DEP, `index.json` for PyPI, OCI manifest for images).
- **Record sync status + audit events**: every sync operation records:
  - Artifact name + version
  - Upstream source URL
  - SHA-256 checksum
  - Signature status (verified/unverified/trust root)
  - Sync timestamp
  - Sync result (SUCCESS/FAILED/SKIPPED)
  - Target repository/registry path

### 6.5 Artifact Allowlists, Version Pinning, and Immutable Ref

| Concept | Definition |
|---|---|
| **Allowlist** | Explicit list of allowed artifact names, patterns, and versions. Maintained in the artifact matrix. |
| **Version pinning** | Artifacts are referenced by exact version (e.g., `python:3.11-slim`, `nginx:1.28.0`, `harbor.internal/oci/app:1.2.3`). No `latest` tags allowed in production. |
| **Immutable refs** | Docker/OCI digests are immutable; once published, an image/digest cannot be overwritten. Nexus repo versions are immutable once released. |
| **Digest-based OCI references** | `harbor.internal/oci/owner-repo@sha256:<digest>` — the digest is the authoritative reference, not the tag. |

### 6.6 Sync Failure Handling, Retry, and Recovery

- **Sync failure**: any non-2xx response from upstream, checksum mismatch, or signature failure.
- **Retry policy**: exponential backoff, max 5 attempts, 30s minimum interval. Failures are logged per-attempt.
- **Recovery**: manual re-trigger from the External Upstream host, or automatic re-sync on the next scheduled window. If the upstream is unavailable for an extended period, the artifact remains **PENDING** in the matrix and is flagged for manual review.

### 6.7 Promotion Between Environments

- Artifacts flow: **Upstream → External Upstream → Internal Repository/Registry → Client**.
- Promotion between environments (e.g., staging → production) is done by **re-publishing** the artifact to the target repository/registry; the artifact is never "promoted" in-place to avoid unintended side effects.
- Each environment has its own repository/registry path; a production artifact is a separate entity from a staging artifact, even if they share the same name/version.

---

## 7. Trust Boundary Section

```
+----------------------+          +----------------------+          +----------------------+
|  Public Internet     |          |   External Upstream  |          |   Internal Network   |
|  (untrusted)         |          |  (controlled egress) |          |  (trusted, offline)  |
+----------+-----------+          +----------+-----------+          +----------+-----------+
           |                                  |                                  |
           |  egress ONLY through approved    |  all artifact flow through      |
           |  URL/IP ranges only              |  Internal Repository/Registry   |
           v                                  v                                  v
+----------------------+          +----------------------+          +----------------------+
|  Public Registries   |          |  Public Repos        |          |  Nexus Repository    |
|  (docker.io, ghcr.io|          |  (yum, apt, PyPI,   |          |  (rpm/deb/pypi/npm)  |
|   quay.io, etc.)    |          |    npm, go)          |          |  Hosted + Proxy      |
+----------------------+          +----------------------+          +----------+-----------+
                                                  |              |
                                                  |              +--------->|  Harbor            |
                                                  +-------------->|  (OCI images)      |
                                                               +----------+-----------+
                                                                  Proxy + Hosted     |
                                                                       +----+------+
                                                                        |    |
                                                                        v    v
                                                                   Stable Service   Endpoint Layer
																	 (Reverse Proxy)
																	 HAProxy / Nginx
																	 stable DNS,
																	 TLS, authz,
																	 path preservation,
																	 load balancing,
																	 health checks,
																	 metrics/alerting
```

**Trust boundary summary**:
- **Public Internet** → untrusted; egress is filtered and monitored.
- **External Upstream** → trusted only for approved artifact retrieval; all outbound Internet access is from this host only.
- **Internal Network** → partially trusted (micro-segmented); no node has direct public Internet access; workloads and services must authenticate/authorize each service call even within the internal network; repository/registry backends enforce RBAC regardless of caller network location.
- **Stable Service Endpoint Layer** → authenticates and authorizes traffic between internal consumers and repository/registry backends; TLS ensures confidentiality; authz propagation enforces policies; backend migration is transparent if the endpoint contract is preserved.

---

## 9. Secrets Management & CI Authentication

No repository/registry credential is stored in source-controlled plaintext. All internal consumers authenticate using short-lived tokens or OIDC federation.

| Credential type | Storage | Rotation | Notes |
|---|---|---|---|
| Harbor robot account token | Secrets Manager / Vault | Every 90 days or on compromise | Short-lived; scoped to specific project |
| Nexus repository auth token | Secrets Manager / Vault | Every 90 days or on compromise | Scoped to specific repo |
| Internal CA private key | Offline (Vault PKI root); intermediate online | Per CA policy | Root kept offline |
| CI pipeline push/pull credential | OIDC federation (GitHub Actions / GitLab CI OIDC) | Per-job ephemeral | No long-lived keys stored |
| Reverse proxy TLS leaf cert | Cert-manager with internal CA | Auto-renewed (short-lived, e.g. 7–30 days) | Revocation via CRL/OCSP or automatic re-issue |

**Rules**:
- Never store Harbor/Nexus credentials, auth tokens, or admin passwords in Git, images, or logs.
- CI pipelines push/pull via OIDC-federated service accounts (e.g., GitHub Actions `id-token: write` → Harbor/Nexus robot account mapped by OIDC claim).
- Human operators use short-lived service-account tokens; shared admin passwords are prohibited.
- External Upstream host holds its own registry credentials for upstream pulls; these are never shared with internal clients.

## 10. External Upstream Redundancy & Monitoring

**Risk**: External Upstream is the single egress point to public registries. If compromised or unavailable, artifact acquisition halts.

| Mitigation | Description |
|---|---|
| Redundant egress hosts | Minimum two External Upstream hosts in different failure zones; sync logs replicated between them. |
| Monitoring | Alert on sync failure rate > 1% or sustained latency > 2s; alert if External Upstream loses outbound connectivity for > 5 min. |
| Backup cache | External Upstream cache snapshots backed up daily; restoration tested quarterly. |
| Compromise response | If External Upstream is suspected compromised, revoke all sync-derived artifacts, re-verify checksums/signatures against upstream, and rotate hosted artifact trust roots before resuming client pulls. |


## 11. What This Document Does NOT Cover

- Full air-gap readiness: This architecture assumes a connected staging path for artifact acquisition. True air-gap (no connected machine ever) requires additional mechanisms (e.g., encrypted media transfer, manual media rotation) that are out of scope.
- P10.1.4 offline-staging implementation: This document is standalone and does not modify or replace any existing P10.1.4 deliverables.
- Product-specific feature claims beyond what is verified in the architecture design table (see Section 5).
- Guarantee of zero failure: sync failures, upstream unavailability, and checksum/signature mismatches are handled via retry and audit, not eliminated.

---
*Document generated for TASK 004-P11.2 — Two-Tier Repository & Registry Architecture*
*Architecture path: architecture/two-tier-repository-registry.md*
