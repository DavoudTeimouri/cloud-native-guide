# Debian Family: Operational Procedures

This document covers operational procedures common to the Debian family (Ubuntu 22.04 LTS, Ubuntu 24.04 LTS, Debian 12). Distribution-specific exceptions are noted inline.

## APT Repositories

### Repository Configuration (Common)

All Debian-family systems consume packages from an internal Nexus mirror. Public internet access is not assumed.

```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ noble main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ noble-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ noble-security main restricted universe multiverse
```

For Ubuntu 22.04 (jammy):

```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ jammy main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ jammy-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ jammy-security main restricted universe multiverse
```

### Verification

```bash
# Update package index
apt-get update

# Verify repository signatures
apt-get update 2>&1 | grep -i "signature\|error\|warning"

# List installed packages from internal mirror
dpkg -l | grep containerd
```

## Package Installation

### Common Packages (All Debian-family)

```bash
apt-get update && apt-get install -y \
  chrony \
  auditd \
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
  apparmor
```

### Distribution-Specific Packages

| Package | Ubuntu 24.04 | Ubuntu 22.04 | Debian 12 | Notes |
|---------|-------------|-------------|-----------|-------|
| containerd.io | Yes | Yes | Yes | From internal mirror |
| apparmor | Yes | Yes | Yes | Mandatory Access Control |
| auditd | Yes | Yes | Yes | Audit daemon |
| firewalld | No | No | No | Not standard on Debian family; nftables/iptables used instead |

### Firewall Family Warning
**⚠️ Family-specific firewall:** Debian-family systems use **nftables** as the backend for iptables, with rules managed via nft syntax. RHEL-family systems use **firewalld** with a default-deny input policy. Do not mix firewall configurations across families — nftables rules will not work on RHEL systems and firewalld commands are not applicable to Debian systems.

```nft
#!/usr/sbin/nft -f
flush ruleset
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        ct state established,related accept
        iif "lo" accept
        tcp dport 22 ct state new accept
        tcp dport 6443 ct state new accept
        tcp dport 2379-2380 ct state new accept
        tcp dport 10250 ct state new accept
        tcp dport 10259 ct state new accept
        tcp dport 10257 ct state new accept
        tcp dport 30000-32767 ct state new accept
        udp dport 8472 ct state new accept  # VXLAN (Cilium)
        udp dport 6081 ct state new accept  # Geneve (Cilium)
        udp dport 4789 ct state new accept  # VXLAN (Calico/overlay)
        icmp type echo-request accept
        ct state invalid drop
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
    }
    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

```bash
# Apply nftables rules
nft -f /etc/nftables.conf
# Verify
nft list ruleset
```

### Version-Specific Notes

- **Ubuntu 24.04 (noble)**: Uses `apparmor` package. AppArmor is enabled by default.
- **Ubuntu 22.04 (jammy)**: Uses `apparmor` package. AppArmor is enabled by default.
- **Debian 12 (bookworm)**: Uses `apparmor` package. AppArmor profiles may differ from Ubuntu.

## systemd

### Enable and Start Services

```bash
# Enable and start chronyd
systemctl enable --now chronyd

# Enable and start containerd
systemctl enable --now containerd

# Enable and start apparmor
systemctl enable --now apparmor

# Verify service status
systemctl is-active chronyd containerd apparmor
```

### Common Units

| Service | Unit Name | Enabled | Started |
|---------|-----------|---------|---------|
| Time synchronization | chronyd | Yes | Yes |
| Container runtime | containerd | Yes | Yes |
| AppArmor | apparmor | Yes | Yes |
| Audit daemon | auditd | Yes | Yes |

## AppArmor

### AppArmor State (Debian Family)

AppArmor **Enforcing** is the platform standard for all Debian-family OS versions.

```bash
# Check current AppArmor status
apparmor_status

# Expected: profiles loaded, some in enforce mode

# Verify apparmor service is active
systemctl is-active apparmor
```

### Container AppArmor

Kubernetes uses AppArmor profiles for container runtime security. Verify the `containerd` AppArmor profile is loaded.

## nftables / iptables Considerations

### Firewall Configuration

Debian-family systems use **nftables** as the backend for iptables. The firewall rules are managed with nftables syntax.

```nft
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        ct state established,related accept
        iif "lo" accept
        tcp dport 22 ct state new accept
        tcp dport 6443 ct state new accept
        tcp dport 2379-2380 ct state new accept
        tcp dport 10250 ct state new accept
        tcp dport 10259 ct state new accept
        tcp dport 10257 ct state new accept
        tcp dport 30000-32767 ct state new accept
        udp dport 8472 ct state new accept  # VXLAN (Cilium)
        udp dport 6081 ct state new accept  # Geneve (Cilium)
        udp dport 4789 ct state new accept  # VXLAN (Calico/overlay)
        icmp type echo-request accept
        ct state invalid drop
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
        ct state established,related accept
    }
    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

```bash
# Apply nftables rules
nft -f /etc/nftables.conf

# Verify
nft list ruleset
```

### Security Safeguards

- **No default-deny rules that lock administrators out.** SSH port 22 is always allowed.
- **Do not overwrite SSH configuration unsafely.** nftables rules do not modify `/etc/ssh/sshd_config`.
- Firewall changes are persistent and verified after application.

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
apt-get update && apt-get install -y containerd.io

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
cp /path/to/internal-ca.crt /usr/local/share/ca-certificates/internal-ca.crt

# Update CA trust
update-ca-certificates

# Verify
trust list | grep -i internal
```

### Distribution-Specific Paths

| Distribution | CA Trust Directory | Command |
|-------------|-------------------|---------|
| Ubuntu 24.04 | /usr/local/share/ca-certificates/ | update-ca-certificates |
| Ubuntu 22.04 | /usr/local/share/ca-certificates/ | update-ca-certificates |
| Debian 12 | /usr/local/share/ca-certificates/ | update-ca-certificates |

## Features That Must Not Be Blindly Reused

- **AppArmor profiles**: Distribution-specific. Ubuntu and Debian AppArmor profiles differ. Test before applying across distributions.
- **nftables rulesets**: Rule syntax may differ between nftables versions. Verify with `nft -c` (check mode) before applying.
- **Package names**: May differ between Debian-family distributions (e.g., `auditd` on Ubuntu vs `auditd` on Debian).
- **Kernel module names**: Generally consistent but verify with `modinfo` before loading.
- **SELinux procedures do NOT apply to Debian family.** Do not apply SELinux commands or configuration files to Ubuntu or Debian systems.
