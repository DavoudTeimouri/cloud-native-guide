# Image and Package Mirroring

This document covers container image mirroring with skopeo, OS package repository synchronization, air-gapped transfer methods, and validation checklists for offline environments.

## Container Image Mirroring with Skopeo

### Prerequisites

- `skopeo` installed on the staging host
- Access to upstream registries (Docker Hub, ghcr.io, quay.io)
- Internal registry (Harbor or Nexus) with sufficient storage
- containerd or Docker configured to pull from the internal registry
- `crictl` configured for the target runtime

### Mirror Command

```bash
skopeo copy --src-tls-verify=false \
  docker://SOURCE_IMAGE \
  docker://INTERNAL_REGISTRY/PATH/TO:TAG
```

### Example: Mirroring Kubernetes Control Plane Images

```bash
#!/bin/bash
set -euo pipefail

IMAGES=(
  "registry.k8s.io/pause:3.9"
  "registry.k8s.io/kube-apiserver:v1.36.5"
  "registry.k8s.io/kube-controller-manager:v1.36.5"
  "registry.k8s.io/kube-scheduler:v1.36.5"
  "registry.k8s.io/kube-proxy:v1.36.5"
  "registry.k8s.io/coredns/coredns:v1.14.2"
  "registry.k8s.io/etcd:3.6.15"
)

for img in "${IMAGES[@]}"; do
  echo "Mirroring $img"
  skopeo copy --src-tls-verify=false \
    "docker://$img" \
    "docker://harbor.internal/base/$(echo $img | sed 's|.*/||')"
done
```

### Verifying Mirrored Image Digests

```bash
skopeo inspect docker://harbor.internal/base/pause:3.9 --format '{{.Digest}}'
```

### containerd Registry Mirror Configuration

Ensure containerd can resolve images from the internal registry by configuring
`/etc/containerd/certs.d/<registry>/hosts.toml` and adding a registry mirror:

```toml
[plugins."io.containerd.grpc.v1.cri".registry.mirrors]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.internal"]
    address = ["http://harbor.internal:8082"]

[plugins."io.containerd.grpc.v1.cri".config."harbor.internal".tls]
  insecure_skip_verify = true
```

### Skopeo with Offline Archives

Mirror images to a local tar archive for media-based transfer:

```bash
skopeo copy --src-tls-verify=false --dest-creds="" \
  docker://registry.k8s.io/pause:3.9 \
  docker-archive:./mirror/pause.tar

# List contents
skopeo inspect docker-archive:./mirror/pause.tar --format '{{.Digest}}'
```

## OS Package Repository Mirroring

### Oracle Linux / RHEL-compatible (dnf)

```bash
#!/bin/bash
set -euo pipefail

# Oracle Linux BaseOS
dnf download --resolve \
  --repoid=ol9-baseos \
  --downloaddir=/mirror/ol9-baseos

# Oracle Linux AppStream
dnf download --resolve \
  --repoid=ol9-appstream \
  --downloaddir=/mirror/ol9-appstream
```

### Oracle Linux GPG Signature Verification

Ensure the internal repo GPG key is configured in `/etc/yum.repos.d/internal.repo`:

```ini
[ol9-baseos]
name=Oracle Linux 9 BaseOS
baseurl=https://nexus.internal/repository/rpm-oraclelinux/ol9-baseos
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg-key-oraclelinux

[ol9-appstream]
name=Oracle Linux 9 AppStream
baseurl=https://nexus.internal/repository/rpm-oraclelinux/ol9-appstream
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg-key-oraclelinux
```

### Ubuntu DEB (apt)

```bash
#!/bin/bash
set -euo pipefail

# Mirror Ubuntu packages using apt-mirror
apt-mirror /etc/apt/mirror.list

# Or manually download with apt-get
apt-get update
apt-get download --default-release stable \
  $(apt-rdepends --state-software --briefs pkg-name | grep pkg-name)
```

### Ubuntu APT Repository Configuration

Create `/etc/apt/sources.list.d/internal.list`:

```ini
deb https://nexus.internal/repository/deb-ubuntu/ focal main restricted
deb https://nexus.internal/repository/deb-ubuntu/ focal-updates main restricted
deb https://nexus.internal/repository/deb-ubuntu/ focal-security main restricted
```

### OS Package Availability Offline Verification

```bash
# Refresh local metadata (already mirrored)
dnf makecache --dir /mirror/ol9-baseos
# Or
apt-get update -o Dir::Cache=/mirror/ol9-deb

# Test offline install
dnf install --releasever=9 ./mirror/ol9-baseos/*.rpm -y --nobest
# Or
apt-get install -y ./mirror/ol9-deb/*.deb --no-install-recommends
```

## Air-Gapped Transfer Methods

### Method 1: Skopeo Offline Archive (`docker-archive`)

```bash
# On staging (connected) host
skopeo copy --src-tls-verify=false \
  docker://registry.k8s.io/pause:3.9 \
  docker-archive:./pause.tar

# Transfer via approved media to air-gapped host
# On air-gapped host
crictl load --input pause.tar
```

### Method 2: Harbor Registry Transfer Over Internal Network

```bash
# Mirror to internal Harbor registry
skopeo copy --src-tls-verify=false \
  docker://SOURCE_IMAGE \
  docker://harbor.internal/namespace/IMAGE:TAG

# On air-gapped host, ensure registry is accessible
# and configure containerd/docker client certs
```

### Method 3: Encrypted USB / Controlled Media

| Method | Use Case | Notes |
|---|---|---|
| Encrypted USB drive | Small artifact sets | Requires chain of custody, encryption, manifest checksum verification on arrival |
| Controlled media shipment | Large-scale deployment | Document hash verification before/after transfer |
| Secure file transfer service | Medium artifact sets | SFTP/SCP with key rotation and audit logging |

### Method 4: Airgap Containerized Skopeo Bundle

```bash
# Use the airgap-skopeo container pattern
docker run --rm \
  -v /path/to/local:/export \
  -v /var/run/aix.sock:/var/run/docker.sock \
  docker.io/library/airgap-skopeo:latest \
  copy --src-tls-verify=false \
    docker://SOURCE_IMAGE \
    docker-archive:/export/IMAGE.tar
```

## Validation Checklists

### Pre-Transfer Verification (Staging Environment)

- [ ] All container image digests verified with `skopeo inspect`
- [ ] All Helm chart SHA256 checksums verified
- [ ] All OS package RPM/DEB files verified with `rpm -K` or `dpkg -s`
- [ ] Artifact matrix (`artifact-matrix.md`) updated with all digests/checksums
- [ ] Vulnerability scans completed (Trivy/Grype with `--skip-db-update`)
- [ ] Signature verification completed where upstream provides signing keys

### Post-Import Verification (Air-Gapped Production)

- [ ] containerd/ Docker can pull images from internal registry
  ```bash
  crictl pull harbor.internal/app:tag
  ```
- [ ] Helm can pull charts from internal OCI repo
  ```bash
  helm pull oci://harbor.internal/charts/app --version X.Y.Z
  ```
- [ ] OS packages install without network access
  ```bash
  dnf install ./path/to/package.rpm -y
  # Or
  apt-get install -y ./path/to/package.deb
  ```
- [ ] Argo CD can resolve all application charts and images
- [ ] Custom resource definitions install from mirrored versions
- [ ] Health checks pass for all deployed components
  ```bash
  kubectl get pods -A
  # Or component-specific
  curl -f https://internal-service/health
  ```
- [ ] Check artifact-matrix.md validation commands succeed
  ```bash
  crictl pull harbor.internal/...
  # Verify digest matches matrix
  ```

### Emergency Rollback Verification

- [ ] Previous artifact versions verifiable and pullable
- [ ] Rollback procedures documented and tested
- [ ] Backup of pre-mirroring state preserved

### Checklist Sign-Off

| Category | Verified By | Date | Notes |
|---|---|---|---|
| Container images | | | |
| Helm charts | | | |
| OS packages | | | |
| Overall validation | | | |

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-26*