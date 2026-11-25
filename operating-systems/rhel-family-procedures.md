# RHEL-Compatible Family: Operational Procedures

This document covers operational procedures common to the RHEL-compatible family (Oracle Linux 9, RHEL 9, Rocky Linux 9, AlmaLinux 9). Distribution-specific exceptions are noted inline.

## DNF/YUM Repositories

### Repository Configuration (Common)

All RHEL-family systems consume packages from an internal Nexus mirror. Public internet access is not assumed.

```ini
# /etc/yum.repos.d/internal.repo
[ol9-baseos]
name=Oracle Linux 9 BaseOS
baseurl=https://nexus.internal/repository/ol9-baseos/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-baseos/RPM-GPG-KEY-oracle

[ol9-appstream]
name=Oracle Linux 9 AppStream
baseurl=https://nexus.internal/repository/ol9-appstream/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-appstream/RPM-GPG-KEY-oracle
```

### Verification

```bash
# List enabled repositories
dnf repolist

# Verify repository metadata
dnf repolist -v ol9-baseos | grep -E "repo id|repo status"

# Clean and refresh metadata
dnf clean all
dnf makecache
```

## Package Installation

### Common Packages (All RHEL-family)

```bash
dnf install -y \
  chrony \
  audit \
  audit-libs \
  jq \
  vim \
  htop \
  net-tools \
  tcpdump \
  strace \
  sysstat \
  curl \
  wget \
  tar \
  gzip \
  unzip \
  rsync \
  openssl \
  ca-certificates \
  container-selinux
```

### Distribution-Specific Packages

| Package | Oracle Linux 9 | RHEL 9 | Rocky Linux 9 | AlmaLinux 9 | Notes |
|---------|---------------|--------|--------------|-------------|-------|
| container-selinux | Yes | Yes | Yes | Yes | Required for containerd |
| containerd.io | Yes | Yes | Yes | Yes | From internal mirror |
| firewalld | Yes | Yes | Yes | Yes | Firewall management |


### Firewall Family Warning

**⚠️ Family-specific firewall:** RHEL-family systems use **firewalld** with a default-deny input policy, managing Kubernetes and CNI ports explicitly. Debian-family systems use **nftables** as the backend for iptables. Do not mix firewall configurations across families — firewalld commands are not applicable to Debian systems and nftables rules will not work on RHEL systems.


```bash
# Enable and start firewalld
systemctl enable --now firewalld

# Add Kubernetes API port
firewall-cmd --permanent --add-port=6443/tcp

# Add kubelet API port
firewall-cmd --permanent --add-port=10250/tcp

# Add VXLAN port (Cilium)
firewall-cmd --permanent --add-port=8472/udp

# Add Geneve port (Cilium)
firewall-cmd --permanent --add-port=6081/udp

# Add NodePort range
firewall-cmd --permanent --add-port=30000-32767/tcp

# Reload firewall
firewall-cmd --reload

# Verify
firewall-cmd --list-all
```
### Version-Specific Notes

- **Oracle Linux 9**: Uses `container-selinux` from the OL9 AppStream repository. `containerd.io` must be installed from the internal Nexus mirror; public downloads are not used in offline workflows.
- **RHEL 9**: Requires a valid Red Hat subscription for package access. Offline workflows use the internal mirror exclusively.
- **Rocky Linux 9 / AlmaLinux 9**: Binary-compatible with RHEL 9. Same package lists apply. Verify GPG keys match the distribution vendor.

## systemd

### Enable and Start Services

```bash
# Enable and start chronyd
systemctl enable --now chronyd

# Enable and start containerd
systemctl enable --now containerd

# Verify service status
systemctl is-active chronyd containerd
```

### Common Units

| Service | Unit Name | Enabled | Started |
|---------|-----------|---------|---------|
| Time synchronization | chronyd | Yes | Yes |
| Container runtime | containerd | Yes | Yes |
| Audit daemon | auditd | Yes | Yes |
| Firewall | firewalld | Yes | Yes (fail-closed) |

## SELinux

### SELinux State (RHEL Family)

SELinux **Enforcing** is the platform standard for all RHEL-family OS versions.

```bash
# Check current SELinux state
getenforce

# Expected output: Enforcing

# Set SELinux to Enforcing (temporary)
setenforce 1

# Set SELinux to Enforcing (persistent)
# Edit /etc/selinux/config: SELINUX=enforcing
```

### Container SELinux

```bash
# Verify container-selinux is installed
rpm -q container-selinux

# Expected: container-selinux-2.x-x.el9.x86_64
```

### Do Not Blindly Reuse

- SELinux policies are distribution-specific. Do not copy SELinux booleans or policy modules from one RHEL-family distribution to another without testing.
- RHEL 9 uses SELinux policy version 34. Older distributions may use different policy versions.

## firewalld

### Firewall Configuration (Fail-Closed)

firewalld manages the firewall with a default-deny input policy. Kubernetes and CNI ports are opened explicitly.

```bash
# Enable and start firewalld
systemctl enable --now firewalld

# Add Kubernetes API port
firewall-cmd --permanent --add-port=6443/tcp

# Add kubelet API port
firewall-cmd --permanent --add-port=10250/tcp

# Add VXLAN port (Cilium)
firewall-cmd --permanent --add-port=8472/udp

# Add Geneve port (Cilium)
firewall-cmd --permanent --add-port=6081/udp

# Add NodePort range
firewall-cmd --permanent --add-port=30000-32767/tcp

# Reload firewall
firewall-cmd --reload

# Verify
firewall-cmd --list-all
```

### Security Safeguards

- **No default-deny rules that lock administrators out.** SSH port 22 is always allowed.
- **Do not overwrite SSH configuration unsafely.** firewalld rules do not modify `/etc/ssh/sshd_config`.
- Firewall changes are persistent (`--permanent`) and verified after reload.

## Kernel Modules and sysctl

### Required Kernel Modules

```bash
# Load required modules
modprobe overlay
modprobe br_netfilter
modprobe ip_vs
modprobe ip_vs_rr
modprobe ip_vs_wrr
modprobe ip_vs_sh
modprobe nf_conntrack

# Persist across reboots
cat > /etc/modules-load.d/k8s.conf << 'EOF'
overlay
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack
EOF

# Verify modules loaded
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'
```

### sysctl Settings

```ini
# /etc/sysctl.d/99-kubernetes.conf
# Network
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Memory
vm.swappiness = 10
vm.overcommit_memory = 1
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1

# File system
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 8192
fs.file-max = 2097152

# Kernel
kernel.panic = 10
kernel.panic_on_oops = 1
kernel.keys.root_maxkeys = 1000000
kernel.keys.root_maxbytes = 25000000
```

```bash
# Apply sysctl settings
sysctl -p /etc/sysctl.d/99-kubernetes.conf

# Verify
sysctl net.bridge.bridge-nf-call-iptables net.ipv4.ip_forward
```

## Time Synchronization

### Chrony Configuration

```conf
# /etc/chrony.conf
server 10.10.0.1 iburst
server 10.10.0.2 iburst
driftfile /var/lib/chrony/drift
makestep 1.0 3
rtcsync
logdir /var/log/chrony
```

```bash
# Enable and start chronyd
systemctl enable --now chronyd

# Verify time synchronization
chronyc tracking
chronyc sources -v

# Target: skew < 100 ms across all nodes
```

## Containerd Prerequisites

### Installation

```bash
# Install containerd from internal mirror
dnf install -y containerd.io

# Enable and start containerd
systemctl enable --now containerd

# Verify
crictl version
crictl info
```

### Configuration

```toml
# /etc/containerd/config.toml
version = 2

[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "harbor.internal/base/pause:3.9"
  max_container_log_line_size = 16384

  [plugins."io.containerd.grpc.v1.cri".containerd]
    snapshotter = "overlayfs"
    default_runtime_name = "runc"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
      runtime_type = "io.containerd.runc.v2"
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
        SystemdCgroup = true

  [plugins."io.containerd.grpc.v1.cri".cni]
    bin_dir = "/opt/cni/bin"
    conf_dir = "/etc/cni/net.d"

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://harbor.internal/library"]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry.k8s.io"]
  endpoint = ["https://harbor.internal/k8s"]

[plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal".tls]
  ca_file = "/etc/containerd/certs.d/harbor.internal/ca.crt"
```

### Offline Workflow Note

- **No public downloads.** containerd images and packages are pulled from the internal Nexus mirror.
- **containerd 2.3.7** is the Kubespray release-2.32 pinned version. Do not substitute with a different version without compatibility validation.

## Certificate Trust

### Internal CA

```bash
# Copy internal CA certificate
cp /path/to/internal-ca.crt /etc/pki/ca-trust/source/anchors/

# Update CA trust
update-ca-trust extract

# Verify
trust list | grep -i internal
```

### Distribution-Specific Paths

| Distribution | CA Trust Directory | Command |
|-------------|-------------------|---------|
| Oracle Linux 9 | /etc/pki/ca-trust/source/anchors/ | update-ca-trust extract |
| RHEL 9 | /etc/pki/ca-trust/source/anchors/ | update-ca-trust extract |
| Rocky Linux 9 | /etc/pki/ca-trust/source/anchors/ | update-ca-trust extract |
| AlmaLinux 9 | /etc/pki/ca-trust/source/anchors/ | update-ca-trust extract |

## Features That Must Not Be Blindly Reused

- **SELinux booleans**: Distribution-specific. Test before applying across distributions.
- **firewalld zones**: Default zone may differ between distributions. Verify `firewall-cmd --get-default-zone`.
- **Package names**: May differ between RHEL-family distributions (e.g., `containerd.io` vs `containerd`).
- **Kernel module names**: Generally consistent but verify with `modinfo` before loading.
- **SELinux vs AppArmor**: RHEL-family uses **SELinux Enforcing** as platform standard (Debian-family uses **AppArmor Enforcing**). Within RHEL family, policies are distribution-specific — do not copy booleans or policy modules between distributions without testing.
