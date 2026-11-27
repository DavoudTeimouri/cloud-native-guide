# Nexus and Harbor Architecture for Offline Environments

## 1. Registry Selection

### 1.1 Role Assignment

| Artifact Type | Primary Registry | Secondary/Backup | Reason |
|---|---|---|---|
| OCI container images | Harbor | Nexus raw | Harbor is the canonical container registry; Nexus handles supplemental artifacts |
| Helm charts (OCI) | Harbor OCI project | Nexus helm | Argo CD targets Harbor exclusively for OCI charts |
| Helm charts (classic) | Nexus helm-hosted | — | Legacy consumers; flat-file index.yaml layout |
| RPM (Oracle Linux, RHEL-compatible) | Nexus rpm-hosted | — | Upstream requires entitlement; Nexus is the mirror |
| DEB (Ubuntu) | Nexus deb-hosted (apt) | — | Includes -updates and -security pockets |
| PyPI | Nexus pypi-hosted | — | Proxy of pypi.org |
| npm (if used) | Nexus npm-hosted | — | Proxy of registry.npmjs.org |
| Go modules | Nexus go-hosted | — | Proxy of proxy.golang.org |
| Git repositories | GitLab self-contained | — | Mirror clone from staging; `git bundle` for transfer |
| Ansible collections/roles | Nexus raw-hosted | — | Galaxy proxy + vendor tarballs into GitLab |
| Security scanner DBs | Nexus raw-hosted | — | Manual refresh from connected staging; date-stamped |
| OS images (cloud) | Nexus raw-hosted | — | Vendor images for cloud-init |
| AI model weights | Harbor + S3-compatible object | — | Large artifacts; not registry objects |
| AI inference images | Harbor | — | Same as any container image |
| NVIDIA drivers/toolkit | Nexus raw-hosted | — | Large files; version-pinned per GPU matrix |
| Vault binaries/plugins | Nexus raw-hosted | — | Proxy of releases.hashicorp.com |

**Anti-pattern**: Do not point clusters at Nexus for images and Harbor for charts and GitLab for images — this creates three pull paths, three auth schemes, and three failure modes.

### 1.2 Selection Criteria

- **Container images** → Harbor (OCI-native, content trust, image scanning integrated)
- **OS packages (RPM/DEB)** → Nexus (yum/apt repo-native, GPG signing, repo metadata)
- **Helm charts** → Harbor OCI for modern clusters; Nexus classic for legacy tooling
- **Language-specific packages (PyPI/npm/Go)** → Nexus (proxy-native, simple index layout)
- **Git repositories** → GitLab (distributed version control; not a registry function)
- **Large binary artifacts (models, driver ISOs)** → S3-compatible object storage + Nexus raw

## 2. High Availability

### 2.1 Harbor HA Architecture

Harbor supports active-passive HA through a floating IP or load balancer fronting two or more Harbor instances.

**Components:**
- **Primary Harbor instance** — handles all traffic; state written to shared storage
- **Secondary Harbor instance** — standby; syncs state from primary
- **Load balancer (L4 or L7)** — distributes traffic; handles failover
- **Shared storage** — NFS, PV, or highly available database for artifact metadata

**Configuration:**
- Both instances point to the same external database (PostgreSQL) or shared NFS for Blob storage
- Session affinity or load balancer ensures sticky connections during replications
- Replication daemon syncs metadata, vulnerability DB, and configuration from primary to secondary
- DNS or DNS-round-robin can redirect clients to the secondary if primary fails

**Example topology:**
```text
       +------------+     +------------+
       |  Client    | --> |  LB / VIP  |
       +------------+     +------------+
                                  / \
                                 /   \
+----------+                  +----------+
| Harbor 1 |                  | Harbor 2 |
+----------+                  +----------+
       \                  /
        \                /
         \              /
          +------------+
          | Shared NFS |
          | / PostgreSQL |
          +------------+
```

### 2.2 Nexus HA Architecture

Nexus can be run in clustered mode using Azure Blob Storage, AWS S3, or a shared filesystem for blob storage. Each Nexus node is stateless regarding repository configuration; blobs are stored in the shared backend.

**Configuration:**
- Minimum 2 nodes in a cluster
- Shared blob store (S3, Azure Blob, GCS, or NFS)
- Router / load balancer distributes requests across nodes
- Cluster protocol (JGroups or TCP) synchronizes repository metadata

**Example topology:**
```text
       +------------+     +------------+
       |  Client    | --> |  Load Bal  |
       +------------+     +------------+
                                  / \
                                 /   \
+----------+                  +----------+
| Nexus 1  |                  | Nexus 2  |
+----------+                  +----------+
       \                  /
        \                /
         \              /
          +------------+
          | Shared S3  |
          | / PostgreSQL |
          +------------+
```

## 3. Storage Backend

### 3.1 Harbor Storage Backend

| Component | Default | Recommended for Production | Notes |
|---|---|---|---|
| **PostgreSQL** | Embedded H2 | External PostgreSQL 13+ | Required for HA; manage backups separately |
| **Blob storage** | `/data/images` on local disk | Network-backed (NFS, S3, Azure Blob, GCS) | Local disk OK for single-node only |
| **Trivy DB** | Embedded SQLite | External PostgreSQL + object storage | Large; separate volume recommended |
| **Log storage** | `/data/log` | Separate volume or syslog | Rotate daily; retain 30 days minimum |

**Notes:**
- For HA, PostgreSQL must be external (embedded H2 does not support clustering)
- Blob storage must be accessible from all HA nodes; S3-compatible is ideal for multi-cloud
- Trivy vulnerability DBs can be stored on separate fast storage; date-stamped snapshots

### 3.2 Nexus Storage Backend

| Component | Default | Recommended for Production | Notes |
|---|---|---|---|
| **Repository metadata** | Embedded H2 | External PostgreSQL 13+ | Required for clustering; manage backups |
| **Blob storage** | `/sonatype-work/sonatype-thirdparty` | S3, Azure Blob, GCS, or NFS | Must be shared across cluster nodes |
| **Sonatype Work** | Local disk | Separate volume, backed up daily | Used for build analytics; optional |

**Notes:**
- Clustering requires a shared blob store; local disk does not support HA
- S3 is the most common production choice; ensure versioning and lifecycle policies are configured
- PostgreSQL must be reachable from all Nexus nodes; use a load balancer or DNS

## 4. Replication

### 4.1 Harbor Replication

Harbor supports image replication from upstream registries and between Harbor instances.

**Upstream replication (mirroring):**
- Pull from upstream (registry.k8s.io, quay.io, docker.io) on schedule
- Use `skopeo copy` under the hood; digest-pinned ensures integrity
- Configuration in Harbor UI or via API:
  ```yaml
  replication:
    remote:
      - name: "registry-k8s-io"
        url: "https://registry.k8s.io"
        username: ""
        password: ""
        pull: true
        push: false
        interval: "1h"
  ```

**Inter-Harbor replication:**
- Active-passive: secondary pulls replicated images from primary
- Used for geographic distribution or DR sites
- Configured via API: `POST /api/v2.0/replication`

**Replication schedule:**
- Default: every hour for upstream mirrors
- Can be tuned per repository; disable for static sets
- Retry with exponential backoff on failure

### 4.2 Nexus Replication

Nexus supports repository replication for proxy repositories.

**Pull-replication (pull-through cache with update):**
- Proxy repository fetches from upstream on demand
- Can be configured to revalidate/replicate on a schedule
- `Schedule` tab in UI or via `repository.replication.interval` in `nexus.properties`

**Push-replication:**
- Push from one Nexus to another (less common; usually pull-through is sufficient)
- Configured via replication destination in UI or REST API

**Example: Configure pull-replication via REST**
```bash
curl -u admin:admin123 -X POST "http://nexus.internal/repository/rpm-containerd/replication" \
  -H "Content-Type: application/json" \
  -d '{"interval": 3600, "online": true}'
```

### 4.3 Replication Best Practices

| Practice | Reason |
|---|---|
| Pin digests, not tags | Tags can change; digests are immutable |
| Set `validate: true` | Verify upstream signature/checksum on each pull |
| Monitor replication lag | Alert if secondary is out of sync beyond threshold |
| Keep replication intervals reasonable | Too frequent = unnecessary load; too stale = outdated artifacts |
| Test failover | Ensure secondary can serve traffic when primary is cut over |

## 5. Security Configuration

### 5.1 Harbor Security

| Area | Configuration | Recommended |
|---|---|---|
| **TLS** | x509 certificate for `harbor.internal` | Use CA-signed cert; enable HTTPS everywhere |
| **Authentication** | Internal DB or LDAP/Active Directory | LDAP for enterprise; internal for simple deployments |
| **User roles** | `admin`, `developer`, `guest` | Grant least privilege; use groups from LDAP |
| **Token expiration** | Default 24h | Rotate regularly; use short-lived tokens for CI |
| **Content trust** | Notary signifier (disabled by default) | Enable for critical images; requires HSM or KMS |
| **Network policy** | Restrict ingress to LB VIP only | Firewall: only allow 443/tcp from approved subnets |
| **Secret scanning** | Built-in vulnerability scanning | Integrate with Trivy; scan on push; retain results 90 days |
| **API security** | CSPM, secret scanning in configs | Run `trivy config` on Helm charts and manifests |

**Detailed TLS setup:**
```yaml
# Harbor configuration (harbor.yml)
hostname: "harbor.internal"
http:
  port: 80
  host: "harbor.internal"
  https:
    enabled: true
    port: 443
    certfile: /etc/harbor/certs/harbor.internal.crt
    keyfile: /etc/harbor/certs/harbor.internal.key
notification:
  webhook_url: ""
  ...
database:
  postgres:
    host: harbor-db.internal
    port: 5432
    user: harbor
    password: "changeme"
    sslmode: "require"
```

### 5.2 Nexus Security

| Area | Configuration | Recommended |
|---|---|---|
| **TLS** | x509 certificate for `nexus.internal` | CA-signed; enable HTTPS on all ports |
| **Authentication** | Internal LDAP/AD or single sign-on | LDAP for enterprise; SSO (OIDC) for modern stacks |
| **Role-based access** | `admin`, `deploy`, `browse`, `restricted` | Least-privilege roles per repository |
| **Anonymous access** | Disabled by default | Disable entirely for offline air-gap |
| **Password policy** | Minimum length, complexity, rotation | 12+ chars; enforce via LDAP policy |
| **HTTP security headers** | X-Content-Type-Options, X-Frame-Options | Set in `nexus.properties` or reverse proxy |
| **Secret scanning** | Integration with Trivy/Grype | Scan stored RPMs/DEBs on schedule |

**Detailed TLS setup:**
```properties
# nexus.properties
application-port=8083
application-host=nexus.internal
application-base-path=
context-path=
jsonp-enabled=false
https.enabled=true
https.keystore=file:/opt/sonatype/sonatype-work/conf/keystore.p12
https.keystore.password=changeit
https.truststore=file:/opt/sonatype/sonatype-work/conf/truststore.p12
https.truststore.password=changeit
ldap.server.url=ldap://ldap.internal:389
ldap.bind.dn=cn=admin,dc=example,dc=com
ldap.bind.password=ldap-password
```

### 5.3 Shared Security Practices

| Practice | Harbor | Nexus |
|---|---|---|
| **TLS everywhere** | ✅ Required | ✅ Required |
| **Least-privilege roles** | ✅ Built-in | ✅ Built-in |
| **Token rotation** | ✅ Every 24h | ✅ Via LDAP policy |
| **Audit logging** | ✅ Enabled by default | ✅ Enabled by default |
| **Image/signature verification** | ✅ Notary / Cosign | ✅ GPG-signed repos |
| **Vulnerability scanning** | ✅ Trivy integrated | ✅ Grype/Trivy on demand |
| **Network isolation** | LB VIP only | Firewall-restricted repos |
| **Backup verification** | Monthly restore test | Quarterly restore test |

---

**Document generated**: November 2026
**Applies to**: Offline/platform air-gapped deployments
**Related artifacts**: `offline-artifacts/artifact-matrix.md`, `offline-artifacts/nexus-harbor-integration.md`, `offline-artifacts/offline-artifact-architecture.md`
