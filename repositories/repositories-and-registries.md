# Repository and Registry Infrastructure

This document describes the internal repository and registry infrastructure for air-gapped and restricted-connectivity environments.

## Overview

The platform operates fully offline. All artifacts (container images, Helm charts, OS packages, binaries) are mirrored to internal registries and repositories.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Internal Artifact Infrastructure                    │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Harbor    │  │   Nexus     │  │   GitLab    │  │   Ceph RGW  │ │
│  │  (OCI/img)  │  │ (rpm/deb/   │  │  (SCM + CI  │  │  (S3/Object)│ │
│  │             │  │  pypi/helm/ │  │   + reg)    │  │             │ │
│  │             │  │  npm)       │  │             │  │             │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │        │
│         └────────────────┴────────────────┴────────────────┘        │
│                              │                                        │
│                    ┌─────────┴─────────┐                             │
│                    │   Internal CA     │                             │
│                    │  (TLS for all)    │                             │
│                    └───────────────────┘                             │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Overview

| Service | Purpose | Internal URL | Port |
|---|---|---|---|
| **Harbor** | OCI images, Helm charts, SBOMs, signatures | `https://harbor.internal` | 443 |
| **Nexus Repository** | rpm/deb (OS), pypi, npm, Helm charts, Maven | `https://nexus.internal` | 443 |
| **GitLab** | Source control, CI/CD, container registry, package registry | `https://gitlab.internal` | 443 |
| **Ceph RGW** | S3-compatible object storage (model weights, backups, logs) | `https://rgw.internal` | 443 |

## Harbor (Container Registry)

### Purpose
Primary container image registry with vulnerability scanning, SBOM generation, and cosign signature verification.

### Configuration
- **Projects**: Per-team (`platform-<team>`, `apps-<team>`)
- **Retention**: Immutable tags for releases, 30-day cleanup for dev tags
- **Replication**: Pull-through cache for upstream (disabled in air-gap)
- **Vulnerability Scanning**: Trivy integration, scheduled daily
- **SBOM**: Generated on push (Syft), stored in Harbor
- **Signatures**: Cosign verification enforced at admission

### Repository Structure
```
harbor.internal/
├── platform/
│   ├── cert-manager/
│   ├── external-dns/
│   ├── cilium/
│   ├── metallb/
│   ├── rancher/
│   ├── argocd/
│   └── ...
├── apps/
│   ├── payments-api/
│   └── ...
├── base/
│   ├── ubuntu:24.04
│   ├── oraclelinux:9
│   └── ...
└── library/          # Upstream mirrors (read-only)
```

### Air-Gap Mirroring
```bash
# Mirror image to internal Harbor
skopeo copy --src-tls-verify=false \
  docker://registry.k8s.io/pause:3.9 \
  docker://harbor.internal/base/pause:3.9

# Mirror Helm chart
helm pull oci://registry-1.docker.io/bitnami/nginx \
  --destination ./charts/
helm push ./charts/nginx-15.0.0.tgz oci://harbor.internal/charts
```

### Client Configuration
```toml
# /etc/containers/registries.conf
[[registry]]
prefix = "harbor.internal"
location = "harbor.internal"
insecure = false

[[registry.mirror]]
prefix = "docker.io"
location = "harbor.internal/library"
```

## Nexus Repository Manager

### Purpose
Universal package repository for OS packages, language packages, and Helm charts.

### Repository Types
| Format | Repository | Upstream |
|---|---|---|
| **apt** | `ubuntu-main`, `ubuntu-updates`, `ubuntu-security` | `http://archive.ubuntu.com/ubuntu` |
| **apt** | `oraclelinux-base`, `oraclelinux-appstream` | `https://yum.oracle.com` |
| **yum** | `ol9-baseos`, `ol9-appstream` | `https://yum.oracle.com` |
| **pypi** | `pypi-proxy` | `https://pypi.org/simple` |
| **npm** | `npm-proxy` | `https://registry.npmjs.org` |
| **helm** | `helm-proxy` | `https://charts.jetstack.io`, `https://charts.bitnami.com` |
| **maven** | `maven-central` | `https://repo1.maven.org/maven2` |
| **raw** | `binaries` | — |

### Client Configuration

**APT (Ubuntu/Oracle Linux):**
```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ noble main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ noble-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ noble-security main restricted universe multiverse
```

**YUM/DNF (Oracle Linux):**
```ini
# /etc/yum.repos.d/nexus.repo
[ol9-baseos]
name=Oracle Linux 9 BaseOS
baseurl=https://nexus.internal/repository/ol9-baseos/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-baseos/RPM-GPG-KEY-oracle
```

**pip:**
```ini
# ~/.config/pip/pip.conf
[global]
index-url = https://nexus.internal/repository/pypi-proxy/simple/
trusted-host = nexus.internal
```

**npm:**
```bash
npm config set registry https://nexus.internal/repository/npm-proxy/
```

**Helm:**
```bash
helm repo add internal https://nexus.internal/repository/helm-proxy/
```

## GitLab (SCM + CI/CD + Registry)

### Purpose
Source control, CI/CD pipelines, container registry, package registry, and project management.

### Key Features
- **Projects**: Per-domain (`platform-<domain>`, `apps-<team>`)
- **CI/CD**: 14-stage pipeline with lint, test, security scan, approval gates
- **Container Registry**: Per-project, integrated with Harbor via replication
- **Package Registry**: Maven, npm, PyPI, Conan, Terraform modules
- **Pages**: Documentation hosting

### CI/CD Pipeline Stages
1. **Lint** → markdownlint, yamllint, hadolint, helm lint
2. **Syntax** → ansible-lint, helm template, kubeval
3. **Unit Test** → pytest, go test, etc.
4. **Security Scan** → Trivy, Syft, Cosign verify
5. **Policy** → Gatekeeper/Kyverno check, OPA policy
5. **Build** → Docker build, Cosign sign, SBOM generate
6. **Push** → Harbor (by digest), Nexus (packages)
7. **Policy Check** → Admission policy validation
8. **Approval** → Manual approval for production
9. **Deploy** → Argo CD sync (App-of-Apps)
10. **Post-Deploy** → Health checks, smoke tests
11. **Drift Detection** → Argo CD diff vs Git
12. **Notify** → Slack/email/webhook

### Protected Branches
- `main`: Requires 2 approvals, pipeline must pass, no force push
- `release/*`: Requires 2 approvals, pipeline must pass
- `hotfix/*`: Requires 1 approval, pipeline must pass

## Ceph RGW (S3-Compatible Object Storage)

### Purpose
S3-compatible object storage for model weights, ML artifacts, backups, logs, and Terraform state.

### Buckets
| Bucket | Purpose | Retention |
|---|---|---|
| `model-weights` | ML model artifacts (GGUF, safetensors) | Immutable, indefinite |
| `terraform-state` | Terraform remote state | Versioned, 1 year |
| `backups` | Velero backups, etcd snapshots | 30 days + 1 offline |
| `logs` | Centralized log archive | 90 days |
| `artifacts` | CI/CD artifacts, SBOMs, signatures | 30 days |

### S3 Client Configuration
```bash
# AWS CLI
aws s3 ls s3://model-weights/ --endpoint-url https://rgw.internal

# Terraform backend
terraform {
  backend "s3" {
    bucket         = "terraform-state"
    key            = "platform/terraform.tfstate"
    endpoint       = "https://rgw.internal"
    region         = "us-east-1"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
  }
}
```

## Internal CA and TLS

All internal services use certificates from the internal CA (Vault PKI):

- **CA Root**: Offline, stored in Vault PKI root
- **Intermediate**: Online, auto-renewed via cert-manager
- **Leaf Certs**: Issued by cert-manager via Vault PKI issuer
- **Trust Distribution**: CA cert distributed via OS baseline (`operating-systems/host-configuration.md`)

### Certificate Distribution
```bash
# Install CA cert on nodes
cp ca.crt /usr/local/share/ca-certificates/internal-ca.crt
update-ca-certificates

# Verify
curl -v https://harbor.internal
curl -v https://nexus.internal
```

## Air-Gap Mirroring Procedure

### Staging Environment
1. Connected staging environment with internet access
2. Mirror all artifacts to staging Harbor/Nexus/GitLab
3. Verify integrity (digests, signatures)
4. Export to air-gap media (encrypted disk, secure transfer)

### Air-Gap Import
1. Transfer media to air-gap network
2. Import to production Harbor/Nexus/GitLab
3. Verify integrity against staging checksums
4. Update client configurations

### Automation
```bash
# scripts/stage_artifacts.sh
# 1. Pull from upstream
# 2. Verify digests/signatures
# 3. Push to staging Harbor/Nexus/GitLab
# 4. Generate artifact-matrix.md with digests
# 5. Export to media

# scripts/import_artifacts.sh
# 1. Import from media
# 2. Verify against artifact-matrix.md
# 3. Update client configs
```

## Monitoring and Health

| Service | Health Check | Metrics |
|---|---|---|
| Harbor | `/api/v2.0/health` | `harbor_*` metrics |
| Nexus | `/service/rest/v1/status` | `nexus_*` metrics |
| GitLab | `/-/health` | `gitlab_*` metrics |
| Ceph RGW | `ceph -s` | `ceph_rgw_*` metrics |

## Security

- All internal communication over TLS (internal CA)
- Network segmentation: registry VLAN isolated
- RBAC: Per-project/team access control
- Audit logging: All registry access logged
- Vulnerability scanning: Trivy on push, scheduled daily

## Backup and Recovery

| Service | Backup Method | Frequency | Retention |
|---|---|---|---|
| Harbor | Velero + DB dump | Daily | 30 days + 1 offline |
| Nexus | Blobstore backup + DB dump | Daily | 30 days |
| GitLab | GitLab backup rake task | Daily | 30 days + monthly full |
| Ceph RGW | Ceph bucket versioning + bucket replication | Continuous | 30 days |

## References

- [Offline Artifacts Matrix](../offline-artifacts/artifact-matrix.md)
- [Offline Artifact Architecture](../offline-artifacts/offline-artifact-architecture.md)
- [Network Communication Matrix](../network-matrix/network-communication-matrix.md)