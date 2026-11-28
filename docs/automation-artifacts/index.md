# Automation Artifacts

## Purpose and scope

Runnable automation artifacts (Ansible playbooks/roles/group_vars, Terraform modules/vars, Python scripts, offline-staging scripts, GitLab CI configs) that implement the guide's deployment and day-2 procedures. Each artifact lists its on-disk path, the variables you customize, and how to run it.

Artifacts are organized by tool:

- [Ansible](ansible.md) — playbooks, roles, group_vars, inventories
- [Terraform](terraform.md) — modules, variables.tf, terraform.tfvars.example
- [Python scripts](python-scripts.md) — link check, catalog validation, offline staging
- [Offline staging](offline-staging.md) — air-gapped artifact sync/import
- [GitLab CI](gitlab-ci.md) — pipeline templates and job definitions

## Customization model

Every artifact is parameterized so you do not edit logic; you edit values:

| Layer | Mechanism | Example |
| --- | --- | --- |
| Ansible group_vars | YAML in `automation/ansible/group_vars/all/<component>.yml` | `ntp_servers`, `internal_registry` |
| Terraform | `terraform.tfvars` copied from `terraform.tfvars.example` | `vm_flavor`, `node_count` |
| Python/offline scripts | CLI flags + JSON manifest + schema | `--manifest`, `--profile` |
| GitLab CI | Variables in `.gitlab-ci.yml` + CI/CD settings | registry URLs, image tags |

## Secrets handling

- Secret values never live in Git.
- Ansible: `group_vars/all/vault.yml` references Vault paths only; actual secrets resolved at runtime via `community.general.hashi_vault` lookup.
- Terraform: `terraform.tfvars.example` has no secrets; real `terraform.tfvars` is gitignored and populated from Vault or an `.env` file.
- Python scripts: read secrets from environment variables or Vault, never from CLI args.

## Running order

The entry point is `automation/ansible/site.yml`, which imports playbooks in dependency order:

1. OS baseline (`playbooks/base.yml`)
2. Container runtime (`playbooks/containerd.yml`)
3. Repositories & registries (`playbooks/repository-registry.yml`)
4. Load balancers (`playbooks/load-balancer.yml`)
5. Kubernetes (`playbooks/kubernetes.yml`)
6. SDS/Ceph (`playbooks/sds-ceph.yml`)
7. Monitoring (`playbooks/monitoring.yml`)
8. GitLab (`playbooks/gitlab.yml`)

Validate before applying:

```bash
ansible-playbook -i automation/ansible/inventories/staging/hosts.ini \
  automation/ansible/site.yml --check --diff
```

## Related

- [Ansible artifacts](ansible.md)
- [Terraform artifacts](terraform.md)
- [Python scripts](python-scripts.md)
- [Offline staging](offline-staging.md)
- [GitLab CI](gitlab-ci.md)
