# Air-gapped deployment

[Previous step](../storage/ceph/cephadm-deployment.md) | [Next step](../management-cluster/rancher/rancher.md)

---

## A. Purpose and scope

**Air-gapped** = zero egress from any node at any stage. All artifacts are mirrored to internal infrastructure **before** any node is installed.

| Artifact type | Mirror target | Tool |
|---------------|---------------|------|
| Container images | Internal OCI registry (Harbor/Nexus/OCI) | `skopeo`, `crane`, `oras` |
| OS packages (yum/apt) | Internal package mirror | `reposync`, `apt-mirror`, `pulp` |
| Helm charts | Internal Helm repo (ChartMuseum/Harbor/OCI) | `helm pull`, `helm push` |
| Binaries (kubectl, helm, cephadm, etc.) | Internal HTTP file server | `rsync`, `wget` |
| Kubespray Ansible collections | Internal Ansible Galaxy / collection dir | `ansible-galaxy collection install` |

## B. Air-gap workstation (the "mirror station")

A single internet-connected workstation runs the mirroring scripts, then artifacts are transferred via **sneakernet** (encrypted USB, signed ISO) to the air-gapped site.

### Workstation requirements

- Linux (Ubuntu 24.04 / OL9 / Rocky 9)
- ~500 GB free disk for full mirror
- `skopeo`, `helm`, `crane`, `oras`, `reposync`, `createrepo_c`, `apt-mirror` installed
- GPG key for signing mirrors (optional but recommended)

### Mirroring procedure (run on workstation)

```bash
#!/usr/bin/env bash
# mirror-all.sh — run on the air-gap workstation
set -euo pipefail

MIRROR_DIR="/mnt/mirror"
REGISTRY="registry.internal:5000"
HELM_REPO="chartmuseum.internal"

mkdir -p "$MIRROR_DIR"/{images,packages,charts,binaries}

# 1. Container images — from compatibility/version-matrix.md
# Kubespray images
skopeo copy --all docker://quay.io/kubespray/kubespray:v2.32.0 \
  docker://$REGISTRY/kubespray/kubespray:v2.32.0
# Kubernetes control plane images (kubeadm pulls these)
skopeo copy --all docker://registry.k8s.io/kube-apiserver:v1.36.5 \
  docker://$REGISTRY/k8s/kube-apiserver:v1.36.5
skopeo copy --all docker://registry.k8s.io/kube-controller-manager:v1.36.5 \
  docker://$REGISTRY/k8s/kube-controller-manager:v1.36.5
skopeo copy --all docker://registry.k8s.io/kube-scheduler:v1.36.5 \
  docker://$REGISTRY/k8s/kube-scheduler:v1.36.5
skopeo copy --all docker://registry.k8s.io/kube-proxy:v1.36.5 \
  docker://$REGISTRY/k8s/kube-proxy:v1.36.5
skopeo copy --all docker://registry.k8s.io/etcd:3.6.15 \
  docker://$REGISTRY/k8s/etcd:3.6.15
skopeo copy --all docker://registry.k8s.io/pause:3.10 \
  docker://$REGISTRY/k8s/pause:3.10
skopeo copy --all docker://registry.k8s.io/coredns/coredns:v1.14.2 \
  docker://$REGISTRY/k8s/coredns:v1.14.2
# CNI images
skopeo copy --all docker://quay.io/cilium/cilium:v1.20.3 \
  docker://$REGISTRY/cilium/cilium:v1.20.3
# Add-ons (MetalLB, Ingress, Cert-manager, etc.) — see version-matrix.md
# Ceph images
skopeo copy --all docker://quay.io/ceph/ceph:v20.2.4 \
  docker://$REGISTRY/ceph/ceph:v20.2.4
# Rook
skopeo copy --all docker://rook/ceph:v1.21.0 \
  docker://$REGISTRY/rook/ceph:v1.21.0
# GPU Operator
skopeo copy --all docker://nvcr.io/nvidia/gpu-operator:v26.7.2 \
  docker://$REGISTRY/nvidia/gpu-operator:v26.7.2

# 2. OS packages
# Ubuntu 24.04 (for cloud-init nodes)
apt-mirror /etc/apt/mirror.list  # mirror.list points to internal mirror
# Oracle Linux 9 / Rocky 9
reposync --repoid=baseos --repoid=appstream --repoid=epel \
  --download-metadata --download-path="$MIRROR_DIR/packages/ol9"
createrepo_c "$MIRROR_DIR/packages/ol9"

# 3. Helm charts
for chart in \
  cilium/cilium-1.20.3.tgz \
  metallb/metallb-0.16.1.tgz \
  nginx-stable/nginx-ingress-2.8.0.tgz \
  jetstack/cert-manager-v1.21.2.tgz \
  rook-release/rook-ceph-1.21.0.tgz \
  prometheus-community/kube-prometheus-stack-92.11.0.tgz \
  grafana/loki-distributed-7.5.0.tgz; do
  helm pull $chart --destination "$MIRROR_DIR/charts"
done
# Push to internal ChartMuseum
for f in "$MIRROR_DIR/charts"/*.tgz; do
  curl --data-binary "@$f" https://$HELM_REPO/api/charts
done

# 4. Binaries (kubectl, kubeadm, kubelet, helm, crictl, cephadm, talosctl, etc.)
# Download from official sources, place in $MIRROR_DIR/binaries/
# Verify checksums against official releases

# 5. Package and sign
tar -czf /mnt/usb/airgap-mirror-$(date +%Y%m%d).tar.gz -C "$MIRROR_DIR" .
# Optional: gpg --sign --detach-sign /mnt/usb/airgap-mirror-*.tar.gz
```

## C. Site-side infrastructure (inside the air gap)

### 1. Internal container registry

```bash
# Harbor / Nexus / plain OCI registry on registry.internal:5000
# TLS certs trusted by all nodes (ca-bundle in /etc/containerd/certs.d/)
```

### 2. Internal package mirror

```bash
# NGINX serving /var/www/html/packages/
# repo files on nodes point to http://mirror.internal/packages/ol9
```

### 3. Internal Helm repository

```bash
# ChartMuseum or Harbor Helm repo at chartmuseum.internal
# helm repo add internal https://chartmuseum.internal
```

### 4. Internal binary server

```bash
# NGINX serving /var/www/html/binaries/
# Nodes fetch: wget https://binaries.internal/kubectl-v1.36.5
```

## D. Node preparation (inside air gap)

### Containerd config (all nodes)

```toml
# /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry.k8s.io"]
  endpoint = ["https://registry.internal:5000"]
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."quay.io"]
  endpoint = ["https://registry.internal:5000"]
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://registry.internal:5000"]
[plugins."io.containerd.grpc.v1.cri".registry.configs."registry.internal:5000".tls]
  ca_file = "/etc/containerd/certs.d/registry.internal:5000/ca.crt"
```

### Kubeadm/Kubespray config

```yaml
# kubespray group_vars/all/offline.yml
containerd_registry_mirrors:
  registry.k8s.io: "https://registry.internal:5000"
  quay.io: "https://registry.internal:5000"
  docker.io: "https://registry.internal:5000"
containerd_registry_configs:
  "registry.internal:5000":
    tls:
      ca_file: "/etc/containerd/certs.d/registry.internal:5000/ca.crt"

# kubespray group_vars/k8s_cluster/k8s-cluster.yml
kube_image_repo: "registry.internal:5000/k8s"
kube_version: "v1.36.5"
etcd_version: "3.6.15"
containerd_version: "2.3.7"
cilium_version: "1.20.3"
```

### Helm values (example)

```yaml
# values-airgap.yaml
global:
  imageRegistry: registry.internal:5000
  imagePullSecrets: [internal-registry-secret]

cilium:
  image:
    repository: registry.internal:5000/cilium/cilium
    tag: v1.20.3

metallb:
  controller:
    image:
      repository: registry.internal:5000/metallb/controller
      tag: v0.16.1
  speaker:
    image:
      repository: registry.internal:5000/metallb/speaker
      tag: v0.16.1
```

## E. Deployment inside the air gap

### 1. Transfer mirror to site

```bash
# On site admin host (after sneakernet transfer)
tar -xzf airgap-mirror-20261028.tar.gz -C /opt/airgap-mirror
```

### 2. Configure local registry as source

```bash
# On admin host
export CONTAINER_REGISTRY=registry.internal:5000
export HELM_REPO=https://chartmuseum.internal
```

### 3. Run bundle + deploy

```bash
# From guide repo (cloned to air-gapped admin host via sneakernet)
python3 scripts/bundle.py --answers answers/example.json --out dist/
cd dist
./deploy.sh --dry-run
./deploy.sh
```

The `deploy.sh` generated by the bundle uses:
- `kubespray` with `offline.yml` pointing to internal registry
- `helm` with `--repo https://chartmuseum.internal`
- `cephadm bootstrap --image registry.internal:5000/ceph/ceph:v20.2.4`

## F. Version matrix

This method uses the same Kubespray releases as the standard Kubespray path. **All versions are pinned in `compatibility/version-matrix.md`** and must be mirrored exactly. See the "Kubespray → Kubernetes / etcd" and "Ceph → MON / OSD / Engine" matrices on the Deployment page.

| Component | Pinned version (example) | Mirror location |
|-----------|--------------------------|-----------------|
| Kubespray | v2.32.0 | registry.internal:5000/kubespray/kubespray:v2.32.0 |
| Kubernetes | v1.36.5 | registry.internal:5000/k8s/... |
| etcd | 3.6.15 | registry.internal:5000/k8s/etcd:3.6.15 |
| containerd | 2.3.7 | packages/ol9/containerd-2.3.7.rpm |
| Cilium | 1.20.3 | chartmuseum.internal/cilium-1.20.3.tgz |
| Ceph | 20.2.4 | registry.internal:5000/ceph/ceph:v20.2.4 |
| Rook | v1.21.0 | registry.internal:5000/rook/ceph:v1.21.0 |

## G. Ongoing operations in air gap

| Operation | Procedure |
|-----------|-----------|
| **Cluster upgrade** | 1. Mirror new versions on workstation 2. Transfer 3. Update `kubesprayRelease` in answers 4. Re-run bundle + deploy |
| **Add node** | Same as "Existing cluster expansion" — node prep uses internal mirrors only |
| **Ceph upgrade** | Mirror new Ceph image, update `cephImage` in answers, run cephadm upgrade |
| **Security patch** | Mirror patched images/packages, transfer, rolling restart via kubespray/helm |

## H. Validation checklist (before declaring air gap operational)

- [ ] All container images pulled from `registry.internal:5000` (no external pulls in logs)
- [ ] All OS packages installed from `mirror.internal` (no external repos in `/etc/yum.repos.d/` or `/etc/apt/sources.list.d/`)
- [ ] All Helm charts deployed from `chartmuseum.internal`
- [ ] All binaries fetched from `binaries.internal`
- [ ] `kubectl version`, `helm version`, `cephadm --version` work offline
- [ ] `deploy.sh --dry-run` completes with zero external connections

---

**Source of truth**: This document + `compatibility/version-matrix.md` + `scripts/mirror_all.py` (to be created) + guide bundle scripts.
