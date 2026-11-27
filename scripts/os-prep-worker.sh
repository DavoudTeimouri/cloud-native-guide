#!/usr/bin/env bash
# OS preparation script — Kubernetes worker role (Linux)
# Applies common baseline then worker-specific tuning:
# container runtime, kubelet, node labels/taints, GPU drivers (optional)
set -euo pipefail

LOG="/var/log/os-prep-worker.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-worker: $*"; }

[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring worker node"

# ---------- 1. Containerd configuration ----------
log "Configuring containerd"
cat > /etc/containerd/config.toml <<'EOF'
version = 2
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
  options = { SystemdCgroup = true }
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://harbor.internal:5000"]
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.internal:5000"]
  endpoint = ["https://harbor.internal:5000"]
EOF

systemctl enable --now containerd
crictl config --set runtime-endpoint=unix:///run/containerd/containerd.sock

# ---------- 2. kubelet ----------
log "Installing kubelet"
# kubelet installed via Kubespray; ensure prerequisites present
command -v kubelet || log "kubelet will be installed by Kubespray"

# ---------- 3. Node labels and taints (applied at join time) ----------
log "Worker node labels/taints applied at cluster join"

# ---------- 4. GPU support (optional) ----------
if lspci | grep -qi nvidia; then
    log "NVIDIA GPU detected; installing GPU drivers"
    if [ -f /etc/os-release ]; then . /etc/os-release; fi
    if [ "$ID" = "ol" ] || [ "$ID" = "rhel" ] || [ "$ID" = "rocky" ] || [ "$ID" = "alma" ]; then
        dnf install -y nvidia-driver-latest-dkms nvidia-container-toolkit
    else
        apt-get install -y nvidia-driver-535 nvidia-container-toolkit
    fi
    systemctl restart nvidia-persistenced 2>/dev/null || true
fi

# ---------- 5. Verify ----------
log "Verifying worker prep"
systemctl is-active containerd
swapoff --show
cat /sys/kernel/mm/transparent_hugepage/enabled

log "Worker OS prep complete"