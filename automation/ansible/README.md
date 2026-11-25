# Ansible Automation for Cloud-Native Stack

This directory contains the Ansible project for preparing and configuring Linux hosts for the Cloud-Native Stack platform.

## Project Structure

```
automation/ansible/
├── ansible.cfg                 # Ansible configuration
├── requirements.yml            # Ansible collections (pinned versions)
├── requirements.txt            # Python dependencies (pinned versions)
├── site.yml                    # Main entry point
├── inventories/
│   ├── staging/hosts.ini       # Staging inventory (example addresses)
│   └── production/hosts.ini    # Production inventory (placeholders)
├── group_vars/
│   ├── all/
│   │   ├── main.yml            # Global variables
│   │   ├── offline.yml         # Internal registry/repository settings
│   │   └── vault.yml           # Vault integration config (no secrets)
│   └── <cluster>/
│       └── main.yml            # Cluster-specific variables
├── host_vars/                  # Host-specific variables
├── roles/
│   ├── base/                   # OS baseline, packages, users, SSH, hostname
│   ├── repositories/           # Internal package repository configuration
│   ├── security/               # Hardening: sysctl, SSH, firewall, audit, SELinux/AppArmor
│   ├── monitoring/             # Node exporter, Fluent Bit, DCGM (GPU)
│   ├── containerd/             # Container runtime and registry config
│   ├── kubernetes/             # Kubespray wrapper
│   ├── ceph/                   # Ceph storage nodes (cephadm)
│   ├── gpu/                    # GPU driver, labels, taints
│   ├── vault/                  # Vault server nodes
│   └── vm/                     # VM post-provisioning configuration
├── playbooks/
│   ├── base.yml                # Full OS baseline
│   ├── repositories.yml        # Internal repositories only
│   ├── security.yml            # Security hardening only
│   ├── time-sync.yml           # Time synchronization only
│   ├── monitoring.yml          # Monitoring agents only
│   ├── containerd.yml          # Container runtime only
│   └── kubernetes.yml          # Kubespray wrapper
├── library/                    # Custom modules (if needed)
└── filter_plugins/             # Custom filters (if needed)
```

## Quick Start

### Prerequisites

- Ansible control node with Python 3.11-3.13
- ansible-core 2.19.x (matching Kubespray release-2.32)
- SSH access to target hosts with key-based authentication
- `ansible` user with passwordless sudo on all targets
- Internal package repositories (Nexus) and container registry (Harbor) available

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Ansible collections
ansible-galaxy collection install -r requirements.yml

# Verify installation
ansible --version
ansible-playbook --version
```

### Inventory Setup

1. Copy the staging inventory as a template:
   ```bash
   cp inventories/staging/hosts.ini inventories/production/hosts.ini
   ```

2. Edit `inventories/production/hosts.ini` with your actual hostnames and IPs.

3. Configure group variables in `group_vars/all/`:
   - `main.yml`: Global settings (NTP, DNS, registry URLs)
   - `offline.yml`: Internal mirror URLs (replace `nexus.internal`, `harbor.internal`)
   - `vault.yml`: Vault connection (no secrets stored here)

### Execution

```bash
# Syntax check
ansible-playbook -i inventories/production/hosts.ini site.yml --syntax-check

# Lint
ansible-lint playbooks/ roles/

# Dry-run (check mode)
ansible-playbook -i inventories/production/hosts.ini site.yml --check --diff

# Full OS preparation
ansible-playbook -i inventories/production/hosts.ini site.yml

# Targeted runs
ansible-playbook -i inventories/production/hosts.ini playbooks/base.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/security.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/containerd.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/kubernetes.yml

# Limit to specific host group
ansible-playbook -i inventories/production/hosts.ini site.yml --limit control-plane
```

## Supported Operating Systems

| OS | Version | Kernel | Status |
|---|---|---|---|
| Oracle Linux | 9 | 5.14 | Preferred |
| Ubuntu Server | 24.04 LTS | 6.6 | Preferred |
| Ubuntu Server | 22.04 LTS | 5.15 | Supported |
| RHEL / Rocky / Alma | 9 | 5.14 | Supported |

## Key Features

### Offline/Restricted Network Support
- All package managers (DNF/APT) configured to use internal Nexus mirrors
- Containerd configured with Harbor registry mirrors
- No public internet access required
- GPG keys and CA certificates from internal sources

### Idempotency
- All roles use Ansible modules (not shell commands) where possible
- Tasks guarded with `changed_when` and `creates`/`removes` for file operations
- Second run reports 0 changed

### Safety
- `host_key_checking = True` in ansible.cfg (protects against host key spoofing)
- No credentials in inventory or group_vars (secrets from Vault at runtime)
- `no_log: true` on tasks handling secrets
- No automatic reboot (reports requirement, leaves execution under operator control)
- Firewall default-deny with explicit allow rules

### Validation
- Post-run verification tasks included in each playbook
- `ansible all -m setup` idempotency check
- Service health checks (chronyd, node_exporter, fluent-bit, containerd)

## Identity Boundary

**SSSD/realmd host joining is NOT included in the default OS preparation path.**

Per ADR-0015 and the catalog `idpIntegration` definition, the standard platform identity model uses Keycloak as the central OIDC broker for application-layer identity federation. Host-level directory integration requires a separate accepted ADR.

Local break-glass access and secure administrative access are preserved by the base role.

## Documentation

- [OS Preparation Guide (English)](../../docs/en/os-preparation.md)
- [OS Preparation Guide (Persian)](../../docs/fa/os-preparation.md)
- [Inventory Usage Guide](../../inventories/README.md)
- [Platform Standards](../../requirements/platform-standards.md)
- [Version & Compatibility Matrix](../../compatibility/version-matrix.md)

## Testing

```bash
# Syntax check
ansible-playbook -i inventories/staging/hosts.ini site.yml --syntax-check

# Lint
ansible-lint playbooks/ roles/

# Idempotency check (in staging)
ansible-playbook -i inventories/staging/hosts.ini site.yml --check --diff

# Post-run verification
ansible all -i inventories/staging/hosts.ini -m setup
```

## AWX Integration

AWX consumes the same roles and inventories. Job templates map to the playbooks, with tags limiting the scope. Survey variables carry the environment-specific values.

## Version Compatibility

| Component | Version |
|---|---|
| ansible-core | 2.19.2 |
| ansible-lint | 25.1.0 |
| Python | 3.11-3.13 |
| Kubespray | release-2.32 (K8s 1.36.5) |

## License

See repository LICENSE.