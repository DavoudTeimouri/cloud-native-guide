#!/usr/bin/env bash
# OS preparation script — Load balancer node role
# Applies common baseline then LB-specific tuning:
# IP forwarding, keepalived, HAProxy/NGINX, VIP health checks
set -euo pipefail

LOG="/var/log/os-prep-lb.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-lb: $*"; }

[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring load balancer node"

# ---------- 1. IP forwarding ----------
log "Enabling IP forwarding"
cat > /etc/sysctl.d/99-lb.conf <<'EOF'
net.ipv4.ip_forward=1
net.ipv4.ip_nonlocal_bind=1
EOF
sysctl --system

# ---------- 2. Install HAProxy ----------
log "Installing HAProxy"
if [ -f /etc/os-release ]; then . /etc/os-release; fi
if [ "$ID" = "ol" ] || [ "$ID" = "rhel" ] || [ "$ID" = "rocky" ] || [ "$ID" = "alma" ]; then
    dnf install -y haproxy keepalived
else
    apt-get install -y haproxy keepalived
fi

# ---------- 3. Basic HAProxy config ----------
log "Configuring HAProxy"
cat > /etc/haproxy/haproxy.cfg <<'EOF'
global
    log /dev/log local0
    maxconn 2000
    user haproxy
    group haproxy
    daemon

defaults
    log global
    mode tcp
    retries 3
    timeout connect 5000
    timeout client 50000
    timeout server 50000

frontend kubernetes-api
    bind *:6443
    default_backend kubernetes-api

backend kubernetes-api
    balance roundrobin
    option tcp-check
    # Server entries added by Kubespray/Ansible

frontend k8s-ingress
    bind *:80
    bind *:443
    default_backend k8s-ingress

backend k8s-ingress
    balance roundrobin
    option tcp-check
    # Server entries added by Kubespray/Ansible
EOF

systemctl enable --now haproxy

# ---------- 4. Keepalived ----------
log "Configuring Keepalived"
cat > /etc/keepalived/keepalived.conf <<'EOF'
vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    virtual_ipaddress {
        10.10.0.10
    }
    track_script {
        chk_haproxy
    }
}

vrrp_script chk_haproxy {
    script "killall -0 haproxy"
    interval 2
    weight 2
}
EOF

systemctl enable --now keepalived

# ---------- 5. Verify ----------
log "Verifying LB prep"
systemctl is-active haproxy
systemctl is-active keepalived
sysctl net.ipv4.ip_forward

log "Load balancer OS prep complete"