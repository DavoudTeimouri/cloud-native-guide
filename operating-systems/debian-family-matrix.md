# Debian Family: OS Compatibility Matrix

This section defines OS support for the Debian family (Ubuntu LTS, Debian stable).

## Supported OS Versions

| OS | Version | Architecture | Kernel | Package Manager | Container Runtime | AppArmor | CNI | K8s Control Plane | K8s Worker | Offline Repo | Status | Evidence |
|----|---------|-------------|--------|----------------|------------------|----------|-----|-------------------|------------|--------------|--------|----------|
| Ubuntu Server | 24.04 LTS | x86_64 | 6.6 | APT | containerd 2.3.7 | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Yes | Yes | APT snapshots (Release/Packages) | **Supported** | Kubespray release-2.32 README; `https://releases.ubuntu.com/` |
| Ubuntu Server | 22.04 LTS | x86_64 | 5.15 | APT | containerd 2.3.7 | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Yes | Yes | APT snapshots (Release/Packages) | **Supported** | Kubespray release-2.32 README; `https://releases.ubuntu.com/` |
| Ubuntu Server | 20.04 LTS | x86_64 | 5.4 | APT | containerd | Enforcing | Cilium 1.20.3, Calico 3.31.7 | No | Conditional | APT snapshots | **Supported with limitations** | Kernel 5.4 below 4.19 requirement is met but below 5.10 Cilium minimum; Ubuntu 20.04 EOL May 2025; not in offline-staging matrix |
| Debian | 12 (bookworm) | x86_64 | 6.1 | APT | containerd | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Conditional | Conditional | APT snapshots | **Conditional / requires validation — not tested with Kubespray release-2.32 offline-staging; general Kubespray compatibility possible** | Not tested with Kubespray release-2.32 offline-staging; general Kubespray compatibility possible |
| Debian | 11 (bullseye) | x86_64 | 5.10 | APT | containerd | Enforcing | Cilium 1.20.3, Calico 3.31.7 | No | Conditional | APT snapshots | **Supported with limitations** | Kernel 5.10 meets Cilium minimum but Debian 11 LTS EOL; not in offline-staging matrix |
| Ubuntu Server | 24.04 LTS | aarch64 | 6.6 | APT | containerd | Enforcing | Cilium, Calico | No | No | APT snapshots | **Not supported** | Kubespray release-2.32 does not validate aarch64; architecture not in offline-staging matrix |
| Debian | 10 (buster) | x86_64 | 4.19 | APT | containerd | Enforcing | Cilium, Calico | No | No | APT snapshots | **Not supported** | Kernel 4.19 at floor; Debian 10 EOL; no containerd 2.3.7 packages available |

## OS Family Notes

- **Do not infer support merely because two distributions belong to the same family.** Each OS/version row above is verified independently.
- **Debian 13 is not a stable release.** Any deployment using Debian 13 is unsupported until a stable release is published. Do not infer support from Debian 12 availability.
- **Offline-staging support** is limited to Oracle Linux 9, Ubuntu 22.04, and Ubuntu 24.04 (RPM/YUM and APT) per the offline-staging implementation (`automation/offline-staging/`). Other OS versions are documented here for general Kubernetes compatibility but are NOT covered by the offline-staging implementation.
- **Python 3.11-3.13** required on the control node for Ansible 2.19.x (Kubespray release-2.32 requirement).
- **AppArmor Enforcing** is the platform standard for all Debian-family OS versions.

## References

- Ubuntu: `https://releases.ubuntu.com/`
- Debian: `https://www.debian.org/`
- Kubespray release-2.32 README — supported OS list, kernel requirements
