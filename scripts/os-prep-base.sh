#!/usr/bin/env bash
# OS preparation script — base role (all Linux nodes)
# Applies: users, SSH, NTP, DNS, kernel params, modules, swap/THP, limits,
# firewall, auditd, AIDE, unattended updates, CA bundle, containerd prereqs
set -euo pipefail

LOG="/var/log/os-prep-base.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-base: $*"; }

fail() { echo "[$(date -Iseconds)] ERROR: $*" >&2; exit 1; }

# Detect OS family
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID="$ID"
    OS_VERSION_ID="$VERSION_ID"
else
    fail "Cannot detect OS"
fi

log "Detected OS: $ID $VERSION_ID"

# ---------- 1. Package updates ----------
log "Updating packages"
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    dnf update -y --enablerepo=internal-base || fail "dnf update failed"
elif [ "$OS_ID" = "ubuntu" ] || [ "$OS_ID" = "debian" ]; then
    apt-get update && apt-get upgrade -y || fail "apt upgrade failed"
fi

# ---------- 2. Users and groups ----------
log "Creating admin user"
id ansible 2>/dev/null || useradd -m -s /bin/bash ansible
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    usermod -aG wheel ansible
else
    usermod -aG sudo ansible
fi
echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible
chmod 440 /etc/sudoers.d/ansible

# SSH key for ansible user
install -d -m 700 /home/ansible/.ssh
if [ -f /root/.ssh/id_ed25519.pub ]; then
    cp /root/.ssh/id_ed25519.pub /home/ansible/.ssh/authorized_keys
elif [ -f /home/admin/.ssh/id_ed25519.pub ]; then
    cp /home/admin/.ssh/id_ed25519.pub /home/ansible/.ssh/authorized_keys
fi
chmod 600 /home/ansible/.ssh/authorized_keys
chown -R ansible:ansible /home/ansible/.ssh

# ---------- 3. SSH hardening ----------
log "Hardening SSH"
SSHD_CONF="/etc/ssh/sshd_config"
for kv in "PermitRootLogin no" "PasswordAuthentication no" "PubkeyAuthentication yes" \
          "X11Forwarding no" "MaxAuthTries 3" "ClientAliveInterval 300" "ClientAliveCountMax 0"; do
    key="${kv%% *}"
    if grep -q "^${key}" "$SSHD_CONF"; then
        sed -i "s/^${key}.*/${kv}/" "$SSHD_CONF"
    else
        echo "$kv" >> "$SSHD_CONF"
    fi
done
systemctl restart sshd || systemctl restart ssh

# ---------- 4. NTP / chrony ----------
log "Configuring chrony"
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    dnf install -y chrony
else
    apt-get install -y chrony
fi

cat > /etc/chrony.conf <<'EOF'
server 10.10.0.1 iburst
server 10.10.0.2 iburst
allow 10.10.0.0/16
local stratum 10
EOF

systemctl enable --now chronyd
chronyc tracking

# ---------- 5. DNS ----------
log "Configuring DNS"
if [ -f /etc/systemd/resolved.conf ]; then
    sed -i 's/^#DNS=/DNS=10.10.0.53/' /etc/systemd/resolved.conf
    sed -i 's/^#Domains=/Domains=internal/' /etc/systemd/resolved.conf
    systemctl restart systemd-resolved
fi

# ---------- 6. Kernel parameters ----------
log "Applying sysctl parameters"
cat > /etc/sysctl.d/99-cloud-native.conf <<'EOF'
net.ipv4.ip_forward=1
net.bridge.bridge-nf-call-iptables=1
net.bridge.bridge-nf-call-ip6tables=1
vm.swappiness=0
vm.overcommit_memory=1
vm.panic_on_oom=0
kernel.panic=10
kernel.softlockup_panic=1
net.core.somaxconn=65535
net.core.netdev_max_backlog=65535
net.ipv4.tcp_tw_reuse=1
net.ipv4.ip_local_port_range=1024 65535
EOF
sysctl --system

# ---------- 7. Kernel modules ----------
log "Loading kernel modules"
cat > /etc/modules-load.d/containerd.conf <<'EOF'
overlay
br_netfilter
ip_vs
nf_conntrack
EOF
modprobe overlay
modprobe br_netfilter
modprobe ip_vs
modprobe nf_conntrack

# ---------- 8. Swap and THP ----------
log "Disabling swap and THP"
swapoff -a
sed -i '/[[:space:]]swap[[:space:]]/ s/^/#/' /etc/fstab

echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag

cat > /etc/tuned/tuned-thp-no.conf <<'EOF'
[main]
summary=Disable transparent huge pages

[vm]
transparent_hugepages=never
EOF
tuned-adm profile tuned-thp-no 2>/dev/null || true

# ---------- 9. Limits ----------
log "Setting file descriptor and process limits"
cat > /etc/security/limits.d/99-cloud-native.conf <<'EOF'
* soft nofile 1048576
* hard nofile 1048576
* soft nproc 65535
* hard nproc 65535
root soft nofile 1048576
root hard nofile 1048576
EOF

# ---------- 10. Firewall ----------
log "Configuring nftables"
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    dnf install -y nftables
else
    apt-get install -y nftables
fi

cat > /etc/nftables.conf <<'EOF'
flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iifname "lo" accept
        ct state established,related accept
        icmp type echo-request accept
        tcp dport 22 accept
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
        ct state established,related accept
    }
    chain output {
        type filter hook output priority 0; policy accept;
    }
}
EOF
systemctl enable --now nftables

# ---------- 11. Auditd ----------
log "Installing auditd"
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    dnf install -y auditd
else
    apt-get install -y auditd
fi
systemctl enable --now auditd

# ---------- 12. AIDE ----------
log "Initializing AIDE"
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    dnf install -y aide
else
    apt-get install -y aide
fi
aide --init
mv /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz 2>/dev/null || true

# ---------- 13. Unattended updates ----------
log "Enabling unattended updates"
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    dnf install -y dnf-automatic
    sed -i 's/apply_updates = no/apply_updates = yes/' /etc/dnf/automatic.conf
    systemctl enable --now dnf-automatic.timer
else
    apt-get install -y unattended-upgrades
    dpkg-reconfigure -f noninteractive unattended-upgrades
fi

# ---------- 14. CA bundle ----------
log "Installing internal CA"
if [ -f /mnt/internal-ca/internal-ca.crt ]; then
    cp /mnt/internal-ca/internal-ca.crt /etc/pki/ca-trust/source/anchors/
    update-ca-trust extract 2>/dev/null || update-ca-certificates 2>/dev/null || true
fi

# ---------- 15. Containerd prerequisites ----------
log "Installing containerd prerequisites"
if [ "$OS_ID" = "ol" ] || [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "rocky" ] || [ "$OS_ID" = "alma" ]; then
    dnf install -y containerd conntrack ethtool
else
    apt-get install -y containerd conntrack ethtool
fi

log "OS prep base complete"