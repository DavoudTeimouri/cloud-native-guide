# RHEL-Compatible Family: OS Compatibility Matrix

This section defines OS support for the RHEL-compatible family (Oracle Linux, RHEL, Rocky Linux, AlmaLinux).

## Supported OS Versions

| OS | Version | Architecture | Kernel | Package Manager | Container Runtime | SELinux | CNI | K8s Control Plane | K8s Worker | Offline Repo | Status | Evidence |
|----|---------|-------------|--------|----------------|------------------|---------|-----|-------------------|------------|--------------|--------|----------|
| Oracle Linux | 9 | x86_64 | 5.14+ | DNF/YUM | containerd 2.3.7 | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Yes | Yes | YUM snapshots (repomd.xml) | **Supported** | Kubespray release-2.32 README; `https://yum.oracle.com/` |
| Oracle Linux | 8 | x86_64 | 4.18 | DNF/YUM | containerd | Enforcing | Cilium 1.20.3, Calico 3.31.7 | No | Yes (conditional) | YUM snapshots | **Supported with limitations** | Kernel 4.18 below 4.19 recommendation; Cilium requires >=5.10; OlS is below platform standard OL9 |
| Red Hat Enterprise Linux | 9 | x86_64 | 5.14+ | DNF/YUM | containerd 2.3.7 | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Yes | Yes | YUM snapshots (repomd.xml) | **Supported** | Kubespray release-2.32 README; RHEL 9 OS family support |
| Red Hat Enterprise Linux | 8 | x86_64 | 4.18 | DNF/YUM | containerd | Enforcing | Cilium 1.20.3, Calico 3.31.7 | No | Yes (conditional) | YUM snapshots | **Supported with limitations** | Kernel 4.18 below 4.19 recommendation |
| Rocky Linux | 9 | x86_64 | 5.14+ | DNF/YUM | containerd 2.3.7 | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Yes | Yes | YUM snapshots (repomd.xml) | **Supported** | RHEL-compatible family; same kernel/userspace as RHEL 9 |
| AlmaLinux | 9 | x86_64 | 5.14+ | DNF/YUM | containerd 2.3.7 | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Yes | Yes | YUM snapshots (repomd.xml) | **Supported** | RHEL-compatible family; same kernel/userspace as RHEL 9 |
| Oracle Linux | 10 | x86_64 | 6.x+ | DNF/YUM | containerd | Enforcing | Cilium 1.20.3, Calico 3.31.7 | Conditional | Conditional | YUM snapshots | **Conditional / requires validation** | Not yet tested with Kubespray release-2.32; no pinned version evidence |
| RHEL/Rocky/Alma | 8 | aarch64 | 4.18 | DNF/YUM | containerd | Enforcing | Cilium, Calico | No | No | YUM snapshots | **Not supported** | Kubespray release-2.32 does not validate aarch64; architecture not in offline-staging matrix |

## OS Family Notes

- **Do not infer support merely because two distributions belong to the same family.** Each OS/version row above is verified independently against Kubespray release-2.32 requirements.
- **Oracle Linux 8** kernel 4.18 is below the Kubespray-recommended 4.19 minimum. Cilium requires kernel >= 5.10. OL8 workers can run Calico but Cilium control-plane eligibility is conditional.
- **Offline-staging support** is limited to Oracle Linux 9, Ubuntu 22.04, and Ubuntu 24.04 (RPM/YUM and APT) per the offline-staging implementation (`automation/offline-staging/`). Other RHEL-family OS versions are documented here for general Kubernetes compatibility but are NOT covered by the offline-staging implementation.
- **Python 3.11-3.13** required on the control node for Ansible 2.19.x (Kubespray release-2.32 requirement).
- **SELinux Enforcing** is the platform standard for all RHEL-family OS versions.

## References

- Kubespray release-2.32 README — supported OS list, kernel requirements
- Oracle Linux: `https://yum.oracle.com/`
- RHEL: `https://access.redhat.com/`
- Rocky Linux: `https://rockylinux.org/`
- AlmaLinux: `https://almalinux.org/`
