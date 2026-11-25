# Common Errors and Troubleshooting

Common issues encountered during OS preparation and how to resolve them.

## Package Installation Failures

### Symptom

DNF/APT fails to install packages from internal repository.

### Diagnosis

```bash
# Verify internal repository access
curl -f https://nexus.internal/repository/ol9-baseos/
curl -f https://nexus.internal/repository/ubuntu-main/
```

### Fix

- Check internal Nexus is reachable
- Verify repository configuration in `/etc/yum.repos.d/internal.repo` or `/etc/apt/sources.list.d/nexus.list`
- Verify GPG keys are imported correctly

## SSH Connection Issues

### Symptom

Ansible cannot connect to target hosts.

### Diagnosis

```bash
# Test SSH connectivity
ansible all -i inventories/production/hosts.ini -m ping

# Verify host keys
ssh-keyscan target-host >> ~/.ssh/known_hosts
```

### Fix

- Ensure SSH server is running on port 22
- Ensure `ansible` user has passwordless sudo
- Verify SSH key-based authentication is configured

## Time Sync Failures

### Symptom

chronyd fails to synchronize time.

### Diagnosis

```bash
# Check chrony status
chronyc tracking
chronyc sources -v
```

### Fix

- Verify internal NTP servers (10.10.0.1, 10.10.0.2) are reachable
- Check chrony configuration in `/etc/chrony.conf`
- Ensure chronyd service is enabled and started

## Containerd Issues

### Symptom

containerd service fails or CRI endpoint unreachable.

### Diagnosis

```bash
# Verify containerd config
containerd --config /etc/containerd/config.toml --validate

# Check service status
systemctl is-active containerd

# Check CRI endpoint
crictl info
```

### Fix

- Verify containerd configuration in `/etc/containerd/config.toml`
- Check registry mirrors point to internal Harbor
- Verify containerd.io package version is 2.3.7 (Kubespray release-2.32 pinned)
- Check service logs: `journalctl -u containerd`

## Firewall Issues

### Symptom

Kubernetes ports unreachable between nodes.

### Diagnosis

```bash
# nftables (Debian family)
nft list ruleset

# firewalld (RHEL family)
firewall-cmd --list-all
```

### Fix

- Verify required ports are open: 6443, 10250, 8472/UDP, 6081/UDP, 30000-32767
- Ensure SSH port 22 is allowed (no lockout)
- Verify firewall service is active

## Kernel Module Issues

### Symptom

Required kernel modules not loaded.

### Diagnosis

```bash
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'
```

### Fix

- Load modules with `modprobe`
- Persist in `/etc/modules-load.d/k8s.conf`
- Reboot if modules fail to load after configuration

## Swap Issues

### Symptom

Swap detected on Kubernetes node.

### Diagnosis

```bash
swapon --show
```

### Fix

- Set `k8s_swap_policy: "managed"` in group_vars
- Set `k8s_swap_confirm_disable: true` for temporary swapoff
- Or set `k8s_swap_policy: "preserve"` to keep existing swap (documented deviation)

## Reboot Required

### Symptom

Playbook reports `REBOOT REQUIRED`.

### Fix

```bash
# Manual reboot when ready
ansible all -i inventories/production/hosts.ini -m reboot
```

- Do not automatically reboot (operator control required)
- Re-run playbook after reboot to clear the flag

## References

- [OS Preparation Guide](os-preparation.md)
- [Validation Commands](validation-commands.md)

---\n*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*
