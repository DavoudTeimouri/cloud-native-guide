# Repository Configuration

Configure internal package repositories for DNF/YUM (RHEL family) and APT (Debian family).

## DNF/YUM Repositories (RHEL Family)

### Repository File

```ini
# /etc/yum.repos.d/internal.repo
[ol9-baseos]
name=Oracle Linux 9 BaseOS
baseurl=https://nexus.internal/repository/ol9-baseos/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-baseos/RPM-GPG-KEY-oracle

[ol9-appstream]
name=Oracle Linux 9 AppStream
baseurl=https://nexus.internal/repository/ol9-appstream/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-appstream/RPM-GPG-KEY-oracle
```

### Verification

```bash
# List enabled repositories
dnf repolist

# Clean and refresh metadata
dnf clean all
dnf makecache

# Verify GPG keys
rpm -q gpg-pubkey --qf '%{name}-%{version}-%{release}\n' | grep -i oracle
```

## APT Repositories (Debian Family)

### Repository File

#### Ubuntu 24.04 (noble)

```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ noble main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ noble-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ noble-security main restricted universe multiverse
```

#### Ubuntu 22.04 (jammy)

```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ jammy main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ jammy-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ jammy-security main restricted universe multiverse
```

### Verification

```bash
# Update package index
apt-get update

# Verify repository signatures (no errors expected)
apt-get update 2>&1 | grep -iE "error|warning|signature"

# List installed packages
dpkg -l | grep containerd
```

## GPG Key Installation

### RHEL Family

```bash
# Import Oracle Linux GPG key
rpm --import https://nexus.internal/repository/ol9-baseos/RPM-GPG-KEY-oracle
```

### Debian Family

```bash
# Add Nexus GPG key
curl -fsSL https://nexus.internal/repository/gpg-keys/nexus.gpg | apt-key add -
```

## Offline Mode

All repositories point to internal Nexus. Public internet access is not assumed.

```bash
# Verify internal repository access
curl -f https://nexus.internal/repository/ol9-baseos/
curl -f https://nexus.internal/repository/ubuntu-main/
```

## References

- [OS Preparation Guide](os-preparation.md)
- [RHEL Family Matrix](../operating-systems/host-configuration.md)
- [Debian Family Matrix](../operating-systems/host-configuration.md)

---\n*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*
