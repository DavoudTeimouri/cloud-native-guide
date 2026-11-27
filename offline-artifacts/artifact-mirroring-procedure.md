# Artifact Mirroring Procedure

This document describes the procedure for mirroring artifacts into air-gapped environments,
covering container images, Helm charts, OS packages, and the validation checklist for
offline verification.

## Container Image Mirroring with Skopeo

### Prerequisites

- `skopeo` installed on the staging host
- Access to upstream registries (Docker Hub, ghcr.io, quay.io)
- Internal registry (Harbor or Nexus) with sufficient storage
- containerd or Docker configured to pull from the internal registry

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

## Helm Chart Packaging

### Prerequisites

- `helm` CLI (v3.22.0 or later)
- Access to upstream chart repositories
- Internal Harbor OCI project or Nexus helm-hosted repository

### Pull and Package Charts

```bash
#!/bin/bash
set -euo pipefail

CHARTS=(
  "oci://registry-1.docker.io/bitnami/nginx:15.0.0"
  "oci://registry-1.docker.io/bitnami/nginx-ingress-controller:2.8.0"
  "https://charts.jetstack.io/cert-manager-v1.21.2.tgz"
  "https://charts.cilium.io/cilium-1.20.3.tgz"
  "https://metallb.github.io/metallb/metallb-0.16.1.tgz"
)

mkdir -p ./charts-mirror

for chart in "${CHARTS[@]}"; do
  echo "Mirroring $chart"
  helm pull "$chart" --destination ./charts-mirror --untar=false
done
```

### Push to Internal Helm Repo

```bash
#!/bin/bash
set -euo pipefail

for chart in ./charts-mirror/*.tgz; do
  helm push "$chart" oci://staging-harbor.internal/charts
done
```

### Verifying Chart Integrity

```bash
sha256sum charts-mirror/*.tgz
# Or verify against the artifact-matrix.md entry
```

### Client Configuration

Add the internal Helm repo:

```bash
helm repo add internal-harbor oci://harbor.internal/charts
helm repo update
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

# Mirror Ubuntu packages
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

### Verify OS Package Availability Offline

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

## Air-Gapped Validation Checklist

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