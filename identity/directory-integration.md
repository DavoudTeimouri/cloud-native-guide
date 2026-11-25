# Identity: SSSD/realmd AD Integration

> **Status**: Optional host-level integration — *not the standard platform path*. The standard identity model uses Keycloak as the OIDC broker for all platform services (Rancher, Argo CD, Harbor, GitLab, Vault). This document describes the SSSD/realmd path for use cases where a dedicated ADR approves direct host joining.

## Overview

Linux hosts *can* join the Active Directory domain using `realmd` and `sssd` when specifically authorized by an architecture decision. This provides:
- Kerberos authentication for local users
- Group policy application
- Centralized identity management at the host level

**Standard platform path**: Applications and platform services authenticate via Keycloak OIDC. Keycloak federates with AD/LDAP for user/group sync. No host joins the directory directly.

## Prerequisites

- Active Directory domain controller reachable
- DNS properly configured (forward and reverse)
- Time synchronization (chrony) with AD DC
- Domain join account with permissions to create computer objects

## Installation

### Oracle Linux 9

```bash
dnf install -y realmd sssd oddjob oddjob-mkhomedir adcli samba-common-tools krb5-workstation
```

### Ubuntu 24.04 LTS

```bash
apt-get update && apt-get install -y realmd sssd sssd-tools libnss-sss libpam-sss adcli krb5-user packagekit
```

## Domain Join

```bash
# Discover the realm
realm discover internal.example.com

# Join the domain
realm join --user=domain-join-account internal.example.com

# Verify
realm list
id user@internal.example.com
```

## SSSD Configuration

```ini
# /etc/sssd/sssd.conf
[sssd]
domains = internal.example.com
config_file_version = 2
services = nss, pam, ssh, autofs

[domain/internal.example.com]
ad_domain = internal.example.com
krb5_realm = INTERNAL.EXAMPLE.COM
realmd_tags = manages-system joined-with-adcli
cache_credentials = True
id_provider = ad
krb5_store_password_if_offline = True
default_shell = /bin/bash
ldap_id_mapping = True
use_fully_qualified_names = True
fallback_homedir = /home/%u@%d
access_provider = ad
```

## Kerberos Configuration

```ini
# /etc/krb5.conf
[libdefaults]
default_realm = INTERNAL.EXAMPLE.COM
dns_lookup_realm = true
dns_lookup_kdc = true
ticket_lifetime = 24h
renew_lifetime = 7d
forwardable = true
rdns = false

[realms]
INTERNAL.EXAMPLE.COM = {
    kdc = dc1.internal.example.com
    kdc = dc2.internal.example.com
    admin_server = dc1.internal.example.com
}

[domain_realm]
.internal.example.com = INTERNAL.EXAMPLE.COM
internal.example.com = INTERNAL.EXTERNAL.COM
```

## Verification

```bash
# Test Kerberos
kinit user@INTERNAL.EXAMPLE.COM
klist

# Test SSSD
id user@internal.example.com
getent passwd user@internal.example.com

# Test SSH
ssh user@internal.example.com@localhost
```

## Break-glass Access

Local account with sudo for when AD is unreachable:

```bash
# Create local break-glass user
useradd -m -s /bin/bash breakglass
echo "breakglass:$(openssl rand -base64 32)" | chpasswd
usermod -aG wheel breakglass

# Store credentials offline in Vault
vault kv put secret/breakglass/linux host=hostname user=breakglass password=...
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `realm join` fails | DNS not resolving AD DC | Fix DNS forward/reverse |
| `kinit` fails | Clock skew > 5 min | Sync chrony with AD DC |
| `id user@domain` fails | SSSD not started | `systemctl start sssd` |
| Group membership missing | `ldap_id_mapping = True` missing | Add to sssd.conf |

## References

- [Red Hat SSSD Documentation](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/configuring_authentication_and_authorization_in_rhel/using-sssd)
- [Ubuntu SSSD Wiki](https://wiki.ubuntu.com/SSSD)

---

*Status: DRAFT | Owner: Identity Team | Last reviewed: 2026-11-23*