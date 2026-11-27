# Kubespray Ansible Inventory Design

## 📋 Purpose and Scope

Document Kubespray inventory design: Ansible inventory structure, group variable organization, host variables, inventory templates, variable precedence, and validation procedures for production deployments.

Cross-references `kubespray/kubespray-deployment.md` §Inventory, `kubespray/group-vars-template.md`, `kubespray/inventory-architecture.md`.

---

## 📁 Inventory Directory Structure

```text
kubespray/
├── VERSION                      # pinned Kubespray release tag
├── inventory/
│   ├── sample/                  # vendored copy of the release's sample inventory
│   └── <cluster>/
│       ├── hosts.ini            # host definitions and groups
│       └── group_vars/
│           ├── all/
│           │   ├── main.yml     # all-host variables
│           │   ├── offline.yml  # image + registry overrides
│           │   └── containerd.yml  # registry mirror + TLS config
│           ├── k8s_cluster/
│           │   ├── k8s-cluster.yml     # version, CNI, networking
│           │   └── k8s-cluster-encrypted-images.yml
│           ├── etcd/
│           ├── kube_node/
│           └── k8s_secrets/
│       └── group_vars/all/external.yml
└── patches/                     # site-specific variable overrides
```

---

## 🏗️ hosts.ini Structure

### Core Layout

```ini
[all:vars]
ansible_user=ansible
ansible_become=yes
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'

# ---------------------------------------------------------------------------
# Control plane (3 nodes, stacked etcd)
# ---------------------------------------------------------------------------
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11 ip=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12 ip=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13 ip=10.20.0.13

[etcd]
k8s-cp-1
k8s-cp-2
k8s-cp-3

# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------
[k8s-node]
k8s-w-1 ansible_host=10.20.0.21 ip=10.20.0.21
k8s-w-2 ansible_host=10.20.0.22 ip=10.20.0.22
k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23

# GPU pool: a separate group so labels and taints can differ
[k8s-node:children]
gpu-node

[gpu-node]
k8s-gpu-1 ansible_host=10.50.0.11 ip=10.50.0.11 labels='{"accelerator":"nvidia"}'

# Storage pool: dedicated OSD hosts
[k8s-node:children]
storage-node

[storage-node]
k8s-st-1 ansible_host=10.40.0.11 ip=10.40.0.11
k8s-st-2 ansible_host=10.40.0.12 ip=10.40.0.12
k8s-st-3 ansible_host=10.40.0.13 ip=10.40.0.13

# ---------------------------------------------------------------------------
# Groups Kubespray expects
# ---------------------------------------------------------------------------
[kube-master]
control-plane

[kube-node]
control-plane
k8s-node

[calico-node]

[k8s-cluster:children]
control-plane
etcd
k8s-node
```

### Rules

| Rule | Description |
|------|-------------|
| etcd members | Must also be in `control-plane` when etcd is stacked |
| k8s-node | Must contain every worker, including GPU pool |
| No double-listing | Never list a host in two `k8s-node` groups |
| `ip=` | Must be the address on the cluster network, not the management address |

---

## 🗂️ Group Variables Organization

### File Purpose

| File | Purpose |
|------|---------|
| `group_vars/all/main.yml` | Container manager, runtime, subnets, cert-manager |
| `group_vars/all/offline.yml` | Image repo overrides, registry mirrors, `files_repo` |
| `group_vars/all/containerd.yml` | Registry mirror, TLS config |
| `group_vars/k8s_cluster/k8s-cluster.yml` | `kube_version`, CNI, proxy mode, subnets |
| `group_vars/k8s_cluster/k8s-cluster-encrypted-images.yml` | Encrypted image variables |
| `group_vars/etcd/` | etcd version, storage backend |
| `group_vars/kube_node/` | kubelet config, node labels |
| `group_vars/k8s_secrets/` | Encrypted secrets (Vault references) |

### Verification Before Use

1. Confirm variable names exist in the pinned Kubespray release:

```bash
# Example verification
grep -rn "kube_proxy_mode\|k8sServiceHost" roles/kubespray_defaults/defaults/main/ | head
grep -rn "containerd_registries_mirrors" roles/ | head
```

2. Never reuse a group-vars file across a Kubespray release without diffing it against the new release's `inventory/sample`.

3. Variables `registry_host`, `registry_addr`, `registry_user`, `registry_pass`, `files_repo`, `yum_repo`, `ubuntu_repo` come from the environment overlay (`site-<env>`) or from Ansible Vault. They are never committed to Git.

---

## 🖥️ Host Variables

### Per-Host Variables Placement

Host-specific variables go into `host_vars/<hostname>.yml` files, or can be placed inline in `hosts.ini` using the `variable=value` syntax after the hostname.

### Example host_vars file

```yaml
# host_vars/k8s-cp-1.yml
ansible_user: ansible
ansible_become: yes
kube_api_server_ip: 10.20.0.11
kube_api_server_port: 6443
```

### Inline in hosts.ini

```ini
k8s-cp-1 ansible_host=10.20.0.11 ip=10.20.0.11 ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### Variable Precedence (Ansible)

Ansible resolves variables in this order (lowest to highest priority):

1. **Default variables** — in `library/` or module defaults
2. **Group vars** — `group_vars/all/` and `group_vars/<group>/`
3. **Host vars** — `host_vars/<hostname>.yml` and inline in inventory
4. **Play vars** — vars assigned in a play
5. **Play var priority** — `set_fact`, `set_hierarchy`, etc.
6. **Extra vars** — `-e` flag or `vars_prompt`

**Production guideline**: Place production-specific overrides in `patches/` directory, never directly in `group_vars/` that are committed from the base Kubespray release.

---

## 🔄 Variable Precedence Details

### Complete Precedence Chain

```
1.     DEFAULT                                 # module defaults
2.     VARIABLES                               # command-line / -e
3.     PLAY-VARS                               # vars: set_fact, etc.
4.     ROLE-VARS                               # defaults/
5.     INVENTORY-VARS                          # group_vars/ host_vars/
6.     PLAY-VARS-PRIORITY                       # priority: set_fact
7.     FACTS                                    # gathered by setup
8.     ROLEx-DEFAULT                          # role defaults
9.     ROLEx-VARS                             # role vars/
10. SITE-DEFINED VARIABLES                   # site.yml, etc.
```

### Production Deployment Guidelines

| Situation | Recommended Location |
|-----------|---------------------|
| Cluster-wide defaults (CNI, version) | `group_vars/k8s_cluster/k8s-cluster.yml` |
| All hosts (container manager, subnets) | `group_vars/all/main.yml` |
| Per-node overrides (labels, taints) | `group_vars/kube_node/` or `host_vars/` |
| Secrets (certs, keys) | `group_vars/k8s_secrets/` with Vault references |
| Site-specific overrides (registry, storage) | `patches/site-<env>.yml` |
| Release-specific adjustments | Diff against `inventory/sample/` |

**Never** commit variables that change between Kubespray releases without verifying compatibility.

---

## ✅ Validation Procedures for Production Deployments

### 1. Syntax Check

```bash
# From the repo root
ansible -i kubespray/inventory/<cluster>/hosts.ini all -m ping
ansible-playbook -i kubespray/inventory/<cluster>/hosts.ini cluster.yml --syntax-check
```

### 2. Inventory Link Validation

Run the repository's link checker:

```bash
python3 scripts/check_links.py
```

This validates:
- Relative markdown file references
- In-page anchors point to existing headings
- No broken links in documentation

### 3. Cluster Compatibility Verification

```bash
# Check pinned Kubespray release matches group vars
grep "kube_version:" kubespray/inventory/<cluster>/group_vars/all/main.yml

# Verify variable names against release
grep -rn "kube_proxy_mode\|k8sServiceHost" roles/kubespray_defaults/defaults/main/ | head
```

### 4. Production Checklist

- [ ] All hosts have `ansible_host` and `ip` set to cluster-network addresses
- [ ] etcd members are also in `control-plane` (when stacked)
- [ ] Every worker (including GPU/storage) is in `k8s-node` group
- [ ] No host appears in two `k8s-node` groups
- [ ] `ip=` uses cluster network address, not management address
- [ ] Group vars verified against pinned Kubespray release
- [ ] No uncommitted Vault secrets or registry credentials
- [ ] Syntax check passes without errors
- [ ] `check_links.py` reports 0 broken links

---

## 🔄 Cross-References

- `kubespray/kubespray-deployment.md` §Inventory
- `kubespray/kubespray-deployment.md` §E — Group vars
- `kubespray/group-vars-template.md` — Authoritative group vars template
- `kubespray/inventory-architecture.md` — Inventory architecture overview
- `kubespray/multi-version-support.md` — Release directory structure
- `compatibility/version-matrix.md` — Supported version ranges per release

---

## 📝 Revision History

| Date | Change |
|------|--------|
| 2026-11-26 | Initial creation — Kubespray Ansible inventory design documentation |