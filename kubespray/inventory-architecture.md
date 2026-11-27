# Kubespray Inventory Architecture

## A. Purpose and scope

Document Kubespray inventory architecture: hosts.ini structure, group_vars organization, cluster-specific variables, secrets injection.

Cross-references `kubespray/kubespray-deployment.md` §Inventory, `kubespray/group-vars-template.md`, `kubespray/multi-version-support.md`.

## B. Inventory directory structure

```
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

## C. hosts.ini structure

```ini
[all:vars]
ansible_user=ansible
ansible_become=yes
ansible_python_interpreter=/usr/bin/python3

[control-plane]
k8s-cp-1 ansible_host=10.20.0.11 ip=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12 ip=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13 ip=10.20.0.13

[etcd]
k8s-cp-1
k8s-cp-2
k8s-cp-3

[k8s-node]
k8s-w-1 ansible_host=10.20.0.21 ip=10.20.0.21
k8s-w-2 ansible_host=10.20.0.22 ip=10.20.0.22

[k8s-node:children]
gpu-node

[gpu-node]
k8s-gpu-1 ansible_host=10.50.0.11 ip=10.50.0.11 labels='{"accelerator":"nvidia"}'

[k8s-cluster:children]
control-plane
etcd
k8s-node

[kube-node]
control-plane
k8s-node
```

## D. Group membership rules

| Rule | Description |
|------|-------------|
| etcd members | Must also be in control-plane when etcd is stacked |
| k8s-node | Must contain every worker, including GPU pool |
| No double-listing | Never list a host in two k8s-node groups |

## E. Group variables organization

| File | Purpose |
|------|---------|
| group_vars/all/main.yml | Container manager, runtime, subnets, cert-manager |
| group_vars/all/offline.yml | Image repo overrides, registry mirrors, files_repo |
| group_vars/all/containerd.yml | Registry mirror, TLS config |
| group_vars/k8s_cluster/k8s-cluster.yml | kube_version, CNI, proxy mode, subnets |
| group_vars/k8s_cluster/k8s-cluster-encrypted-images.yml | Encrypted image variables |
| group_vars/etcd/ | etcd version, storage backend |
| group_vars/kube_node/ | kubelet config, node labels |
| group_vars/k8s_secrets/ | Encrypted secrets (Vault references) |

## F. Cluster-specific variables

Each cluster has its own inventory directory with cluster-specific hosts.ini and group_vars. Variables are never shared between clusters unless intentionally copied.

## G. Secrets injection

Secrets are not stored in plain text in inventory. Use Vault references:

```yaml
# group_vars/k8s_secrets/vault.yml
vault_addr: https://vault.internal:8200
vault_role: kubernetes
vault_secret_path: secret/cluster/<name>
```

## H. Cross-references

- `kubespray/kubespray-deployment.md` §D — Inventory
- `kubespray/kubespray-deployment.md` §E — Group vars
- `kubespray/group-vars-template.md` — Authoritative template
- `kubespray/multi-version-support.md` — Release directory structure
