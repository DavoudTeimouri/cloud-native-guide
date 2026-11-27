# Section 5: Operating System and Container Runtime Lifecycle

*Illustrative only — not production-committed configurations. No live system is upgraded from this document. All examples are version-dependent and labeled as such.*

## 5.1 Supported operating systems

The following OS families and versions are within the documented support matrix (see `lifecycle/version-compatibility-matrix.md`):

| OS family | Supported versions | Package manager | Init system | Notes |
|---|---|---|---|---|
| Oracle Linux | 9 (default), 8 (conditional) | DNF/YUM | systemd | Kernel 4.18 (OL8) below Kubespray 4.19 recommendation |
| Red Hat Enterprise Linux | 9 (default), 8 (conditional) | DNF/YUM | systemd | SELinux enforcing by default |
| Rocky Linux | 9 (default) | DNF/YUM | systemd | |
| AlmaLinux | 9 (default) | DNF/YUM | systemd | |
| Ubuntu Server LTS | 24.04 (default), 22.04 | APT | systemd | AppArmor by default |
| Debian | 12 (supported), 13 (conditional) | APT | systemd | Debian 13 conditional/unvalidated |

Architecture: x86_64 supported; aarch64 not supported for RHEL/Debian family per pinned Kubespray release (see `compatibility/version-matrix.md`).

## 5.2 Update type definitions

| Update type | Meaning | Reversibility | Typical downtime |
|---|---|---|---|
| OS package update | `dnf upgrade` / `apt upgrade` within same release | Forward-only (packages, not OS release) | Minimal (service restart) |
| Kernel update | Install new kernel package, keep running kernel | Forward-only | Reboot required to activate |
| Kernel replacement | Swap kernel flavor/version (e.g., OL UEK → RHCK) | Forward-only | Reboot required |
| OS minor release upgrade | OL8 → OL8.x point release, Ubuntu 22.04 → 22.04.x | Generally forward-only | Minimal to moderate |
| OS major release migration | OL8 → OL9, Ubuntu 22.04 → 24.04 | Not generally supported in-place; reinstall preferred | High (rebuild node) |

## 5.3 Containerd lifecycle

Containerd is the pinned container runtime for Kubespray release-2.32. Version constraints:

| Item | Version | Notes |
|---|---|---|
| containerd (OL/RHEL) | pinned per `version-compatibility-matrix.md` | Install via internal DNF/YUM repo |
| containerd (Ubuntu/Debian) | pinned per `version-compatibility-matrix.md` | Install via internal APT repo |
| runc | pinned per `version-compatibility-matrix.md` | OCI runtime shim |

Containerd upgrade considerations:

- Upgrade containerd in lockstep with Kubernetes where the version matrix requires it.
- Restart containerd after upgrade; running containers continue, new containers use new binary.
- CRI socket: `/run/containerd/containerd.sock`.
- Registry mirrors configured in `/etc/containerd/config.toml` must point to internal Harbor (`harbor.internal`) — see TASK 004-P11.2.

## 5.4 Package repository and offline requirements

- All package updates must come from the internal repository (Nexus), not public DNF/APT mirrors — see TASK 004-P11.2 two-tier architecture.
- Offline/restricted-network upgrades require pre-staged RPM/DEB packages and repository metadata snapshots on the internal repo.
- Do not expand the supported OS matrix just because documentation covers additional versions; offline-staging remains limited to OL9, Ubuntu 22.04, Ubuntu 24.04.

## 5.5 Kernel modules, sysctl, SELinux/AppArmor, firewall

Kernel modules and sysctl settings must be re-verified after a kernel update:

- `br_netfilter`, `overlay`, `nf_conntrack` for Kubernetes networking.
- `net.ipv4.ip_forward=1`, `net.bridge.bridge-nf-call-iptables=1`.

SELinux (RHEL family):

- Enforcing by default on RHEL/Rocky/Alma/OL9.
- containerd and kubelet require appropriate SELinux labels; do not set SELinux to permissive as an upgrade workaround.
- Verify SELinux booleans and file contexts after kernel/package updates.

AppArmor (Debian family):

- Enforcing by default on Ubuntu/Debian.
- containerd/kubelet AppArmor profiles must be reloaded after runtime upgrade.

Firewall:

- RHEL family: firewalld (default) vs nftables — do not mix; family-specific warnings apply (see `operating-systems/rhel-family-procedures.md`).
- Debian family: nftables/iptables considerations (see `operating-systems/debian-family-procedures.md`).

## 5.6 Reboot planning and worker maintenance

Kernel updates and containerd upgrades typically require a node reboot or containerd restart:

1. Drain the worker: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --force`.
2. Apply package/kernel updates.
3. Reboot if kernel was updated.
4. Uncordon: `kubectl uncordon <node>`.
5. Verify: `kubectl get node <node>` → `Ready`; confirm pods rescheduled.

PDBs must allow the evacuation; verify `kubectl get pdb` before draining.

## 5.7 Distribution-specific commands (illustrative, placeholders labeled)

RHEL family (DNF):

```bash
# Illustrative — replace <version> with pinned value from version-compatibility-matrix.md
dnf install -y containerd-<version>
systemctl restart containerd
dnf versionlock add containerd
```

Debian family (APT):

```bash
# Illustrative — replace <version> with pinned value
apt-get install -y containerd=<version>
systemctl restart containerd
apt-mark hold containerd
```

## 5.8 Limitations

- No OS major release migration is supported in-place; rebuild nodes for major version changes.
- Debian 13 is conditional/unvalidated; do not use in production upgrade paths.
- OL8/RHEL8 kernel 4.18 is below the Kubespray 4.19 recommendation; validate Cilium kernel requirements before upgrade.
- Kernel replacement (e.g., UEK flavor change) is not a routine upgrade; specialist review required.

---

*SND 004-P11.6 — OS and Container Runtime Lifecycle (illustrative)*
