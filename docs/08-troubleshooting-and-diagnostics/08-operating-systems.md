# 08 · Operating systems

## Symptoms
- Node not reachable via SSH
- Package install fails
- Service not starting
- Clock skew > 100 ms
- Kernel module missing (overlay, br_netfilter, ip_vs, nf_conntrack)

## Possible causes
- SSH service not running or blocked by firewall
- Internal repository unreachable
- systemd unit failed or masked
- chrony not synchronized
- Kernel module not loaded

## Diagnostic commands
```bash
# SSH connectivity
ssh <user>@<node> 'hostname; uptime'

# Service status
systemctl status <unit>
journalctl -u <unit> -n 50 --no-pager

# Clock
chronyc tracking
timedatectl

# Kernel modules
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'

# Repository
dnf repolist   # OL/RHEL/Rocky/Alma
apt-cache policy  # Ubuntu
```

## Expected output
- SSH: shell prompt returned
- systemctl: Active: active (running)
- chronyc: LEAP status normal, last offset small
- lsmod: modules listed
- repolist: enabled repos with package counts

## Investigation procedure
1. Verify SSH reachability; check firewall port 22
2. Check systemd unit status and logs
3. Verify chrony synchronization; check NTP server reachability
4. Verify kernel modules loaded; load missing via modprobe
5. Verify repository connectivity; check internal mirror URL

## Resolution
- Start/enable failed systemd unit
- Resynchronize chrony; verify NTP server
- Load missing kernel modules; persist via /etc/modules-load.d
- Fix repository configuration; verify internal mirror reachability

## Verification
- SSH succeeds; unit Active: active; chrony synchronized; modules loaded; repolist shows enabled repos

## Prevention
- Automate OS baseline via Ansible; idempotent runs
- Monitor chrony offset; alert on skew > 100 ms
- Monitor repository sync status

## Related
- [02 · Operating Systems and Infrastructure Preparation (2.5 OS Preparation by Role)](../02-components/2.5-os-prep-by-role.md)
