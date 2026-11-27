# OS Upgrade

### Purpose
Patch OS packages and kernel upgrades.

### Prerequisites
- Node drained (if worker)
- Velero backup of workloads
- Maintenance window scheduled

### Execution
```bash
# Oracle Linux
dnf update -y --security

# Ubuntu
apt-get update && apt-get upgrade -y --security-only

# Reboot if kernel updated
if [ -f /var/run/reboot-required ]; then
  systemctl reboot
fi
```

### Validation
- Node rejoins cluster
- All pods Running
- No alerting
