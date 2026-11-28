# Ansible Artifacts

## Purpose and scope

Ansible playbooks, roles, group_vars, and inventories that prepare OSs, install container runtimes, deploy registries/load balancers/Kubernetes/Ceph/monitoring/GitLab, and run upgrades. All artifacts live under `automation/ansible/`.

## Directory layout

```text
automation/ansible/
├── ansible.cfg                 # Ansible configuration (host_key_checking=False, etc.)
├── requirements.yml            # Ansible collections (pinned versions)
├── requirements.txt            # Python packages for the control node
├── site.yml                    # Single entry point; imports all section playbooks
├── inventories/
│   ├── staging/hosts.ini       # Staging host groups
│   └── production/hosts.ini    # Production host groups
├── group_vars/
│   └── all/
│       ├── main.yml            # Common variables (NTP, DNS, admin user, etc.)
│       ├── offline.yml         # Internal mirrors, air-gapped settings
│       ├── vault.yml           # Vault paths (no secret values)
│       ├── containerd.yml      # Container runtime config
│       ├── kubernetes.yml      # K8s cluster config
│       ├── repository.yml      # Harbor/Nexus/GitLab registry config
│       ├── load-balancer.yml   # HAProxy/NGINX config
│       ├── ceph.yml            # Ceph cluster config
│       ├── monitoring.yml      # Prometheus/Grafana config
│       ├── gitlab.yml          # GitLab config
│       └── velero.yml          # Velero backup config
├── playbooks/
│   ├── base.yml                # OS baseline (all nodes)
│   ├── containerd.yml          # Container runtime
│   ├── repository-registry.yml # Harbor, Nexus, GitLab registry
│   ├── load-balancer.yml       # HAProxy, NGINX
│   ├── kubernetes.yml          # Kubespray cluster
│   ├── sds-ceph.yml            # Ceph SDS
│   ├── monitoring.yml          # Prometheus, Grafana, Alertmanager
│   ├── gitlab.yml              # GitLab server
│   ├── upgrade.yml             # Cluster upgrades
│   ├── os-prep-*.yml           # OS prep by role (base, worker, control-plane, storage, etc.)
│   └── inventory-generation.yml# Dynamic inventory generation
└── roles/
    ├── base/
    ├── containerd/
    ├── kubernetes/
    ├── load-balancer/
    ├── repository-registry/
    ├── ceph/
    ├── monitoring/
    ├── gitlab/
    ├── velero/
    ├── repositories/
    ├── security/
    └── hardening/
```

## Customization points

### 1. group_vars/all/main.yml (common)

Edit these for your environment:

```yaml
ntp_servers:
  - 10.10.0.1
  - 10.10.0.2
dns_servers:
  - 10.10.0.53
dns_search_domain: "internal"
admin_user: ansible
ssh_port: 22
swap: false
selinux: enforcing
firewall_backend: nftables
internal_ca_path: /etc/pki/ca-trust/source/anchors/internal-ca.crt
```

| Variable | What it controls | Customize when |
| --- | --- | --- |
| `ntp_servers` | NTP sources for all nodes | Your internal NTP pool differs |
| `dns_servers` | DNS resolvers | Your internal DNS IPs differ |
| `admin_user` | SSH admin user | You use a different admin name |
| `internal_ca_path` | Path to internal CA cert | Your CA lives elsewhere |

### 2. group_vars/all/offline.yml (air-gapped)

Set internal mirror URLs so nodes never reach public internet:

```yaml
internal_registry: "harbor.internal:5000"
internal_nexus: "https://nexus.internal:8443"
internal_harbor: "https://harbor.internal:443"
air_gapped: true
offline_mirror_root: "/mnt/offline-mirror"
```

### 3. group_vars/all/vault.yml (secrets)

Reference Vault paths only — no secret values:

```yaml
vault_addr: "https://vault.internal:8200"
vault_auth_method: "token"
# Secrets resolved at runtime via lookup('community.general.hashi_vault', ...)
harbor_admin_password_path: "secret/data/harbor/admin-password"
nexus_admin_password_path: "secret/data/nexus/admin-password"
gitlab_root_password_path: "secret/data/gitlab/root-password"
```

### 4. Per-component group_vars

Each component has its own file — edit only the one you deploy:

| File | Controls |
| --- | --- |
| `containerd.yml` | Containerd version, registry mirrors, CNI |
| `kubernetes.yml` | K8s version, Kubespray vars, CNI/CSI choices |
| `repository.yml` | Harbor/Nexus/GitLab versions, storage sizes |
| `load-balancer.yml` | HAProxy/NGINX backends, SSL certs |
| `ceph.yml` | Ceph version, pool sizes, crush rules |
| `monitoring.yml` | Prometheus retention, Alertmanager routes |
| `gitlab.yml` | GitLab version, external URL, SMTP |

## How to run

### Prerequisites

```bash
cd automation/ansible
pip install -r requirements.txt  # control node deps
ansible-galaxy collection install -r requirements.yml
```

### Dry-run (recommended first)

```bash
ansible-playbook -i inventories/staging/hosts.ini site.yml --check --diff
```

### Apply

```bash
ansible-playbook -i inventories/production/hosts.ini site.yml
```

### Run a single section

```bash
ansible-playbook -i inventories/production/hosts.ini playbooks/kubernetes.yml
```

### Limit to specific hosts

```bash
ansible-playbook -i inventories/production/hosts.ini site.yml --limit k8s-workers
```

## Idempotency

All playbooks are idempotent: a second run with no changes reports `changed=0`. Guard every shell/command task with `changed_when` and `creates`/`removes`.

## Related

- [Automation Artifacts overview](index.md)
- [OS prep by role (docs section 02.5)](../02-components/2.5-os-prep-by-role.md)
- [Ansible structure (detailed)](../automation/ansible/ansible-structure.md)
