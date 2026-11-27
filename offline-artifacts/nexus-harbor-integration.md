# Nexus and Harbor Integration

## A. Purpose and scope

Document how Nexus (artifact/repository manager) and Harbor (container image registry) integrate in the offline platform. Both are required for air-gapped operation: Nexus hosts OS packages, Helm charts, and binaries; Harbor hosts container images.

## B. Architecture

```
                                    +-------------------+
                                    |  External network |
                                    |   (connected)     |
                                    +-------------------+
                                             |
                                             v (mirror only)
                                    +-------------------+
                                    |   Staging host    |
                                    |  (download only)  |
                                    +-------------------+
                                             |
                                             v (skopeo/curl)
        +-------------------+   +----------------------+
        |   Harbor          |   |      Nexus           |
        | (container images)|   | (OS pkgs, Helm, bins)|
        | harbor.internal   |   | nexus.internal       |
        +-------------------+   +----------------------+
                 |                       |
                 v                       v
        containerd hosts             dnf/apt/yum clients
        (via hosts.toml mirror)      (via repo files)
```

## C. Harbor

### Images mirrored

| Image source | Internal destination | Integrity |
|-------------|---------------------|-----------|
| registry.k8s.io | harbor.internal/platform/kubernetes | digest pinned |
| quay.io/kubespray/kubespray | harbor.internal/platform/kubespray | digest pinned |
| quay.io/ceph/ceph | harbor.internal/platform/ceph | digest pinned |
| quay.io/rook/ceph | harbor.internal/platform/rook-ceph | digest pinned |
| quay.io/cephcsi | harbor.internal/platform/cephcsi | digest pinned |
| docker.io/* | harbor.internal/platform/<upstream-path> | digest pinned |

### Containerd mirror configuration

```toml
# /etc/containerd/hosts.toml
server = "https://harbor.internal"

[host."https://harbor.internal"]
  capabilities = ["pull", "resolve", "push"]

  [host."https://harbor.internal".headers]
    Authorization = "Basic {{ registry_credentials_b64 }}"

  [host."https://harbor.internal".mirrors]
    # Mirrors upstream registries
    [host."https://harbor.internal".mirrors."https://registry-1.docker.io"]
    [host."https://harbor.internal".mirrors."https://registry.k8s.io"]
    [host."https://harbor.internal".mirrors."https://quay.io"]
```

### Mirroring procedure

```bash
# Mirror a single image
skopeo copy --all \
  docker://registry.k8s.io/kube-apiserver:v1.36.5 \
  docker://harbor.internal/platform/kubernetes/kube-apiserver:v1.36.5 \
  --dest-tls-verify=false

# Verify
skopeo inspect docker://harbor.internal/platform/kubernetes/kube-apiserver:v1.36.5
```

## D. Nexus

### Repositories

| Repository | Format | Contents |
|------------|--------|----------|
| nexus.internal/rpm | yum | OS packages, containerd, Ceph |
| nexus.internal/deb | apt | OS packages, containerd, Ceph |
| nexus.internal/raw | raw | Helm CLI, kubectl, binaries |
| nexus.internal/helm | helm | Helm charts (Cilium, cert-manager, etc.) |

### OS package repository configuration

```ini
# /etc/yum.repos.d/nexus.repo
[nexus-containerd]
name=Nexus containerd
baseurl=https://nexus.internal/rpm/containerd
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/rpm/containerd/gpg

[nexus-ceph]
name=Nexus Ceph
baseurl=https://nexus.internal/rpm-ceph
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/rpm-ceph/gpg
```

### Helm chart mirroring

```bash
# Pull chart from upstream
helm pull cilium/cilium --version 1.20.3 --untar

# Push to Nexus
helm push cilium/ oci://nexus.internal/helm
```

## E. Offline workflow

1. **Connected staging**: Download artifacts to staging host
2. **Verify integrity**: Check checksums and signatures
3. **Import to Harbor/Nexus**: skopeo copy for images, helm push for charts, copy for RPMs/DEBs
4. **Update artifact matrix**: Record versions, checksums, internal destinations
5. **Deploy offline**: Use internal registries and repos only

## F. Cross-references

- `offline-artifacts/artifact-matrix.md` — Complete artifact inventory
- `offline-artifacts/offline-artifact-architecture.md` — Architecture overview
- `kubespray/kubespray-deployment.md` §Offline image configuration
- `compatibility/version-matrix.md` — Version pins
