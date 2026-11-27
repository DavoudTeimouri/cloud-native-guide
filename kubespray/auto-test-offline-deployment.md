# Kubespray Offline Deployment Procedure

## 📋 Purpose

Document the complete offline deployment procedure for Kubespray in air-gapped environments. This procedure covers image mirroring, OS package preparation, bootstrap validation, and end-to-end installation — enabling Kubernetes cluster deployment without any outbound internet access.

---

## 🏗️ Infrastructure Prerequisites

### Internal Services Required

| Service | Description | Configuration |
|---|---|---|
| **Container Image Registry** | Harbor or compatible registry containing all Kubespray-required images | `registry_host` variable |
| **OS Package Repository** | Yum (RHEL/Oracle Linux) or Debian/Ubuntu repository with required OS packages | `yum_repo` / `debian_repo` / `ubuntu_repo` |
| **Static Files Mirror** | HTTP reverse proxy/cache serving binaries, zips, and helm charts | `files_repo` variable |
| **Optional: PyPI/Helm Registries** | Internal Python and Helm package registries | `pypi_repo` / `helm_repo` |

### Repository Path Mapping

Preserve upstream repository paths in the internal registry to minimize variable overrides:

```yaml
# group_vars/all/offline.yml
registry_host: "harbor.internal"
files_repo: "http://files-repo.internal"
yum_repo: "http://yum-repo.internal"
debian_repo: "http://deb-repo.internal"
ubuntu_repo: "http://ubuntu-repo.internal"
```

---

## 📦 Image Mirroring

### Step 1: Generate Image List

In a connected environment, generate the complete image list using Kubespray's offline tooling:

```bash
# Clone the pinned Kubespray release
git clone --depth 1 https://github.com/kubernetes-sigs/kubespray.git
cd kubespray
git checkout release-2.32  # or pinned version from kubespray/VERSION

# Generate the image list
cd contrib/offline
./generate_list.sh
```

**Output files:**
- `temp/files.list.template` — static files (binaries, zips)
- `temp/images.list.template` — all container images including kube-apiserver, kube-controller-manager, kube-scheduler, kube-proxy

### Step 2: Mirror Images to Internal Registry

Pull each image from upstream and push to the internal registry:

```bash
# Example: Mirror control plane images
skopeo copy --dest-daemon=false \
  docker://k8s.gcr.io/kube-apiserver:v1.31.0 \
  docker://harbor.internal/k8s-tools/kube-apiserver:v1.31.0

skopey copy --dest-daemon=false \
  docker://k8s.gcr.io/kube-controller-manager:v1.31.0 \
  docker://harbor.internal/k8s-tools/kube-controller-manager:v1.31.0

skopeo copy --dest-daemon=false \
  docker://k8s.gcr.io/kube-scheduler:v1.31.0 \
  docker://harbor.internal/k8s-tools/kube-scheduler:v1.31.0

skopeo copy --dest-daemon=false \
  docker://k8s.gcr.io/kube-proxy:v1.31.0 \
  docker://harbor.internal/k8s-tools/kube-proxy:v1.31.0
```

**Mirror all images from the generated list:**

```bash
while read -r image tag; do
  skopeo copy --dest-daemon=false \
    "docker://${image}:${tag}" \
    "docker://${registry_host}/${image}:${tag}"
done < temp/images.list.template
```

### Step 3: Verify Image Mirroring

Pull test from the offline environment:

```bash
# Verify each critical image is pullable without internet access
crictl image pull ${registry_host}/kube-apiserver:v1.31.0
crictl image pull ${registry_host}/kube-proxy:v1.31.0
```

---

## � OS Package Preparation

### Step 1: Create OS Package Repository

**For RHEL/Oracle Linux:**

```bash
# Generate repository metadata
createrepo_c ${yum_repo}/base
createrepo_c ${yum_repo}/containerd

# Required packages containerd and dependencies
# Mirror these from the connected environment:
# - containerd package and GPG key
# - Kubernetes packages (kubelet, kubectl, kubeadm)
# - Any site-specific RPMs
```

**For Debian/Ubuntu:**

```bash
# Create apt repository
apt-mirror ${debian_repo} \
  or manually construct /etc/apt/sources.list.d/internal.list

# Include required pockets
deb https://${debian_repo}/ focal main restricted
deb https://${debian_repo}/ focal-updates main restricted
deb https://${debian_repo}/ focal-security main restricted
```

### Step 2: Configure Package Repositories on Target Nodes

** containerd RHEL configuration (`group_vars/all/offline.yml`):**

```yaml
# Oracle Linux / RHEL family
containerd_rh_repo_base_url: "${yum_repo}/containerd"
containerd_rh_repo_gpgkey: "${yum_repo}/containerd/gpg"

# Ubuntu
containerd_ubuntu_repo_base_url: "${ubuntu_repo}/containerd"
containerd_ubuntu_repo_gpgkey: "${ubuntu_repo}/containerd/gpg"
containerd_ubuntu_repo_repokey: 'YOURREPOKEY'
```

**Kubespray group variables:**

```yaml
# group_vars/k8s_cluster/k8s-cluster.yml
containerd_rh_repo_base_url: "${yum_repo}/containerd"
kube_pods_subnet: "10.30.0.0/16"
kube_service_addresses: "10.32.0.0/16"
```

### Step 3: Verify OS Package Availability

```bash
# On a target node with no internet access:
yum install -y containerd.io-1.7.x  # RHEL/Oracle Linux
# or
apt-get update && apt-get install -y containerd  # Debian/Ubuntu
```

---

## 🔧 Bootstrap Validation

### Pre-Check Checklist

Run these validations before starting the Ansible deployment:

```bash
# 1. Verify inventory file exists and is valid
ls -la inventory/<cluster>/hosts.ini

# 2. Verify group vars are configured
ls -la inventory/<cluster>/group_vars/

# 3. Test connectivity to all nodes
ansible -i inventory/<cluster>/hosts.ini all -m ping

# 4. Syntax check the playbook
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml --syntax-check

# 5. Dry-run limited to control-plane nodes
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml \
  -b --check --diff --limit control-plane

# 6. Verify containerd is running on all nodes
ansible -i inventory/<cluster>/hosts.ini all -a "containerd --version"

# 7. Verify Docker/containerd registry configuration
ansible -i inventory/<cluster>/hosts.ini all -a "cat /etc/containerd/config.toml 2>/dev/null || cat /etc/containerd/config.toml"
```

### Expected Validation Results

- All nodes respond to Ansible ping
- Playbook syntax is valid
- containerd configuration points to internal registry
- OS packages are installable from internal repositories
- All required container images are available locally

---

## 🚀 End-to-End Offline Installation

### Step 1: Preparation

```bash
# From the Automation Management Server or bastion host

# 1. Set up the Kubespray directory with pinned release
git clone --depth 1 https://github.com/kubernetes-sigs/kubespray.git
cd kubespray
echo "release-2.32" > VERSION  # or pinned version

# 2. Copy the generated inventory
cp -r /path/to/generated/inventory inventory/mycluster

# 3. Verify offline group vars are in place
ls inventory/mycluster/group_vars/all/offline.yml
ls inventory/mycluster/group_vars/all/main.yml
```

### Step 2: Pre-Deployment Checks

```bash
# Run pre-deployment validation
cd /workspace/project/github/public-repository/cloud-native-guide.phase6/kubespray

# Check inventory validity
ansible -i inventory/mycluster/hosts.ini all -m ping

# Syntax check
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml --syntax-check

# Limited check on control-plane
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml \
  -b --check --diff --limit control-plane
```

### Step 3: Deploy the Cluster

```bash
# Execute the full deployment
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b

# Expected output phases:
# - Pre-flight checks
# - containerd setup and configuration
# - Kubernetes components installation
# - CNI (Cilium) installation
# - CoreDNS and kube-proxy setup
# - Cluster add-ons configuration
```

### Step 4: Post-Deployment Validation

```bash
# Verify cluster status
kubectl get nodes -o wide

# Verify all pods are running
kubectl get pods -A

# Verify control plane health
kubectl get --raw='/readyz?verbose'

# Verify etcd health
etcdctl --endpoints=https://127.0.0.1:2379 \
  endpoint health \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
```

### Step 5: Idempotency and Reruns

Kubespray is idempotent by design. Reruns are safe and are the normal way to apply corrected variables:

```bash
# Rerun with updated variables
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b

# Add or remove workers
# - Add worker: Add to k8s-node in hosts.ini, run cluster.yml --limit <host>
# - Remove worker: drain, remove from inventory, run cluster.yml --limit <host>
# - Replace worker: drain + remove + rebuild via Ansible + re-add
```

### Step 6: Reset a Node (if needed)

```bash
# Teardown a node while preserving cluster state
ansible-playbook -i inventory/mycluster/hosts.ini reset.yml --limit <host>
```

---

## 🔄 Offline Deployment Workflow Summary

```mermaid
flowchart TD
    A[Generate image list in connected env] --> B[Mirror images to internal registry]
    B --> C[Create OS package repository]
    C --> D[Configure containerd registry mirrors]
    D --> E[Validate bootstrap (ping, syntax-check, --check)]
    E --> F[Deploy cluster with ansible-playbook]
    F --> G[Post-deployment validation]
    G --> H{All checks pass?}
    H -->|Yes| I[Cluster operational]
    H -->|No| J[Fix issues, rerun]
    J --> F
```

---

## 📦 Artifact Matrix Reference

Maintain artifact accountability in `offline-artifacts/artifact-matrix.md`. Track per-component:

| Component | Upstream Source | Internal Mirror | Mirror Status | Last Verified |
|---|---|---|---|---|
| kube-apiserver | k8s.gcr.io | harbor.internal | ✅ verified | 2026-11-26 |
| kube-controller-manager | k8s.gcr.io | harbor.internal | ✅ verified | 2026-11-26 |
| kube-scheduler | k8s.gcr.io | harbor.internal | ✅ verified | 2026-11-26 |
| kube-proxy | k8s.gcr.io | harbor.internal | ✅ verified | 2026-11-26 |
| containerd | upstream | yum/repo / apt-repo | ✅ verified | 2026-11-26 |
| Cilium Helm chart | Cilium repo | files_repo/helm.cilium.io | ✅ verified | 2026-11-26 |

---

## 🛠️ Troubleshooting Common Issues

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `image pull error: EOF` | Image not mirrored to internal registry | Verify `skopeo copy` completed for all images; run pull test |
| `yum/dnf error: repomd cannot be fetched` | OS package repo not accessible | Check `yum_repo`/`debian_repo` URL; verify repository metadata |
| `cannot connect to registry` | TLS/config issue in containerd | Verify `/etc/containerd/certs.d/` configuration; check `containerd_registries_mirrors` |
| `ansible ping timeout` | Network connectivity issue | Verify SSH access; check firewall rules between bastion and nodes |
| `syntax error in playbook` | Incompatible Kubespray version with inventory | Pin `kubespray/VERSION` to match inventory release |
| `etcd member unhealthy` | Disk pressure or misconfiguration | Check etcd disk usage; verify member addition/removal procedure |

---

**Document generated**: 2026-11-26  
**Environment**: Air-gapped deployment  
**Kubespray version**: release-2.32 (pinned via `kubespray/VERSION`)  
**Registry**: harbor.internal (internal image registry)  
**OS**: Oracle Linux 9 / Ubuntu 22.04 (per inventory configuration)