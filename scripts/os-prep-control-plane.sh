#!/usr/bin/env bash
# OS preparation script — Kubernetes control plane role
# Applies common baseline then control-plane-specific tuning:
# dedicated NVMe for etcd, max_pods, kubelet reserved resources
set -euo pipefail

LOG="/var/log/os-prep-control-plane.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-control-plane: $*"; }

# Require base to be run first
[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring control-plane node"

# ---------- 1. Dedicated NVMe for etcd ----------
log "Preparing etcd storage"
ETCD_DISK="${ETCD_DISK:-/dev/nvme1n1}"
if [ -b "$ETCD_DISK" ]; then
    wipefs -af "$ETCD_DISK" 2>/dev/null || true
    mkfs.xfs -f "$ETCD_DISK"
    mkdir -p /var/lib/etcd
    echo "$ETCD_DISK  /var/lib/etcd  xfs  defaults,noatime  0  2" >> /etc/fstab
    mount /var/lib/etcd
    chown etcd:etcd /var/lib/etcd 2>/dev/null || true
    log "etcd storage mounted at /var/lib/etcd"
else
    log "WARNING: $ETCD_DISK not found; etcd will use root filesystem"
fi

# ---------- 2. kubelet configuration ----------
log "Configuring kubelet"
KUBELET_CONF_DIR="/etc/kubernetes/kubelet"
mkdir -p "$KUBELET_CONF_DIR"

cat > "$KUBELET_CONF_DIR/kubelet-config.yaml" <<'EOF'
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
staticPodPath: /etc/kubernetes/manifests
clusterDNS: 10.96.0.10
clusterDomain: cluster.local
maxPods: 110
readOnlyPort: 10255
authentication:
  anonymous:
    enabled: false
  webhook:
    enabled: true
authorization:
  mode: Webhook
evictionHard:
  memory.available: "500Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
  imagefs.available: "10%"
reservedSystemCPUs: "500m"
reservedSystemMemory: "512Mi"
EOF

# ---------- 3. Kernel tuning for control plane ----------
cat >> /etc/sysctl.d/99-cloud-native.conf <<'EOF'
# Control plane tuning
net.ipv4.tcp_keepalive_time=600
net.ipv4.tcp_keepalive_intvl=30
net.ipv4.tcp_keepalive_probes=10
EOF
sysctl --system

# ---------- 4. Disable swap (ensure) ----------
swapoff -a
sed -i '/[[:space:]]swap[[:space:]]/ s/^/#/' /etc/fstab

# ---------- 5. Verify ----------
log "Verifying control-plane prep"
chronyc tracking
sysctl net.ipv4.ip_forward
lsmod | grep -E 'overlay|br_netfilter'
mount | grep /var/lib/etcd || true

log "Control plane OS prep complete"