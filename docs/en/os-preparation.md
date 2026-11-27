# OS Preparation Guide (English)

This guide covers the automated preparation of Linux hosts for the Cloud-Native Stack platform using Ansible.

## Supported Operating Systems

| OS | Version | Kernel | Status |
|---|---|---|---|
| Oracle Linux | 9 | 5.14 (UEK/RHCK) | Preferred |
| Ubuntu Server | 24.04 LTS | 6.8+ (GA), 6.11+ (HWE) | Preferred |
| Ubuntu Server | 22.04 LTS | 5.15 (GA), 6.x (HWE) | Supported |
| RHEL / Rocky / Alma | 9 | 5.14 | Supported |

**Note**: Oracle Linux 8 (kernel 4.18) and Ubuntu 20.04 are below the minimum kernel 4.19 recommended by Kubespray and are not supported. Ubuntu 24.04 LTS ships with kernel 6.8+ GA and 6.11+ HWE; the 6.6 kernel referenced in earlier drafts is not the GA kernel.

**CNI-Specific Kernel Requirements:**
- **Cilium 1.20+**: Requires Linux kernel >= 5.10 (per upstream Cilium documentation). Ubuntu 22.04 HWE (5.15+) and Oracle Linux 9 UEK/RHCK (5.14+) meet this requirement.
- **Calico**: Supports kernel >= 4.19.
- The effective kernel requirement is the maximum of Kubernetes general minimum (4.19) and CNI-specific minimum.

## Prerequisites

### Control Node
- Python 3.11-3.13
- ansible-core >=2.19.0, <2.20.0 (per Kubespray v2.32.0 requirements)
- Ansible 12 (per Kubespray v2.32.0)
- SSH key access to all target hosts
- Access to internal Nexus and Harbor

**Note**: The Ansible environment must be prepared on the control node independently of target-node preparation. This role does not manage control-node dependencies.

### Target Hosts
- SSH server running on port 22
- `ansible` user with passwordless sudo
- Python 3 installed
- Network access to internal Nexus (`https://nexus.internal`) and Harbor (`https://harbor.internal`)

## Inventory Preparation

### 1. Copy and Customize Inventory

```bash
cd automation/ansible
cp inventories/staging/hosts.ini inventories/production/hosts.ini
```

Edit `inventories/production/hosts.ini` with your actual hostnames and IP addresses:

```ini
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13

[worker]
k8s-w-1 ansible_host=10.30.0.11
k8s-w-2 ansible_host=10.30.0.12

[gpu]
k8s-gpu-1 ansible_host=10.50.0.11

[storage]
ceph-st-1 ansible_host=10.40.0.11
ceph-st-2 ansible_host=10.40.0.12
ceph-st-3 ansible_host=10.40.0.13
...
```

### 2. Configure Group Variables

Edit the following files in `group_vars/all/`:

**`main.yml`** - Global settings:
```yaml
ntp_servers:
  - 10.10.0.1
  - 10.10.0.2

dns_servers:
  - 10.10.0.53
  - 10.10.0.54

internal_registry: "harbor.internal:5000"
internal_helm_repo: "https://harbor.internal/charts"
internal_nexus: "https://nexus.internal"
```

**`offline.yml`** - Internal mirrors (REQUIRED for offline mode):
```yaml
ol9_baseos_repo_url: "https://nexus.internal/repository/ol9-baseos/"
ol9_appstream_repo_url: "https://nexus.internal/repository/ol9-appstream/"

ubuntu_main_repo_url: "https://nexus.internal/repository/ubuntu-main/"
ubuntu_updates_repo_url: "https://nexus.internal/repository/ubuntu-updates/"
ubuntu_security_repo_url: "https://nexus.internal/repository/ubuntu-security/"

container_registry:
  url: "harbor.internal:5000"
```

**`vault.yml`** - Vault connection (no secrets stored here):
```yaml
vault_addr: "https://vault.internal:8200"
vault_namespace: "platform"
```

## Execution

### 1. Validate Setup

```bash
cd automation/ansible

# Syntax check
ansible-playbook -i inventories/production/hosts.ini site.yml --syntax-check

# Lint
ansible-lint playbooks/ roles/

# Dry-run (check mode)
ansible-playbook -i inventories/production/hosts.ini site.yml --check --diff
```

### 2. Run Default OS Baseline

```bash
# Default baseline (does NOT include monitoring, kubernetes, or GPU/DCGM)
ansible-playbook -i inventories/production/hosts.ini site.yml

# Or run individual playbooks
ansible-playbook -i inventories/production/hosts.ini playbooks/base.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/repositories.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/security.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/time-sync.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/containerd.yml
```

### 3. Kubernetes Node Prerequisites (Opt-in)

```bash
# After OS baseline + containerd are complete
ansible-playbook -i inventories/production/hosts.ini playbooks/k8s-node-prereqs.yml
```

### 4. Opt-in Additional Components

```bash
# Monitoring agents (opt-in)
ansible-playbook -i inventories/production/hosts.ini playbooks/monitoring.yml

# Kubernetes/Kubespray cluster deployment (separate explicit workflow, after k8s-node-prereqs)
ansible-playbook -i inventories/production/hosts.ini playbooks/kubernetes.yml

# GPU/DCGM (requires GPU role implementation)
# ansible-playbook -i inventories/production/hosts.ini playbooks/gpu.yml
```

### 5. Targeted Execution

```bash
# Limit to control plane nodes only
ansible-playbook -i inventories/production/hosts.ini site.yml --limit control-plane

# Run specific role tags
ansible-playbook -i inventories/production/hosts.ini site.yml --tags base,security
ansible-playbook -i inventories/production/hosts.ini site.yml --tags containerd
```

### 5. Post-Run Verification

```bash
# Verify idempotency (0 changed on second run)
ansible-playbook -i inventories/production/hosts.ini site.yml

# Verify all hosts
ansible all -i inventories/production/hosts.ini -m setup | grep -E "ansible_distribution|ansible_distribution_version"

# Verify specific services
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active chronyd"
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active node_exporter"
ansible all -i inventories/production/hosts.ini -m shell -a "crictl version"
```

## What Gets Configured

### Base Role (`roles/base/`)
- Hostname validation/configuration
- Base packages (chrony, audit, jq, vim, htop, net-tools, tcpdump, strace, sysstat, curl, wget, etc.)
- Required kernel modules (overlay, br_netfilter, ip_vs, nf_conntrack)
- Sysctl settings for Kubernetes (IP forwarding, bridge-nf, memory, filesystem, kernel)
- **SSH hardening via drop-in (`/etc/ssh/sshd_config.d/99-hardening.conf`) — does not overwrite `/etc/ssh/sshd_config`**
- Chrony time synchronization with internal NTP servers
- systemd-resolved DNS configuration with internal DNS servers
- Internal CA certificate directory

### Repositories Role (`roles/repositories/`)
- Disables public repositories
- Configures internal Oracle Linux 9 DNF repositories (BaseOS, AppStream, Add-ons)
- Configures internal Ubuntu APT repositories (main, updates, security)
- Downloads and installs Nexus GPG keys

### Security Role (`roles/security/`)
- Auditd with Kubernetes-specific rules
- SELinux Enforcing (Oracle Linux) / AppArmor (Ubuntu)
- Kernel hardening sysctls (kptr_restrict, dmesg_restrict, ptrace_scope, mmap_min_addr)
- nftables firewall with default-deny inbound, explicit allow for:
  - SSH (22) — **restricted to `security_firewall_allowed_source_cidrs` (no default, must be explicitly configured)**
  - Kubernetes API (6443)
  - etcd (2379-2380)
  - kubelet (10250)
  - kube-scheduler (10259)
  - kube-controller-manager (10257)
  - NodePort range (30000-32767)
  - VXLAN (8472 UDP) — for Cilium VXLAN mode
  - Geneve (6081 UDP) — for Cilium Geneve mode
  - VXLAN (4789 UDP) — for Calico/overlay
  - ICMP echo-request
- **Does NOT flush legacy iptables rules** (explicit migration procedure required if needed)

### Monitoring Role (`roles/monitoring/`) — **OPT-IN**
- Prometheus Node Exporter (port 9100)
- Fluent Bit log forwarder to Loki
- DCGM Exporter (GPU nodes only, port 9400) — **only runs on nodes with `nvidia-smi` present**
- **Opt-in via `ansible-playbook playbooks/monitoring.yml`**
- **Offline mode**: Fails gracefully if `monitoring_node_exporter_download_url` / `monitoring_dcgm_exporter_download_url` not set to internal mirror; does not silently fall back to public GitHub URLs

### Containerd Role (`roles/containerd/`)
- Installs containerd.io from internal repositories
- Generates containerd config with:
  - Systemd cgroup driver
  - OverlayFS snapshotter
  - Registry mirrors for docker.io, registry.k8s.io, ghcr.io, quay.io → Harbor
  - TLS configuration for Harbor
- Creates registry mirror configurations with CA certificates

### Kubernetes Node Prerequisites Role (`roles/k8s-node-prereqs/`) — **OPT-IN**
- Validates OS compatibility with Kubespray/Kubernetes versions
- Validates kernel version: Kubernetes general minimum 4.19 + CNI-specific (Cilium >=5.10, Calico >=4.19)
- Loads required kernel modules (overlay, br_netfilter, ip_vs, nf_conntrack) — ip_vs_rr/wrr/sh built into ip_vs on modern kernels
- **Sysctl ownership: base role applies 17 settings (6 Kubernetes + 11 performance) to `/etc/sysctl.d/99-kubernetes.conf`; this role validates them**
- Applies CNI-specific sysctls only: Cilium (2: IPv4/IPv6 forwarding) to `/etc/sysctl.d/99-cilium.conf`; Calico (3: VXLAN, WireGuard, IPVS) conditional on features
- Performs read-only Cilium kernel config checks: BPF fs, cgroup v2, CONFIG_BPF, CONFIG_BPF_SYSCALL, CONFIG_CGROUP_BPF, CONFIG_VXLAN/GENEVE, CONFIG_NETFILTER, CONFIG_BPF_JIT; warns if unverifiable
- Performs read-only Calico kernel config checks: CONFIG_VXLAN, CONFIG_WIREGUARD, CONFIG_IP_VS, CONFIG_NETFILTER; warns if unverifiable
- Swap handling: **Non-destructive, explicit opt-in via `k8s_swap_policy: "managed"` + `k8s_swap_confirm_disable: true`**
  - Detects all swap sources (partitions, files, fstab, systemd units, zram)
  - Reports detected sources; fails if policy is "disable" without opt-in
  - With `k8s_swap_policy: "managed"`: backs up `/etc/fstab`, comments fstab swap entries; **does NOT delete swapfiles, zram config, or systemd units**
  - Temporary swapoff **requires `k8s_swap_confirm_disable: true`**; otherwise reports manual steps
  - With `k8s_swap_policy: "preserve"`: keeps existing swap configuration
- Verifies cgroups v2 is enabled (cgroup2fs)
- SELinux/AppArmor: Reports current state, warns if not target state, does NOT blindly change
- Creates required directories (/etc/kubernetes, /var/lib/kubelet, /var/lib/etcd, /opt/cni/bin, /etc/cni/net.d, /etc/containerd, /etc/kubernetes/manifests)
- Verifies Containerd: service active + CRI endpoint reachable (`crictl info`)
- Checks for reboot-required state (needs-restarting on RedHat, /var/run/reboot-required on Debian)
- Documents required network ports by role (control-plane vs worker) and CNI (Cilium VXLAN 8472 UDP, Geneve 6081 UDP; Calico VXLAN 4789 UDP, WireGuard)
- **Opt-in via `ansible-playbook playbooks/k8s-node-prereqs.yml`**
- **Does NOT install Kubernetes, join cluster, or run Kubespray**
- **Prerequisites**: OS baseline, repositories, security, time-sync, containerd must be complete first

### Kubespray Cluster Deployment (`playbooks/kubernetes.yml`) — **SEPARATE WORKFLOW**
- Runs Kubespray `cluster.yml` from pinned checkout at `/opt/kubespray/<version>`
- Requires all node prerequisites to be satisfied first
- **Opt-in via `ansible-playbook playbooks/kubernetes.yml`**
- **Does NOT run as part of default site.yml**

## Offline/Restricted Network Operation

Three operating modes are defined:

### 1. Restricted Network (Default)
- Internal package mirrors (Nexus) for DNF/APT
- Internal container registry (Harbor) for containerd images
- GPG keys and CA certificates from internal sources
- **Monitoring/DCGM binaries**: Download from internal mirror if URLs configured; fails gracefully with clear error if not

### 2. Package-Mirror-Only
- Package installation from internal Nexus only
- Other artifacts (monitoring binaries, GPU artifacts) may require manual staging
- Explicit external dependencies documented per role

### 3. Full Air-Gap — **NOT YET SUPPORTED**
- Ansible collections and Python dependencies do not yet have a documented, reproducible internal staging/install path
- Until these are addressed, full air-gap Ansible execution is not supported
- Work in progress: internal staging for Ansible collections and Python dependencies via Nexus

Configure `offline_mode: true` in `group_vars/all/offline.yml` to enable restricted-network behavior (modes 1 and 2).

## Reboot Handling

If kernel or core library updates are applied, the playbook will:
- Report `REBOOT REQUIRED` in the output
- Set `k8s_reboot_required: true`
- **NOT automatically reboot** (operator control required)

```bash
# Manual reboot when ready
ansible all -i inventories/production/hosts.ini -m reboot
```

**Note**: The playbook detects reboot-required state using:
- RedHat family: `needs-restarting -r` (exit code 1 = reboot required)
- Debian family: existence of `/var/run/reboot-required`

A second run of the playbook will report the same reboot-required state if the host has not been rebooted. This is expected behavior — the marker persists until the host is actually rebooted.

## Identity Boundary

**SSSD/realmd host joining is NOT performed by the default OS preparation playbooks.**

Per ADR-0015 and the catalog `idpIntegration` definition, the standard platform identity model uses Keycloak as the central OIDC broker for application-layer identity federation. Host-level directory integration requires a separate accepted ADR.

The base role preserves:
- Local break-glass account (`emergency` user, UID 999, key-only)
- SSH key-based authentication for `ansible` user
- Secure administrative access

## Troubleshooting

### Package Installation Failures
```bash
# Verify internal repository access
ansible all -i inventories/production/hosts.ini -m shell -a "curl -f https://nexus.internal/repository/ol9-baseos/"

# Check DNF/APT cache
ansible all -i inventories/production/hosts.ini -m shell -a "dnf clean all && dnf makecache"
```

### SSH Connection Issues
```bash
# Test SSH connectivity
ansible all -i inventories/production/hosts.ini -m ping

# Verify host keys
ssh-keyscan target-host >> ~/.ssh/known_hosts
```

### Time Sync Failures
```bash
# Check chrony status
ansible all -i inventories/production/hosts.ini -m shell -a "chronyc tracking"
ansible all -i inventories/production/hosts.ini -m shell -a "chronyc sources -v"
```

### Containerd Issues
```bash
# Verify containerd config
ansible all -i inventories/production/hosts.ini -m shell -a "containerd --config /etc/containerd/config.toml --validate"

# Check registry mirrors
ansible all -i inventories/production/hosts.ini -m shell -a "cat /etc/containerd/certs.d/*/hosts.toml"

# Verify Containerd service and CRI
ansible all -i inventories/production/hosts.ini -m systemd -a "name=containerd"
ansible all -i inventories/production/hosts.ini -m shell -a "crictl info"
```

## Limitations

1. **No automatic disk partitioning** - Assumes OS is already installed with appropriate partition layout
2. **No hardware RAID configuration** - Must be configured before OS installation
3. **No BIOS/firmware updates** - Must be performed separately
4. **No network interface configuration** - Assumes interfaces are configured by OS installer or cloud-init
5. **GPU driver installation** - Handled separately by `gpu` role after OS baseline

## References

- [Ansible Project README](../automation/ansible/index.md)
- [Inventory Usage Guide](../inventories/README.md)
- [Platform Standards](../requirements/platform-standards.md)
- [Version & Compatibility Matrix](../compatibility/version-matrix.md)
- [Kubespray Deployment Guide](../en/kubespray-deployment.md)
- [Persian OS Preparation Guide](../fa/os-preparation.md)
- [Persian Kubespray Deployment Guide](../fa/kubespray-deployment.md)

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-24*