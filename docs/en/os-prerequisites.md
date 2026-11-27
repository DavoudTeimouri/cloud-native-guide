# OS Prerequisites

Prerequisites for preparing Linux hosts for the Cloud-Native Stack platform.

## Supported Operating Systems

| OS | Version | Architecture | Kernel | Status |
|----|---------|-------------|--------|--------|
| Oracle Linux | 9 | x86_64 | 5.14+ | Preferred |
| Ubuntu Server | 24.04 LTS | x86_64 | 6.6+ | Preferred |
| Ubuntu Server | 22.04 LTS | x86_64 | 5.15+ | Supported |
| RHEL | 9 | x86_64 | 5.14+ | Supported |
| Rocky Linux | 9 | x86_64 | 5.14+ | Supported |
| AlmaLinux | 9 | x86_64 | 5.14+ | Supported |

## Control Node Prerequisites

- Python 3.11-3.13
- ansible-core >=2.19.0, <2.20.0 (per Kubespray v2.32.0)
- SSH key access to all target hosts
- Access to internal Nexus (`https://nexus.internal`) and Harbor (`https://harbor.internal`)

## Target Host Prerequisites

- SSH server running on port 22
- `ansible` user with passwordless sudo
- Python 3 installed
- Network access to internal Nexus and Harbor

## Kernel Requirements

For Kubernetes >= 1.32:
- Recommended 4.x LTS kernel: 4.19
- Any 5.x or 6.x supported
- cgroups v2 needs >= 4.15 (5.8+ recommended)

### CNI-Specific Kernel Requirements

| CNI | Minimum Kernel |
|-----|---------------|
| Cilium 1.20.3 | 5.10 |
| Calico 3.31.7 | 4.19 |

### Verification

```bash
# Check kernel version
uname -r

# Expected: >= 4.19 (Kubernetes general minimum)
# Cilium: >= 5.10
# Calico: >= 4.19

# Check cgroups version
stat -fc %T /sys/fs/cgroup

# Expected: cgroup2fs
```

## Hardware Prerequisites

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| Memory | 4 GB | 8+ GB |
| Disk | 50 GB | 100+ GB |
| Network | 1 Gbps | 10 Gbps |

## Network Prerequisites

- Static IP address configured
- DNS resolution working
- Internal Nexus and Harbor reachable

## References

- [Version & Compatibility Matrix](../../compatibility/version-matrix.md)
- [OS Preparation Guide](os-preparation.md)

---\n*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*
