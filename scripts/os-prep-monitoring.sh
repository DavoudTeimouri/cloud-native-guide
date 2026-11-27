#!/usr/bin/env bash
# OS preparation script — Monitoring node role
# Applies common baseline then monitoring-specific tuning:
# node_exporter, Fluent Bit, Prometheus scrape targets
set -euo pipefail

LOG="/var/log/os-prep-monitoring.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-monitoring: $*"; }

[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring monitoring node"

# ---------- 1. Monitoring storage ----------
log "Preparing monitoring storage"
MON_DISK="${MON_DISK:-/dev/nvme1n1}"
MON_MOUNT="${MON_MOUNT:-/var/lib/prometheus}"
if [ -b "$MON_DISK" ]; then
    wipefs -af "$MON_DISK" 2>/dev/null || true
    mkfs.xfs -f "$MON_DISK"
    mkdir -p "$MON_MOUNT"
    echo "$MON_DISK  $MON_MOUNT  xfs  defaults,noatime  0  2" >> /etc/fstab
    mount "$MON_MOUNT"
    log "Monitoring storage mounted at $MON_MOUNT"
else
    log "WARNING: $MON_DISK not found; using root filesystem"
fi

# ---------- 2. Install monitoring packages ----------
log "Installing monitoring packages"
if [ -f /etc/os-release ]; then . /etc/os-release; fi
if [ "$ID" = "ol" ] || [ "$ID" = "rhel" ] || [ "$ID" = "rocky" ] || [ "$ID" = "alma" ]; then
    dnf install -y prometheus grafana alertmanager prometheus-node-exporter
else
    apt-get install -y prometheus grafana alertmanager prometheus-node-exporter
fi

# ---------- 3. Configure node_exporter ----------
log "Configuring node_exporter"
systemctl enable --now prometheus-node-exporter

# ---------- 4. Configure Prometheus ----------
log "Configuring Prometheus"
mkdir -p /etc/prometheus
cat > /etc/prometheus/prometheus.yml <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets:
        - 'localhost:9100'
EOF

systemctl enable --now prometheus
systemctl enable --now grafana
systemctl enable --now alertmanager

# ---------- 5. Verify ----------
log "Verifying monitoring prep"
systemctl is-active prometheus-node-exporter
systemctl is-active prometheus
mount | grep "$MON_MOUNT" || true

log "Monitoring OS prep complete"