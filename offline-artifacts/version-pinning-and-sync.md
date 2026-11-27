# Version Pinning and Synchronization

This document describes the offline version pinning strategy for the platform, covering Kubespray/Kubernetes version matrices, container image tags, package versions, repository synchronization schedules, and drift detection.

## 📋 Kubespray Version Matrix

| Kubespray Release | Kubernetes (default) | Min Kubernetes | etcd | containerd | Helm | Cilium | Calico | Ansible | Python |
|---|---|---|---|---|---|---|---|---|---|
| `release-2.32` | 1.36.5 | v1.34.0 | 3.6.15 | 2.3.7 | 3.22.0 | 3.22.0 | 3.31.7 | >= 2.19.0, < 2.20.0 | 3.11 - 3.13 |
| `release-2.31` | 1.35.9 | v1.30 | 3.6.15 | 2.2.10 | 3.18.4 | 3.19.3 | 3.31.7 | >= 2.18.0, < 2.19.0 | 3.11 - 3.13 |
| `release-2.30` | 1.34.12 | v1.30 | 3.5.34 | 2.2.10 | 3.18.4 | 3.18.6 | 3.30.7 | >= 2.17.3 | 3.10 - 3.12 |
| `release-2.29` | 1.33.10 | v1.30 | 3.5.29 | 2.1.6 | 3.16.4 | 3.18.4 | 3.30.7 | >= 2.17.3 | 3.10 - 3.12 |
| `release-2.28` | 1.32.13 | v1.30 | 3.5.29 | 2.0.7 | 3.16.4 | 3.17.9 | 3.29.7 | >= 2.16.4 | 3.10 - 3.12 |

**Rule**: One virtualenv per Kubespray release. The Ansible version differs between releases (2.16.4 to 2.19.0), and a shared virtualenv will break one of them. Each venv installs that release's own `requirements.txt`.

**One inventory per (cluster, release) pair**: The group-vars differ between releases (variable names change). A single inventory would accumulate conditional variables for five releases, and every run would carry dead configuration.

## 🏷️ Container Image Tags

| Component | `release-2.32` | `release-2.31` | `release-2.30` | `release-2.29` | `release-2.28` | Source |
|---|---|---|---|---|---|---|
| `kube-apiserver` | `v1.36.5` | `v1.35.9` | `v1.34.12` | `v1.33.10` | `v1.32.13` | `registry.k8s.io` |
| `kube-controller-manager` | `v1.36.5` | `v1.35.9` | `v1.34.12` | `v1.33.10` | `v1.32.13` | `registry.k8s.io` |
| `kube-scheduler` | `v1.36.5` | `v1.35.9` | `v1.34.12` | `v1.33.10` | `v1.32.13` | `registry.k8s.io` |
| `kube-proxy` | `v1.36.5` | `v1.35.9` | `v1.34.12` | `v1.33.10` | `v1.32.13` | `registry.k8s.io` |
| `coredns` | `v1.14.2` | `v1.14.2` | `v1.14.2` | `v1.14.2` | `v1.14.2` | `registry.k8s.io` |
| `pause` | `3.9` | `3.9` | `3.9` | `3.9` | `3.9` | `registry.k8s.io` |
| `etcd` | `3.6.15` | `3.6.15` | `3.5.34` | `3.5.29` | `3.5.29` | `github.com/etcd-io/etcd` |
| `runc` | `2.3.7` | `2.2.10` | `2.2.10` | `2.1.6` | `2.1.6` | upstream |
| `CNI plugins` | `3.22.0` | `3.19.3` | `3.18.6` | `3.18.5` | `3.17.9` | `github.com/containernetworking/plugins` |
| `Helm CLI` | `3.22.0` | `3.18.4` | `3.18.4` | `3.16.4` | `3.16.4` | `https://get.helm.sh` |

## 📦 Package Versions

| Package | Version | Repository | Refresh Schedule | Offline Validation |
|---|---|---|---|---|
| `Oracle Linux BaseOS` | 8/9 | `nexus.internal/rpm-oraclelinux` | Monthly `dnf makecache` | `dnf install --releasever=9 ./mirror/ol9-baseos/*.rpm -y --nobest` |
| `Oracle Linux AppStream` | pin | `nexus.internal/rpm-oraclelinux` | Monthly `dnf makecache` | `dnf install ./path/to/package.rpm -y` |
| `RHEL-compatible packages` | pin | `nexus.internal/rpm-rhel` | Monthly via Satellite/`subscription-manager` | `dnf install ./path/to/package.rpm -y` |
| `Ubuntu packages` | 22.04/24.04 | `nexus.internal/deb-ubuntu` | Monthly `apt-get update` | `apt-get install -y ./mirror/ol9-deb/*.deb --no-install-recommends` |
| `Python wheels` | pinned | `nexus.internal/pypi` | Per release `pip download -r requirements.txt` | `pip install --no-index` |
| `Ansible collections` | pinned | `nexus.internal/ansible-galaxy` | Per release `ansible-galaxy collection download -r requirements.yml` | `ansible-galaxy collection list` |
| `NVIDIA driver` | pin (branch) | `nexus.internal/rpm-nvidia` | Per driver release | `nvidia-smi` |
| `NVIDIA Container Toolkit` | pin | `nexus.internal/rpm`, `harbor.internal/platform/nvidia-container-toolkit` | Per release | `nvidia-smi` in pod |

## 🔄 Repository Synchronization Schedules

| Repository Type | Synchronization Method | Schedule | Trigger |
|---|---|---|---|
| `Kubernetes control plane images` | `skopeo copy` from `registry.k8s.io` | After each K8s minor release | New K8s minor ISO published |
| `Kubespray release artifacts` | `git clone --mirror` from `github.com/kubernetes-sigs/kubespray` | Quarterly | Release branch update |
| `OS package repositories` | `dnf download --resolve` / `apt-mirror` | Monthly (1st weekend) | Cron job / apt-dnf periodic |
| `Helm charts` | `helm pull` from upstream repos | Weekly | CI pipeline run |
| `Trivy/Grype vulnerability DBs` | `trivy --skip-db-update` / `grype db update` | Monthly | Security team calendar |
| `NVIDIA driver/toolkit` | `dnf download --resolve` / `skopeo copy` | On new branch release | NVIDIA publish cycle |
| `Ansible Galaxy collections` | `ansible-galaxy collection download` | Per release cycle | `requirements.yml` update |

**Synchronization procedure** (example for OS packages):

```bash
# Oracle Linux monthly sync
dnf download --resolve \
  --repoid=ol9-baseos \
  --downloaddir=/mirror/ol9-baseos
dnf download --resolve \
  --repoid=ol9-appstream \
  --downloaddir=/mirror/ol9-appstream
dnf makecache --dir /mirror/ol9-baseos
dnf makecache --dir /mirror/ol9-appstream
```

## 🔍 Drift Detection

Drift is detected when the actual deployed component version diverges from the pinned version in the artifact matrix. Detection methods:

### Container Image Drift
```bash
# Verify mirrored digest matches matrix
crictl pull harbor.internal/platform/kubernetes/pause:3.9
crictl images | grep pause
# Compare output digest against artifact-matrix.md entry
```

### OS Package Drift
```bash
# Verify installed version against matrix
rpm -qa | grep oraclelinux
dnf list installed --releasever=9
apt-getInstalled=$(dpkg -l | grep '^ii' | grep ubuntu)
```

### Kubespray/Ansible Drift
```bash
# Verify ansible version against matrix
ansible --version | grep "ansible "
# Check installed collections
ansible-galaxy collection list | grep kubernetes-core
```

### Helm Drift
```bash
# Verify helm version
helm version | grep "version"
# Check chart versions against matrix
helm search repo --versions kube-prometheus-stack
```

### Drift Detection Workflow

```bash
# Step 1: Generate current state report
bash scripts/generate_drift_report.sh > /tmp/drift-report-$(date +%Y%m%d).md

# Step 2: Compare against artifact-matrix.md
python3 scripts/check_drift.py \
  --matrix /workspace/project/github/public-repository/cloud-native-guide-next/offline-artifacts/artifact-matrix.md \
  --report /tmp/drift-report-$(date +%Y%m%d).md

# Step 3: Output
# - No drift: "All versions match the pinned artifact matrix"
# - Drift detected: List of components with version mismatches
#   - Example: "Kubespray release-2.31: installed ansible 2.19.0, expected >=2.18.0, <2.19.0"
#   - Example: "kube-apiserver: mirrored digest v1.36.5-a1b2c3 does not match matrix v1.36.5-a1b2c3d4e5f6"
```

### Drift Categories

| Category | Description | Action |
|---|---|---|
| `minor` | Version is within allowed range (e.g., patch bump) | Document and continue |
| `patch` | Version matches exactly | No action needed |
| `out-of-range` | Version outside allowed range | Update pin or upgrade release |
| `missing` | Artifact not found in internal repo | Re-mirror or mark EXEMPT |

### Drift Rollback

When drift is detected:

1. **Container images**: Re-pull the pinned digest
   ```bash
   crictl pull harbor.internal/...@sha256:<digest>
   ```

2. **OS packages**: Re-install from mirrored repo
   ```bash
   dnf install ./mirror/ol9-baseos/<package>.rpm -y
   ```

3. **Kubespray/Ansible**: Re-run with pinned release
   ```bash
   source /opt/kubespray/venvs/release-2.32/bin/activate
   ansible-playbook -i inventory/prod cluster.yml
   ```

4. **Helm charts**: Re-pull from internal repo
   ```bash
   helm pull oci://harbor.internal/charts/kube-prometheus-stack --version X.Y.Z
   ```

---

**Document generated**: 2026-11-26  
**Owner**: DevOps Automator  
**Related artifacts**: `artifact-matrix.md`, `image-and-package-mirroring.md`, `offline-artifact-architecture.md`, `staging-and-import.md`