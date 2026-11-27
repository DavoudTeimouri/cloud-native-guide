# Phase 0 — Operating System Selection Guide

Choose the operating system for every node before deploying any cluster component.
This guide helps you pick the OS that is compatible with Kubespray, Ceph, Rancher,
and all supported add-ons, then apply the host configuration baseline.

## 0.1 Supported Operating Systems

| Aspect | Oracle Linux 9 | Ubuntu Server 24.04 LTS |
|--------|---------------|-------------------------|
| **Package manager** | `dnf` / `yum` | `apt` / `dpkg` |
| **Mandatory access control** | SELinux (enforcing) | AppArmor (enforcing) |
| **Firewall** | `firewalld` | `ufw` or `nftables` (pick one) |
| **Verified kernel** | 5.14 (UEK or RHCK) | 6.6 (generic) |
| **Minimum kernel** | 5.14 recommended | 6.6 recommended |
| **Time sync** | `chronyd` | `chrony` (24.04 defaults to `systemd-timesyncd`) |
| **Certificate trust** | `/etc/pki/ca-trust/...` + `update-ca-trust` | `/usr/local/share/ca-certificates/` + `update-ca-certificates` |
| **Major version upgrade** | `dnf upgrade` + `leapp` | `do-release-upgrade` |
| **Best fit** | KRDO / Ceph integration, Red Hat ecosystem | Broad hardware support, Ubuntu familiarity |

**Minimum kernel requirement:** 4.19 or newer. Both supported OSes meet this.
Oracle Linux 8 (kernel 4.18) is below the recommendation — do not use for new deployments.

## 0.2 Decision Criteria

Choose **Oracle Linux 9** when:
- You run Ceph/Rook-Ceph (KRDO integration is validated on RHEL-family).
- You already standardize on Oracle Linux or RHEL.
- You need `dnf`/`yum` repository mirroring for offline/air-gapped sites.

Choose **Ubuntu Server 24.04 LTS** when:
- Your hardware support is better on Ubuntu (newer NIC/GPU/RAID controllers).
- Your team is more familiar with `apt`/`dpkg` and Debian packaging.
- You already run an Ubuntu estate for application clusters.

## 0.3 Host Prerequisites (All OSes)

Apply these on every node before any cluster component is installed:

| Requirement | Value |
|-------------|-------|
| Swap | Disabled permanently (`swapoff -a`, mask swap units) |
| `vm.max_map_count` | `>= 262144` |
| `fs.file-max` | `>= 1048576` |
| `kernel.pid_max` | `>= 4194304` |
| Kernel modules | `overlay`, `br_netfilter`, `nf_conntrack`, `rbd` |
| Container runtime | containerd 2.x (Kubespray default) |
| Time sync | Internal NTP source, synchronized across all nodes |
| DNS | Internal resolver, forward and reverse records for all node IPs |
| Out-of-band | IPMI / iDRAC / iLO access confirmed on all hosts |

## 0.4 Host Configuration Baseline

See `operating-systems/host-configuration.md` for the shared baseline across all OSes
(identity/access, time/locale, name resolution, kernel/memory, limits, security,
container runtime prerequisites).

Per-OS baselines:
- **Oracle Linux 9:** `operating-systems/oracle-linux/baseline.md` — SELinux, firewalld, DNF repo hardening, break-glass account.
- **Ubuntu 24.04:** `operating-systems/ubuntu/baseline.md` — AppArmor, ufw/nftables, APT repo hardening, `chrony` install, unattended-upgrades disabled.

## 0.5 Hardening Checklist

- [ ] SELinux enforcing (OL9) or AppArmor enforcing (Ubuntu) — never disabled to fix a problem.
- [ ] Firewall active with explicit allow rules + default deny; every open port justified.
- [ ] Auditd retention/rotation configured; logs shipped to centralized immutable storage.
- [ ] Unattended upgrades: security-only with planned reboot window — **no automatic reboots** on Kubernetes nodes.
- [ ] SSH: root login disabled, password auth disabled, public key auth only, restricted cipher suite.
- [ ] Swap disabled persistently (comment/remove from fstab).
- [ ] Transparent Huge Pages: `madvise` for latency workloads, `never` for Ceph OSDs.
- [ ] vm.max_map_count >= 262144.
- [ ] file-max >= 1048576.
- [ ] DNS: internal resolver only; DoT off for internal name resolution.
- [ ] NTP: 2 internal sources + 1 on a different switch; chronyd configured.
- [ ] Certificate trust store updated with internal CA before any TLS component is deployed.

## 0.6 Next Step

After OS selection and host configuration are complete on every node, proceed to
**Phase 1 — Cluster Foundation** (`docs/deploy/choose-cluster-type.md`).
