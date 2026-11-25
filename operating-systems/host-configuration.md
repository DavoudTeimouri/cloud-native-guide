# Host Configuration Baseline

This document defines the baseline host configuration for all nodes in the Cloud-Native Stack.

## Operating Systems

| OS | Version | Kernel | Status |
|---|---|---|---|
| Oracle Linux | 9 | 5.14 | Preferred |
| Ubuntu Server | 24.04 LTS | 6.6 | Preferred |
| Ubuntu Server | 22.04 LTS | 5.15 | Supported |
| RHEL/Rocky/Alma | 9 | 5.14 | Supported |

## Kernel Requirements

For Kubernetes >= 1.32:
- Recommended 4.x LTS kernel: 4.19
- Any 5.x or 6.x supported
- cgroups v2 needs >= 4.15 (5.8+ recommended)

If kernel below requirement: No verified workaround exists for kernel incompatibility. Setting `kubeadm_ignore_preflight_errors: [SystemVerification]` is a documented deviation from kubespray defaults and should NOT be used as a solution to kernel incompatibility. If proceeding despite known kernel issues, this flag may be set at your own risk.

## Base Configuration

### Sysctl

```yaml
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

### Containerd Configuration

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

### Kubelet Configuration

```yaml
# /var/lib/kubelet/config.yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cgroupDriver: systemd
clusterDNS:
  - 10.32.0.10
clusterDomain: cluster.local
cgroupsPerQOS: true
enforceNodeAllocatable:
  - pods
  - system-reserved
  - kube-reserved
evictionHard:
  memory.available: "500Mi"
  nodefs.available: "10%"
  imagefs.available: "15%"
evictionMinimumReclaim:
  memory.available: "1Gi"
  nodefs.available: "1Gi"
  imagefs.available: "1Gi"
kubeReserved:
  cpu: "500m"
  memory: "512Mi"
  ephemeral-storage: "1Gi"
systemReserved:
  cpu: "500m"
  memory: "512Mi"
  ephemeral-storage: "1Gi"
maxPods: 110
podsPerCore: 10
protectKernelDefaults: true
```

## Security Baseline

### CIS Benchmarks

- **Oracle Linux 9**: CIS Benchmark v2.0.0 Level 1
- **Ubuntu 24.04**: CIS Benchmark v2.0.0 Level 1

### SELinux / AppArmor

| OS | Mandatory Access Control |
|---|---|
| Oracle Linux 9 | SELinux Enforcing |
| Ubuntu 24.04 | AppArmor Enforcing |

### Auditd

```ini
# /etc/audit/rules.d/30-kubernetes.rules
# Kubernetes API server
-w /etc/kubernetes/ -p wa -k kubernetes
-w /etc/kubernetes/manifests -p wa -k kubernetes_manifests
-w /var/lib/kubelet -p wa -k kubelet
-w /etc/containerd -p wa -k container
-w /etc/cni -p wa -k cni
-w /opt/cni -p wa -k cni
-w /var/lib/kubelet -p wa -k kubelet
```

### SSH Hardening

```ssh
# /etc/ssh/sshd_config
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 2
LoginGraceTime 30
Banner /etc/issue.net
```

## Time Synchronization

### Chrony

```conf
# /etc/chrony.conf
server 10.10.0.1 iburst
server 10.10.0.2 iburst
driftfile /var/lib/chrony/drift
makestep 1.0 3
rtcsync
logdir /var/log/chrony
```

### Verification

```bash
chronyc tracking
chronyc sources -v
# Target: skew < 100 ms across all nodes
```

## SSH Hardening

```ssh
# /etc/ssh/sshd_config
Port 22
Protocol 2
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 2
LoginGraceTime 30
AllowUsers ansible ansible-user
```

## Firewall

### nftables

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
        udp dport 8472 ct state new accept  # VXLAN
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

## Package Repositories

### Oracle Linux 9

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

### Ubuntu 24.04

```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ noble main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ noble-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ noble-security main restricted universe multiverse
```

## Package Installation

```bash
# Oracle Linux
dnf install -y \
  chrony \
  audit \
  audit-libs \
  container-selinux \
  containerd.io \
  kubectl \
  kubeadm \
  kubelet \
  kubernetes-cni \
  nfs-utils \
  iscsi-initiator-utils \
  multipath-tools \
  lvm2 \
  cryptsetup \
  jq \
  vim \
  htop \
  net-tools \
  tcpdump \
  strace \
  sysstat

# Ubuntu
apt-get update && apt-get install -y \
  chrony \
  auditd \
  containerd.io \
  kubectl \
  kubeadm \
  kubelet \
  kubernetes-cni \
  nfs-common \
  open-iscsi \
  multipath-tools \
  lvm2 \
  cryptsetup \
  jq \
  vim \
  htop \
  net-tools \
  tcpdump \
  strace \
  sysstat
```

## Validation

```bash
# Verify OS
cat /etc/os-release

# Verify kernel
uname -r

# Verify sysctl
sysctl -p /etc/sysctl.d/99-kubernetes.conf

# Verify container runtime
crictl version
crictl info

# Verify kubelet
kubelet --version

# Verify time sync
chronyc tracking

# Verify firewall
nft list ruleset

# Verify SSH
sshd -T | grep -E "permitrootlogin|passwordauthentication|pubkeyauthentication"
```

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*