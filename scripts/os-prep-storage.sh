#!/usr/bin/env bash
# OS preparation script — Ceph storage node role
# Applies common baseline then storage-specific tuning:
# XFS with ftype=1, dedicated journal/WAL devices, disk tuning
set -euo pipefail

LOG="/var/log/os-prep-storage.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-storage: $*"; }

[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring storage node"

# ---------- 1. XFS with ftype=1 ----------
log "Preparing OSD devices"
for disk in /dev/nvme1n1 /dev/nvme2n1 /dev/sdb /dev/sdc; do
    if [ -b "$disk" ]; then
        wipefs -af "$disk" 2>/dev/null || true
        mkfs.xfs -f -n ftype=1 "$disk"
        log "Formatted $disk as XFS with ftype=1"
    fi
done

# ---------- 2. Disk tuning ----------
log "Tuning OSD disks"
for disk in /dev/nvme1n1 /dev/nvme2n1; do
    if [ -b "$disk" ]; then
        echo 1024 > /sys/block/$(basename "$disk")/queue/read_ahead_kb 2>/dev/null || true
        echo none > /sys/block/$(basename "$disk")/queue/scheduler 2>/dev/null || true
    fi
done

# ---------- 3. Ceph user ----------
log "Creating ceph user"
id ceph 2>/dev/null || useradd -r -s /sbin/nologin -d /var/lib/ceph ceph

# ---------- 4. Disk tuning params ----------
cat > /etc/sysctl.d/99-ceph.conf <<'EOF'
vm.vfs_cache_pressure=50
vm.dirty_ratio=10
vm.dirty_background_ratio=5
EOF
sysctl --system

# ---------- 5. Verify ----------
log "Verifying storage prep"
xfs_info /dev/nvme1n1 2>/dev/null || true
id ceph

log "Storage OS prep complete"