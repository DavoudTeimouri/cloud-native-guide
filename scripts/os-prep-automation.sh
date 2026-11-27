#!/usr/bin/env bash
# OS preparation script — Automation server role (Ansible control node)
# Applies common baseline then automation-specific tuning:
# Ansible venv, collections from internal mirror, SSH keys
set -euo pipefail

LOG="/var/log/os-prep-automation.log"
exec > >(tee -a "$LOG") 2>&1

log() { echo "[$(date -Iseconds)] os-prep-automation: $*"; }

[ -f /etc/chrony.conf ] || { echo "Run os-prep-base.sh first"; exit 1; }

log "Configuring automation server"

# ---------- 1. Python 3 and pip ----------
log "Installing Python 3 and pip"
if [ -f /etc/os-release ]; then . /etc/os-release; fi
if [ "$ID" = "ol" ] || [ "$ID" = "rhel" ] || [ "$ID" = "rocky" ] || [ "$ID" = "alma" ]; then
    dnf install -y python3 python3-pip
else
    apt-get install -y python3 python3-pip
fi

# ---------- 2. Ansible virtualenv ----------
log "Creating Ansible virtualenv"
python3 -m venv /opt/ansible/venv
/opt/ansible/venv/bin/pip install --upgrade pip
/opt/ansible/venv/bin/pip install ansible-core==2.19.2 ansible-lint==25.1.0 netaddr jinja2

# Configure pip to use internal index
mkdir -p /opt/ansible/venv/pip.conf
cat > /opt/ansible/venv/pip.conf <<'EOF'
[global]
index-url = http://nexus.internal/repository/pypi/simple
trusted-host = nexus.internal
EOF

# ---------- 3. Ansible collections ----------
log "Installing Ansible collections"
cat > /tmp/requirements.yml <<'EOF'
collections:
  - name: community.general
    version: ">=8.0.0,<10.0.0"
  - name: ansible.posix
    version: ">=1.5.0,<2.0.0"
  - name: kubernetes.core
    version: ">=3.0.0,<5.0.0"
  - name: community.crypto
    version: ">=2.20.0,<3.0.0"
EOF

/opt/ansible/venv/bin/ansible-galaxy collection install -r /tmp/requirements.yml

# ---------- 4. SSH keys for all managed nodes ----------
log "Setting up SSH keys"
install -d -m 700 /home/ansible/.ssh
if [ -f /root/.ssh/id_ed25519 ]; then
    cp /root/.ssh/id_ed25519 /home/ansible/.ssh/
    cp /root/.ssh/id_ed25519.pub /home/ansible/.ssh/
    chmod 600 /home/ansible/.ssh/id_ed25519
    chmod 644 /home/ansible/.ssh/id_ed25519.pub
fi
chown -R ansible:ansible /home/ansible/.ssh

# ---------- 5. known_hosts ----------
log "Pre-populating known_hosts"
ssh-keyscan 10.10.0.101 10.10.0.102 10.10.0.103 10.10.0.201 10.10.0.202 10.10.0.203 >> /home/ansible/.ssh/known_hosts 2>/dev/null || true
chown ansible:ansible /home/ansible/.ssh/known_hosts

# ---------- 6. Verify ----------
log "Verifying automation prep"
/opt/ansible/venv/bin/ansible --version
ls /opt/ansible/venv/bin/ansible-playbook

log "Automation OS prep complete"