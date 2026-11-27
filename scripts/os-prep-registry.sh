#!/usr/bin/env bash
# OS preparation script — Repository/registry manager role (Harbor/Nexus)
# Applies common baseline then registry-specific tuning:
# large disk for image layers, backup, TLS certificates
set -euo pipefail

LOG="/var/log/os-prep-registry.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-registry: $*"; }

[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring repository/registry node"

# ---------- 1. Large disk for image layers ----------
log "Preparing registry storage"
REGISTRY_DISK="${REGISTRY_DISK:-/dev/nvme1n1}"
REGISTRY_MOUNT="${REGISTRY_MOUNT:-/opt/registry}"
if [ -b "$REGISTRY_DISK" ]; then
    wipefs -af "$REGISTRY_DISK" 2>/dev/null || true
    mkfs.xfs -f "$REGISTRY_DISK"
    mkdir -p "$REGISTRY_MOUNT"
    echo "$REGISTRY_DISK  $REGISTRY_MOUNT  xfs  defaults,noatime  0  2" >> /etc/fstab
    mount "$REGISTRY_MOUNT"
    chown -R 10000:10000 "$REGISTRY_MOUNT" 2>/dev/null || true
    log "Registry storage mounted at $REGISTRY_MOUNT"
else
    log "WARNING: $REGISTRY_DISK not found; using root filesystem"
fi

# ---------- 2. Install registry software prerequisites ----------
log "Installing registry prerequisites"
if [ -f /etc/os-release ]; then . /etc/os-release; fi
if [ "$ID" = "ol" ] || [ "$ID" = "rhel" ] || [ "$ID" = "rocky" ] || [ "$ID" = "alma" ]; then
    dnf install -y docker-compose python3
else
    apt-get install -y docker-compose python3
fi

# ---------- 3. TLS certificates ----------
log "Installing TLS certificates"
mkdir -p /etc/registry/certs
if [ -f /mnt/internal-ca/registry.crt ]; then
    cp /mnt/internal-ca/registry.crt /etc/registry/certs/
    cp /mnt/internal-ca/registry.key /etc/registry/certs/
    chmod 600 /etc/registry/certs/registry.key
fi

# ---------- 4. Verify ----------
log "Verifying registry prep"
mount | grep "$REGISTRY_MOUNT" || true

log "Registry OS prep complete"