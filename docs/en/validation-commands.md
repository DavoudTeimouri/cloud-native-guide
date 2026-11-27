# Validation Commands

Commands for verifying Kubernetes node preparation.

## OS Verification

```bash
# Verify OS
cat /etc/os-release

# Verify kernel
uname -r

# Verify cgroups
stat -fc %T /sys/fs/cgroup
# Expected: cgroup2fs
```

## Sysctl Verification

```bash
# Verify key sysctl settings
sysctl net.bridge.bridge-nf-call-iptables net.ipv4.ip_forward net.ipv4.conf.all.rp_filter
sysctl net.bridge.bridge-nf-call-ip6tables net.ipv4.conf.all.forwarding
```

## Kernel Module Verification

```bash
# Verify loaded modules
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'
```

## Containerd Verification

```bash
# Verify containerd version
crictl version

# Verify CRI endpoint
crictl info

# Verify service status
systemctl is-active containerd

# Validate config
containerd --config /etc/containerd/config.toml --validate
```

## Firewall Verification

```bash
# nftables (Debian family)
nft list ruleset

# firewalld (RHEL family)
firewall-cmd --list-all
```

## Time Synchronization Verification

```bash
# Check chrony status
chronyc tracking
chronyc sources -v
# Target: skew < 100 ms across all nodes
```

## SELinux / AppArmor Verification

```bash
# SELinux (RHEL family)
getenforce
# Expected: Enforcing

# AppArmor (Debian family)
apparmor_status
```

## Swap Verification

```bash
# Check swap status
swapon --show
# Expected: no output (swap disabled)
```

## Ansible Verification

```bash
# Verify all hosts report correct OS
ansible all -i inventories/production/hosts.ini -m setup | grep -E "ansible_distribution|ansible_distribution_version"

# Verify services
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active chronyd"
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active containerd"
ansible all -i inventories/production/hosts.ini -m shell -a "crictl version"
```

## Expected Validation Results

| Check | Expected Result |
|-------|----------------|
| `cat /etc/os-release` | Supported OS/version |
| `uname -r` | >= 4.19 (Kubernetes), >= 5.10 (Cilium) |
| `stat -fc %T /sys/fs/cgroup` | cgroup2fs |
| `getenforce` (RHEL) | Enforcing |
| `apparmor_status` (Debian) | Profiles loaded |
| `systemctl is-active containerd` | active |
| `crictl info` | RC=0, CRI endpoint reachable |
| `chronyc tracking` | Skew < 100 ms |

## References

- [OS Preparation Guide](os-preparation.md)
- [Kernel and Networking Preparation](kernel-networking-preparation.md)
- [Containerd Prerequisites](containerd-prerequisites.md)

---\n*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*
