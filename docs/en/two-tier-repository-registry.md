# Two-Tier Repository & Registry Architecture

Status: DRAFT
Owner: Platform Team
Last reviewed: 2026-11-25
Applies to version: 1.0
Source of truth: Nexus Repository Manager docs + Harbor docs + checked 2026-11-25

## 1. Purpose and Architecture

### Purpose
This document describes the two-tier repository and registry architecture for the Cloud-Native Stack implementation. The architecture separates **package repositories** (for OS-level and language-level binary artifacts) from **container image registries** (for container images and Helm charts), providing distinct trust boundaries, scaling characteristics, and operational models.

The two-tier design consists of:
- **Tier 1 (Local/Proxied)**: Primary repositories/registries that serve as the authoritative source for artifacts. These are deployed in the management cluster with high availability.
- **Tier 2 (Remote/Upstream)**: External public repositories and registries (e.g., Docker Hub, Maven Central, PyPI, GitHub Packages) that are mirrored or proxied through Tier 1.

This separation enables:
- Offline operation via cached artifacts
- Fine-grained access control per artifact type
- Bandwidth optimization through selective mirroring
- Trust boundary isolation (public vs. internal artifacts)

### Architecture Overview
```mermaid
graph TD
    subgraph Tier 1 - Local
        direction LR
        L1[Local Nexus Repository<br/>(yum/apt/maven/nuget)]
        L2[Local Harbor Registry<br/>(Docker/OCI images)]
    end

    subgraph Tier 2 - Remote
        direction LR
        R1[Docker Hub<br/>upstream]
        R2[Maven Central<br/>upstream]
        R3[PyPI<br/>upstream]
        R4[GitHub Packages<br/>upstream]
    end

    subgraph Consumers
        direction LR
        C1[Kubernetes Nodes]
        C2[Developer Workstations]
        C3[CI/CD Pipelines]
        C4[Internal Services]
    end

    C1 -->|pull| L1
    C2 -->|pull| L1
    C3 -->|pull| L1
    C4 -->|pull| L1
    C1 -->|pull| L2
    C2 -->|pull| L2
    C3 -->|pull| L2
    C4 -->|pull| L2

    L1 -->|proxy/proxy+cache| R1
    L1 -->|proxy/proxy+cache| R2
    L1 -->|proxy/proxy+cache| R3
    L2 -->|proxy/proxy+cache| R4

    style Tier 1 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style Tier 2 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style Consumers fill:#fff3e0,stroke:#fb8c00,stroke-width:2px
```

### Trust Boundaries
| Boundary | Direction | Artifacts | Control |
|---|---|---|---|
| **Public → Local** | Inbound | Public upstream artifacts | Rate limiting, GPG verification |
| **Local → Public** | Outbound | Proxy requests to upstream | Proxy authentication, bandwidth caps |
| **Internal → Local** | North-South | Internal/custom artifacts | RBAC, SSO integration |
| **Cluster → Cluster** | East-West | HA sync between replica pairs | encrypted replication, quorum |

### Deployment Location
- **Tier 1 repositories** (Nexus): Deployed on the `repository` role in the management cluster
- **Tier 2 registries** (Harbor): Deployed on the `infra` role in the management cluster
- Both tiers run as highly available StatefulSets with PVC-backed storage

## 2. Supported Versions and Compatibility

| Item | Requirement | Verified |
|---|---|---|
| OS | Ubuntu 24.04 LTS / Oracle Linux 9 | UNVERIFIED |
| CPU | 2+ cores per tier component | UNVERIFIED |
| RAM | 4 GB minimum per component | UNVERIFIED |
| Storage | 100 GB minimum per component, SSD recommended | UNVERIFIED |
| Network | IPv4+, TLS 1.2+ capable | UNVERIFIED |
| Docker/OCI | Image format v2.2 compatible | UNVERIFIED |
| Package managers | DNF 4+, APT 2.6+, Maven 3.6+ | UNVERIFIED |
| TLS | Cert-manager managed, CA signed | UNVERIFIED |

> **Note**: Anything not verified is marked **UNVERIFIED** with the verification procedure in Section 14.

## 3. Prerequisites

### Infrastructure Dependencies
- Management cluster with 3 control-plane nodes minimum
- PersistentVolumeClaim storage >= 100 GB per Nexus/Haror component
- Static IP addresses or DNS names for both tiers
- Load balancer (internal) fronting both Tier 1 components

### Software Dependencies
- Nexus Repository Manager 3.55+ (or latest stable)
- Harbor Registry v2.110+ (or latest stable)
- Containers runtime with docker/OCI support
- `kubectl` configured to management cluster
- `jq` for JSON parsing in validation commands

### Configuration Prerequisites
- DNS entries configured (see Section 4)
- TLS certificates provisioned (see Section 8)
- SSO/IdP integration ready (see Section 7)
- Backup storage configured (see Section 12)

## 4. Network and DNS Conventions

### Endpoint URLs
All endpoints follow the pattern `<service>.<namespace>.internal` for internal access or `<service>.<domain>` for external access.

| Component | Internal Endpoint | External Endpoint | Port |
|---|---|---|---|
| Nexus Repository Manager | `nexus.repo.internal` | `nexus.corp.example.com` | 8081, 8082 |
| Harbor Registry | `harbor.registry.internal` | `harbor.corp.example.com` | 443 |
| Nexus Health Check | `nexus.repo.internal/health` | — | 8081 |
| Harbor Health Check | `harbor.registry.internal/health` | — | 443 |

### DNS Records Required
| Record | Type | Value | TTL |
|---|---|---|---|
| `nexus.repo.internal` | A | `<load-balancer-ip>` | 300 |
| `harbor.registry.internal` | A | `<load-balancer-ip>` | 300 |
| `nexus.repo.internal-api` | A | `<nexus-pod-ip>` | 300 |
| `harbor.registry.internal-api` | A | `<harbor-pod-ip>` | 300 |

> **Note**: Do not assume public DNS resolution. Verify with `dig nexus.repo.internal` and `dig harbor.registry.internal` before proceeding.

### Network Segments
| Segment | CIDR | Purpose | Restriction |
|---|---|---|---|
| `net.repo-tier1` | 10.10.10.0/24 | Nexus Tier 1 traffic | Inter-tier only |
| `net.registry-tier1` | 10.10.20.0/24 | Harbor Tier 1 traffic | Inter-tier only |
| `net.proxy-upstream` | 10.10.30.0/24 | Outbound to upstream repos/registries | Firewalled |

## 5. Firewall and Connectivity Requirements

### Required Ports
| Direction | Protocol | Port(s) | Component | Purpose |
|---|---|---|---|---|
| Inbound | TCP | 8081 | Nexus | HTTP API |
| Inbound | TCP | 8082 | Nexus | HTTPS API |
| Inbound | TCP | 443 | Harbor | HTTPS API |
| Inbound | TCP | 22 | All | SSH (admin) |
| Outbound | TCP | 443 | Nexus | Upstream proxy |
| Outbound | TCP | 443 | Harbor | Upstream proxy |
| Outbound | TCP | 80 | Nexus | Metadata fetch (optional) |
| Outbound | UDP | 123 | All | NTP time sync |

### Firewall Rules (nftables example, RHEL family)
```nft
#!/usr/sbin/nft -i

flush ruleset

table inet repo_fw {
    chain input {
        type filter hook input priority 0
        ct state established,related accept

        # Nexus
        ip daddr 10.10.10.1/32 tcp dport 8081 accept
        ip daddr 10.10.10.1/32 tcp dport 8082 accept

        # Harbor
        ip daddr 10.10.20.1/32 tcp dport 443 accept

        # SSH
        ip daddr anywhere tcp dport 22 accept

        drop
    }

    chain forward {
        type filter hook forward priority 0
        ct state established,related accept

        # Allow proxy to upstream
        ip daddr 10.10.30.0/24 tcp dport 443 accept

        drop
    }

    chain output {
        type filter hook output priority 0
        ct state established,related accept

        # Outbound HTTPS for proxy
        tcp dport 443 accept

        drop
    }
}
```

### Connectivity Verification
```bash
# Verify Nexus reachability
curl -f https://nexus.repo.internal/health || echo "NEXUS UNREACHABLE"

# Verify Harbor reachability
curl -f https://harbor.registry.internal/health || echo "HARBOR UNREACHABLE"

# Verify upstream proxy connectivity
curl -f --proxy https://nexus.repo.internal:8081 https://registry-1.docker.io/v2/ || echo "PROXY FAILURE"
```

## 6. Step-by-Step Setup Procedures

### 6.1 Install Nexus Repository Manager
```bash
# Prerequisites: kubectl context set to management cluster
# Execution context: management-cluster namespace "repository"

# 1. Create namespace if not exists
kubectl create namespace repository --dry-run=client -o yaml | kubectl apply -f -

# 2. Install Nexus via Helm
helm repo add nexus https://charts.nexus.com/chart-repository/nexus-repository-manager
helm install nexus/nexus-repository-manager \
  --name nexus \
  --namespace repository \
  --set persistence.enabled=true \
  --set persistence.size=100Gi \
  --set service.type=LoadBalancer \
  --set proxy.enabled=true

# 3. Wait for pod to be ready
kubectl wait pod -l app.kubernetes.io/name=nexus-repository-manager \
  -n repository --condition=Ready --timeout=300s

# 4. Get the external IP
LB_IP=$(kubectl get svc -n repository nexus-repository-manager -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Nexus UI: https://${LB_IP}:8082"
```

### 6.2 Install Harbor Registry
```bash
# Prerequisites: TLS certs installed in secret "harbor-core-secret"
# Execution context: management-cluster namespace "registry"

# 1. Create configuration file
cat > /harbor/harbor.yml <<'EOF'
hostname: harbor.registry.internal
http:
  port: 443
  https:
    port: 443
    certificate: /certs/cert.pem
    privateKey: /certs/key.pem
storage:
  path: /data
  volume:
    capacity: 100TB
  maxJobWorkers: 10
  maxWorkers: 8
  logLevel: info
trust:
  token: notary
  certificate: /certs/trustedca.crt

componentLog:
  enabled: true
  defaultLogLevel: info
EOF

# 2. Install Harbor via Helm
helm repo add harbor https://helm.goharbor.io/repo/
helm install harbor/harbor \
  --name harbor \
  --namespace registry \
  --values /harbor/harbor.yml \
  --dependency-update

# 3. Wait for pods
kubectl wait pod -l app.kubernetes.io/instance=harbor -n registry \
  --condition=Ready --timeout=300s
```

### 6.3 Configure Upstream Remotes
```bash
# Nexus: Add Maven Central remote
curl -X POST "https://nexus.repo.internal:8082/service/rest/v1/repositories/maven" \
  -u <NEXUS_USER>:<NEXUS_PASS> \
  -H "Content-Type: application/json" \
  -d '{"name":"maven-central","online":true,"remoteStorageUrl":"https://repo1.maven.org/maven2","remoteId":"maven-central"}'

# Harbor: Add Docker Hub registry
helm upgrade harbor harbor/harbor --set config.repository.config[0].upstreamUrl=https://registry-1.docker.io
```

## 7. Authentication and Authorization

### SSO Integration (Keycloak)
Both Nexus and Harbor integrate with Keycloak for centralized identity management.

**Keycloak setup:**
- Realm: `repo-registry`
- Client: `nexus` and `harbor` with valid redirect URIs
- Groups: `admin`, `developer`, `viewer`

**Nexus LDAP/SSO configuration:**
```bash
# Via Nexus UI or API
# 1. Login to Nexus as admin
# 2. Navigate to: Security → Login Settings → SSO
# 3. Configure Keycloak connection:
#    - SSO Login URL: https://keycloak.internal/auth/realms/repo-registry/protocol/saml
#    - SSO Logout URL: https://keycloak.internal/auth/realms/repo-registry/protocol/saml/logout
#    - Entity ID: keycloak.internal
```

**Harbor LDAP/SSO configuration:**
```yaml
# Harbor values.yaml snippet
harbor:
  externalURL: https://harbor.registry.internal
  secretKey: <NEXUS_SECRET_KEY>
  db:
    password: <HARBOR_DB_PASSWORD>
  core:
    config:
      harbor:
        ui:
          anonymouse: "false"
        authentication:
          # Use Keycloak OAuth2
          oauth2:
            client: keycloak
            secret: ${KEYCLOAK_CLIENT_SECRET}
            endpoint: https://keycloak.internal/auth/realms/repo-registry/protocol/openid connect
```

### RBAC Policies
| Role | Nexus Permissions | Harbor Permissions |
|---|---|---|
| `admin` | Full repository read/write, user management | Full registry read/write, user management |
| `developer` | Read/write to personal namespace repos | Read/write to personal image projects |
| `viewer` | Read-only repository view | Read-only image gallery |

### Service Accounts
- `nexus-service-account`: Used by CI/CD pipelines for artifact deployment
- `harbor-service-account`: Used by Kubernetes clusters for image pull

## 8. TLS and Certificate Configuration

### Certificate Sources
- **Preferred**: Cert-manager issued certificates from ACME provider (Let's Encrypt for external, internal CA for internal)
- **Alternative**: Manual PKI with certs mounted as Secrets

### Nexus TLS via Cert-manager
```yaml
# ClusterIssuer reference
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: lets-encrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: docs-team@corp.example.com
    privateKeySecretRef:
      name: lets-encrypt-private-key
    solvers:
      - http01:
          ingressClass: nginx
          clusterIssuerReference:
            name: lets-encrypt-prod

# TLS Certificate for Nexus
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: nexus-tls
  namespace: repository
spec:
  secretName: nexus-tls-secret
  issuer: lets-encrypt-prod
  commonName: nexus.corp.example.com
  dnsNames:
    - nexus.corp.example.com
    - nexus.repo.internal
  renewBefore: 30d
  maturityDuration: 90d
```

### Harbor TLS via Cert-manager
```yaml
# Harbor registry TLS
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: harbor-tls
  namespace: registry
spec:
  secretName: harbor-tls-secret
  issuer: lets-encrypt-prod
  commonName: harbor.corp.example.com
  dnsNames:
    - harbor.corp.example.com
    - harbor.registry.internal
  renewBefore: 30d
```

### Self-Signed Certificate (Air-Gap/Offline)
```bash
# Generate CA
openssl req -x509 -newkey rsa:4096 -keyout ca.key -out ca.crt -days 3650 -nodes \
  -subj "/CN=internal-repo-ca/O=Corp Inc/C=US"

# Generate Nexus certificate
openssl req -newkey rsa:2048 -keyout nexus.key -out nexus.csr -days 365 -nodes \
  -subj "/CN=nexus.repo.internal"

# Sign by CA
openssl x509 -req -in nexus.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out nexus.crt -days 365

# Create Kubernetes secret
kubectl create secret generic nexus-tls \
  --from-file=tls=nexus.crt \
  --from-file=key=nexus.key \
  -n repository
```

> **Warning**: Self-signed certificates require trust distribution to all client systems. Prefer ACME/CA-signed certificates when possible.

## 9. Proxy and Hosted Repository Configuration

### Nexus Proxy Repository (Proxy + Cache)
```bash
# Create proxy repository via API
curl -X POST "https://nexus.repo.internal:8082/service/rest/v1/repositories/maven" \
  -u <NEXUS_USER>:<NEXUS_PASS> \
  -H "Content-Type: application/json" \
  -d '{
    "name": "maven-proxy",
    "online": true,
    "type": "proxy",
    "storage": "default",
    "component": "maven",
    "remoteStorageUrl": "https://repo1.maven.org/maven2",
    "remoteId": "maven-proxy"
  }'

# Create hosted repository for internal artifacts
curl -X POST "https://nexus.repo.internal:8082/service/rest/v1/repositories/maven" \
  -u <NEXUS_USER>:<NEXUS_PASS> \
  -H "Content-Type: application/json" \
  -d '{
    "name": "maven-internal",
    "online": true,
    "type": "hosted",
    "storage": "default",
    "component": "maven"
  }'
```

### Harbor Registry Proxy Remote
```yaml
# Harbor values.yaml - proxy configuration
harbor:
  config:
    repository:
      - name: docker-proxy
        type: proxy
        url: https://registry-1.docker.io
        pullThrough: true
        credential:
          user: ""
          password: ""
      - name: ghcr-proxy
        type: proxy
        url: https://ghcr.io
        pullThrough: true
        credential:
          user: "${GITHUB_ACTOR}"
          password: "${GITHUB_TOKEN}"
```

### Hosted Repository (for internal uploads)
```bash
# Nexus: Upload internal Maven artifact
curl -u admin:admin -T /path/to/internal-artifact-1.0.0.jar \
  "https://nexus.repo.internal:8082/repository/maven-internal/content"

# Harbor: Push image to hosted repository
docker tag my-image:latest harbor.registry.internal/library/my-image:latest
docker push harbor.registry.internal/library/my-image:latest
```

## 10. Team/Project Onboarding

### New Team Provisioning
1. Create Keycloak group: `team-<team-name>`
2. Assign Nexus/Harbor RBAC roles matching group
3. Provide team members with access instructions

### Developer Workstation Setup
```bash
# Install Nexus CLI (if available) or use curl
npm install -g nexus-repository-manager-cli 2>/dev/null || echo "Use curl/HTTP API instead"

# Configure npm for internal registry
npm config set //nexus.repo.internal:8082/maven internal
npm config set //nexus.repo.internal:8082/npm npm-registry

# Configure docker for Harbor
cat >> ~/.docker/config.json <<'EOF'
{
  "auths": {
    "https://harbor.registry.internal": {
      "auth": "$(echo -n 'harbor-user:harbor-pass' | base64)"
    }
  }
}
EOF

# Test connectivity
npm login --registry=https://nexus.repo.internal:8082/repository/npm/npm-registry/
docker login https://harbor.registry.internal
```

### Project Repository Configuration
```bash
# Create project-specific Nexus repository
curl -X POST "https://nexus.repo.internal:8082/service/rest/v1/repositories/maven" \
  -u <NEXUS_USER>:<NEXUS_PASS> \
  -H "Content-Type: application/json" \
  -d '{
    "name": "project-alpha-maven",
    "online": true,
    "type": "hosted",
    "storage": "default",
    "component": "maven"
  }'

# Configure Maven for project
cat > /tmp/settings-alpha.xml <<'EOF'
<settings>
  <profiles>
    <profile>
      <id>alpha-repo</id>
      <repositories>
        <repository>
          <id>project-alpha</id>
          <layout>default</layout>
          <url>https://nexus.repo.internal:8082/repository/project-alpha-maven/</url>
          <releases>
            <enabled>true</enabled>
          </releases>
          <snapshots>
            <enabled>true</enabled>
          </snapshots>
        </repository>
      </repositories>
    </profile>
  </profiles>
  <activeProfiles>
    <activeProfile>alpha-repo</activeProfile>
  </activeProfiles>
</settings>
EOF
```

## 11. Artifact Synchronization

### Pull Synchronization (Scheduled)
```bash
# Nexus: Pull from Maven Central daily via cron
# Create a scheduled task via Nexus UI or script

# Script: sync-nexus-remotes.sh
#!/bin/bash
# Execution context: host with curl access to Nexus

NEURUS_URL="https://nexus.repo.internal:8082"
NEURUS_USER="admin"
NEURUS_PASS="admin"

# Trigger sync for all proxy repositories
curl -s -X POST "${NEURUS_URL}/service/rest/v1/repositories/proxy/*/content/sync" \
  -u "${NEURUS_USER}:${NEURUS_PASS}" \
  -H "Content-Type: application/json"

# Harbor: Garbage collection and sync
helm upgrade harbor harbor/harbor --set job.jobGraveyard.enabled=true --set job.garbageCollection.enabled=true
```

### Push Synchronization
```bash
# Nexus: Promote snapshot to release
curl -X POST "https://nexus.repo.internal:8082/service/rest/v1/repositories/maven/project-alpha-maven/content/release" \
  -u <NEXUS_USER>:<NEXUS_PASS> \
  -H "Content-Type: application/json"

# Harbor: Replicate image to remote site
helm upgrade harbor harbor/harbor \
  --set replica.enabled=true \
  --set replica.remoteSites[0].url=https://remote-harbor.internal \
  --set replica.remoteSites[0].credential.user=admin \
  --set replica.remoteSites[0].credential.password=<HARBOR_REPLICA_PASSWORD>
```

### Synchronization Verification
```bash
# Verify synchronized artifacts count
curl -s -u admin:admin "${NEURUS_URL}/service/rest/v1/repositories/maven/maven-proxy/content" | jq '.items | length'

# Verify Harbor replication status
helm status harbor-replica -n registry
```

## 12. Backup and Restore

### Backup Procedures
| Component | Backup Method | Frequency | Retention |
|---|---|---|---|
| Nexus | `nexus backup` API + PVC snapshot | Daily (02:00 UTC) | 14 days |
| Harbor | `harbor job configuration export` + PVC snapshot | Daily (03:00 UTC) | 30 days |

```bash
# Nexus backup via API
curl -X POST "${NEURUS_URL}/service/rest/v1/admin/system/backup" \
  -u <NEXUS_USER>:<NEXUS_PASS> \
  -H "Content-Type: application/json" \
  -d '{"format":"tar","name":"backup-'$(date +%Y%m%d-%H%M%S)'"}' \
  -o /backup/nexus/backup-$(date +%Y%m%d).tar

# Harbor backup via velero or built-in
velero backup create harbor-backup-$(date +%Y%m%d) \
  --selector include=harbor.io/backup=true \
  --storage-location velero-rgw
```

### Restore Procedures
```bash
# Nexus restore
curl -X POST "${NEURUS_URL}/service/rest/v1/admin/system/restore" \
  -u <NEXUS_USER>:<NEXUS_PASS> \
  -H "Content-Type: application/json" \
  -d "{\"format\":\"tar\",\"filePath\":\"file:///backup/nexus/backup-20261125.tar\"}"

# Harbor restore
velero restore create --from-backup harbor-restore-$(date +%Y%m%d)

# Verify restore
# Nexus: Check backup manifest
kubectl exec -n repository $(kubectl get pod -n repository -l app.kubernetes.io/name=nexus-repository-manager -o jsonpath='{.items[0].metadata.name}') \
  -- nexus backup:list

# Harbor: Check restored projects
kubectl get projects -n registry
```

### RTO/RPO Targets
- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 24 hours (daily backups)

## 13. HA and Failure Recovery

### Nexus HA Configuration
- **Deployment**: 3-replica StatefulSet with PVCs
- **Replication**: Local secret replication via ` Nexus sync` API
- **Failover**: Automatic via StatefulSet ordinal indexing
- **Quorum**: Based on persistent storage quorum (etcd or external DB)

```bash
# Check Nexus HA status
kubectl get svc -n repository nexus-repository-manager
kubectl get pods -n repository -l app.kubernetes.io/name=nexus-repository-manager -o wide

# Force failover to replica-2
kubectl patch statefulset nexus-repository-manager -n repository \
  -p '{"spec":{"replicas":3}}'  # Ensure 3 replicas running
```

### Harbor HA Configuration
- **Deployment**: 3-replica Core + 3-replica Registry deployment
- **Replication**: Notary2 transparency log replication
- **Failover**: DNS switchover + load balancer reconfiguration

```bash
# Check Harbor HA status
kubectl get pods -n registry -l app.kubernetes.io/instance=harbor -o wide
kubectl get svc -n registry harbor-registry-core -o wide

# Simulate node failure - drain and redeploy
kubectl drain node-worker-3 --ignore-daemonsets --delete-emptydata --force
# Pods reschedule on remaining nodes
```

### Failure Recovery Procedures
1. **Node failure**: Kubernetes auto-replaces pods on healthy nodes
2. **Node pool failure**: Re-deploy StatefulSet on new pool, restore from backup if PVC lost
3. **Total site failure**: Restore from off-site backup (see Section 12)
4. **Certificate expiry**: Cert-manager auto-renewal; manual renewal if using self-signed

```bash
# Monitor HA health
kubectl get crd | grep -E "nexus|harbor" | head -5

# Check replica status
kubectl get pods -n repository -l app.kubernetes.io/name=nexus-repository-manager \
  -o jsonpath='{.items[*].status.containerStatuses[0].ready}'

# Verify data integrity post-recovery
nexus repo list || harbor project list
```

## 14. Validation Commands and Expected Outputs

### Nexus Validation
```bash
# 1. Check Nexus service status
kubectl -n repository get pod -l app.kubernetes.io/name=nexus-repository-manager

# 2. Verify HTTP API endpoint
curl -s https://nexus.repo.internal:8082/service/rest/v1/status | jq '.'

# 3. Verify proxy repository is online
curl -s -u admin:admin https://nexus.repo.internal:8082/service/rest/v1/repositories/maven/maven-proxy | jq '.online'

# 4. Verify hosted repository has content
curl -s -u admin:admin https://nexus.repo.internal:8082/repository/maven-internal/ | head -5
```

### Harbor Validation
```bash
# 1. Check Harbor pod status
kubectl -n registry get pod -l app.kubernetes.io/instance=harbor

# 2. Verify Harbor API health
curl -s -k https://harbor.registry.internal/health | jq '.'

# 3. Verify registry is operational
curl -s -k https://harbor.registry.internal/v2/_catalog | jq '.'

# 4. List projects
curl -s -k -u admin:admin https://harbor.registry.internal/api/projects | jq '.'
```

### Expected Output Samples

**Nexus status JSON:**
```json
{
  "name": "Nexus Repository Manager",
  "version": "3.55.20241115",
  "status": "running",
  "licensed": true,
  "lastHealthCheck": "2026-11-25T10:30:00Z",
  "healthCheck": "healthy"
}
```

**Harbor health JSON:**
```json
{
  "status": "success",
  "message": "Harbor is running",
  "version": "v2.110.3",
  "timestamp": "2026-11-25T10:30:00Z"
}
```

### Failure Condition Detection
| Command | Expected | Failure Indicator |
|---|---|---|
| `curl -f https://nexus.repo.internal:8082/health` | RC 0, `healthy` | RC non-0, timeout, `unhealthy` |
| `curl -f https://harbor.registry.internal/health` | RC 0, `success` | RC non-0, timeout, error JSON |
| `kubectl -n repository get pod` | All 3 pods `Ready` | Any pod `ContainerCreating` or `Error` |
| `helm status harbor -n registry` | All components `deployed` | Any component `pending` or `failed` |

## 15. Common Errors and Troubleshooting

### Proxy Connection Errors
| Symptom | Diagnosis | Fix |
|---|---|---|
| `curl: (7) Failed to connect to Nexus` | Network unreachable or wrong DNS | Verify DNS resolution: `dig nexus.repo.internal`; Check firewall rules (Section 5) |
| `HTTP 502 Bad Gateway` | Upstream proxy not running | Check Nexus pod: `kubectl get pods -n repository`; Restart: `kubectl rollout restart deployment/nexus-repository-manager -n repository` |
| `HTTP 403 Forbidden` | Authentication failure | Verify admin credentials; Check Keycloak SSO integration (Section 7) |
| `HTTP 404 Not Found` | Repository not found | Verify repository name: `nexus repo list`; Check spelling and case |

### TLS/Certificate Errors
| Symptom | Diagnosis | Fix |
|---|---|---|
| `curl: (60) SSL certificate problem: self signed certificate` | Self-signed cert not trusted | Add CA to system trust store: `cp ca.crt /usr/local/share/ca-certificates/ && update-ca-certificates`; Or use `--insecure` flag temporarily |
| `curl: (28) Connection timed out` | Certificate expiry or firewall | Check cert expiry: `openssl x509 -in cert.crt -text -noout | grep "Not After"`; Verify firewall allows 443 TCP |
| `NET::ERR_CERT_COMMON_NAME_INVALID` | CN mismatch in certificate | Verify certificate CN matches endpoint: `openssl x509 -in cert.crt -text -noout | grep "Subject:"`; Regenerate cert with correct CN |

### Repository/Registry Errors
| Symptom | Diagnosis | Fix |
|---|---|---|
| `404 Not found` when pulling image | Image not in repository | Verify image tag: `docker images`; List projects: `harbor project list` |
| `Maven artifact not found` | Proxy not caching | Force re-sync: `curl -X POST /service/rest/v1/repositories/proxy/*/content/sync`; Check upstream availability |
| `Permission denied` when pushing | RBAC misconfiguration | Check user/group assignments in Keycloak; Verify Harbor/RBAC policies (Section 7) |
| `Tag already exists` | Duplicate tag push | Allow overwrite: Update Harbor chart `push.allowOverwrite: true`; Or use different tag |

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*

**Cross-references:**
- [Platform Standards](../requirements/platform-standards.md)
- [Version Matrix](../compatibility/version-matrix.md)
- [Architecture Overview](../architecture/00-overview.md)
- [Validation Strategy](../requirements/validation-strategy.md)