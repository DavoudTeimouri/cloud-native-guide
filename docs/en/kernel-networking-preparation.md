# Kernel and Networking Preparation

Kernel modules, sysctl settings, and firewall configuration for Kubernetes nodes.

## Kernel Modules

### Required Modules

| Module | Purpose |
|--------|---------|
| overlay | OverlayFS for container storage |
| br_netfilter | Bridge netfilter for Kubernetes networking |
| ip_vs | IP virtual server for kube-proxy |
| ip_vs_rr | IPVS round-robin scheduler |
| ip_vs_wrr | IPVS weighted round-robin scheduler |
| ip_vs_sh | IPVS shortest hash scheduler |
| nf_conntrack | Netfilter connection tracking |

### Loading Modules

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

## Sysctl Settings

### Configuration File

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

### Apply and Verify

```bash
# Apply sysctl settings
sysctl -p /etc/sysctl.d/99-kubernetes.conf

# Verify key settings
sysctl net.bridge.bridge-nf-call-iptables net.ipv4.ip_forward net.ipv4.conf.all.rp_filter
```

## Firewall Configuration

### nftables (Debian Family)

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

### firewalld (RHEL Family)

```bash
# Enable and start firewalld
systemctl enable --now firewalld

# Add Kubernetes ports
firewall-cmd --permanent --add-port=6443/tcp
firewall-cmd --permanent --add-port=10250/tcp
firewall-cmd --permanent --add-port=8472/udp
firewall-cmd --permanent --add-port=6081/udp
firewall-cmd --permanent --add-port=30000-32767/tcp

# Reload and verify
firewall-cmd --reload
firewall-cmd --list-all
```

### Security Safeguards

- **SSH port 22 is always allowed** — no default-deny lockout
- **No unsafe SSH configuration overwrites** — firewall rules do not modify `/etc/ssh/sshd_config`

## References

- [OS Preparation Guide](os-preparation.md)
- [RHEL Family Procedures](../operating-systems/host-configuration.md)
- [Debian Family Procedures](../operating-systems/host-configuration.md)

---\n*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*
