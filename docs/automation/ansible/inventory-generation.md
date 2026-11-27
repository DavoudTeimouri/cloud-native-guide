# Ansible Inventory Generation

## A. Purpose and scope

Document inventory generation: hosts.ini template, group_vars generation, cluster-specific variables, secrets injection.

Cross-references `kubespray/inventory-architecture.md`, `kubespray/kubespray-deployment.md` §Inventory, `automation/ansible/ansible-structure.md`.

## B. Inventory generation workflow

Inventory is generated from a source of truth (CMDB, Git, or Terraform output), not hand-edited:

```bash
# Generate hosts.ini from Terraform output
terraform output -json k8s_hosts | \
  python3 scripts/generate_hosts_ini.py > inventory/<cluster>/hosts.ini

# Generate group_vars from cluster config
python3 scripts/generate_group_vars.py \
  --cluster <name> \
  --config configs/<name>.yaml \
  --output inventory/<cluster>/group_vars/
```

## C. Hosts.ini template

```ini
[all:vars]
ansible_user={{ ansible_user }}
ansible_become={{ ansible_become | default(true) }}
ansible_python_interpreter={{ ansible_python_interpreter | default('/usr/bin/python3') }}

[control-plane]
{% for host in control_plane %}
{{ host.name }} ansible_host={{ host.ip }} ip={{ host.ip }}
{% endfor %}

[etcd]
{% for host in etcd_nodes %}
{{ host.name }}
{% endfor %}

[k8s-node]
{% for host in worker_nodes %}
{{ host.name }} ansible_host={{ host.ip }} ip={{ host.ip }}
{% endfor %}

[k8s-cluster:children]
control-plane
etcd
k8s-node
```

## D. Group_vars generation

group_vars are generated from templates with cluster-specific overrides:

```yaml
# group_vars/all/main.yml (template)
kube_version: {{ kube_version }}
container_manager: containerd
etcd_deployment_type: stacked
etcd_storage_backend: etcd3

# group_vars/k8s_cluster/k8s-cluster.yml (template)
cluster_name: {{ cluster_name }}
dns_domain: {{ dns_domain }}
networking: {{ networking }}
ipvs: {{ ipvs | default(false) }}
kube_network_prefix: {{ kube_network_prefix }}
```

## E. Secrets injection

Secrets are never stored in generated inventory. Use Vault references:

```yaml
# inventory/<cluster>/group_vars/k8s_secrets/vault.yml (generated)
vault_addr: {{ vault_addr }}
vault_role: {{ vault_role }}
vault_secret_path: secret/cluster/{{ cluster_name }}
```

## F. Cross-references

- `kubespray/inventory-architecture.md` — Inventory architecture
- `kubespray/kubespray-deployment.md` §D — Inventory
- `kubespray/group-vars-template.md` — Authoritative template
- `automation/ansible/ansible-structure.md` — Ansible structure
