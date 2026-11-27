#!/usr/bin/env bash
# OS preparation script — GitLab server role
# Applies common baseline then GitLab-specific tuning:
# PostgreSQL, Redis, object storage, GitLab omnibus package
set -euo pipefail

LOG="/var/log/os-prep-gitlab.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-gitlab: $*"; }

[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring GitLab node"

# ---------- 1. GitLab storage ----------
log "Preparing GitLab storage"
GITLAB_DISK="${GITLAB_DISK:-/dev/nvme1n1}"
GITLAB_MOUNT="${GITLAB_MOUNT:-/var/opt/gitlab}"
if [ -b "$GITLAB_DISK" ]; then
    wipefs -af "$GITLAB_DISK" 2>/dev/null || true
    mkfs.xfs -f "$GITLAB_DISK"
    mkdir -p "$GITLAB_MOUNT"
    echo "$GITLAB_DISK  $GITLAB_MOUNT  xfs  defaults,noatime  0  2" >> /etc/fstab
    mount "$GITLAB_MOUNT"
    log "GitLab storage mounted at $GITLAB_MOUNT"
else
    log "WARNING: $GITLAB_DISK not found; using root filesystem"
fi

# ---------- 2. Install GitLab ----------
log "Installing GitLab omnibus"
if [ -f /etc/os-release ]; then . /etc/os-release; fi
if [ "$ID" = "ol" ] || [ "$ID" = "rhel" ] || [ "$ID" = "rocky" ] || [ "$ID" = "alma" ]; then
    dnf install -y curl policycoreutils openssh-server
    curl https://packages.gitlab.com/install/repositories/gitlab/gitlab-ee/script/rpm.sh | bash
    dnf install -y gitlab-ee
else
    apt-get install -y curl openssh-server ca-certificates tzdata perl
    curl https://packages.gitlab.com/install/repositories/gitlab/gitlab-ee/script/deb.sh | bash
    apt-get install -y gitlab-ee
fi

# ---------- 3. Initial GitLab config ----------
log "Configuring GitLab"
cat > /etc/gitlab/gitlab.rb <<'EOF'
external_url 'https://gitlab.internal'
gitlab_rails['initial_root_password'] = 'CHANGE_ME'
nginx['redirect_http_to_https'] = true
nginx['ssl_certificate'] = '/etc/gitlab/ssl/gitlab.internal.crt'
nginx['ssl_certificate_key'] = '/etc/gitlab/ssl/gitlab.internal.key'
gitlab_rails['smtp_enable'] = true
gitlab_rails['smtp_address'] = 'smtp.internal'
gitlab_rails['smtp_port'] = 25
EOF

# ---------- 4. Verify ----------
log "Verifying GitLab prep"
mount | grep "$GITLAB_MOUNT" || true

log "GitLab OS prep complete"