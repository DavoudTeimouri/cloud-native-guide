# Air-Gapped Upgrade

## Purpose and scope

Upgrade procedures for fully disconnected environments.

## Steps

1. Stage new artifacts on connected staging host
2. Transfer artifacts to air-gapped environment via transfer station
3. Import artifacts to internal Harbor/Nexus/GitLab
4. Upgrade components using internal mirrors only
5. Verify no public internet dependency

## Implementation

```bash
# On connected staging host
skopeo copy docker://<image> dir:/tmp/staging/<image>
helm pull <chart> --version <new-version>
# Transfer /tmp/staging to air-gapped environment via physical media

# On air-gapped environment
skopeo copy dir:/tmp/staging/<image> docker://harbor.internal/<image>
helm upgrade <release> <chart> --version <new-version> -n <namespace>
```

## Validation

- All artifacts available internally
- No public internet access during upgrade
- Components healthy after upgrade

## Related

- [Overview (1.4 Air-Gapped & Disconnected Environments)](../01-overview-and-architecture/1.5-deployment-environments.md)
- [Repository & Registry Management (3.4 Air-Gapped)](../03-repository-registry/3.4-repository-catalog.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)

## Automation: upgrade playbook

Run upgrades via Ansible:

```bash
# Dry-run
ansible-playbook -i automation/ansible/inventories/staging/hosts.ini \
  automation/ansible/playbooks/upgrade.yml --check --diff

# Apply
ansible-playbook -i automation/ansible/inventories/production/hosts.ini \
  automation/ansible/playbooks/upgrade.yml

# Limit to specific component
ansible-playbook -i automation/ansible/inventories/production/hosts.ini \
  automation/ansible/playbooks/upgrade.yml --tag kubernetes
ansible-playbook -i automation/ansible/inventories/production/hosts.ini \
  automation/ansible/playbooks/upgrade.yml --tag ceph
ansible-playbook -i automation/ansible/inventories/production/hosts.ini \
  automation/ansible/playbooks/upgrade.yml --tag gitlab
```

**Upgrade order** (follow section 10-07 compatibility/order):

1. OS firmware/hypervisor (via Terraform + Ansible os-prep)
2. Kubernetes + Kubespray (control plane first, then workers)
3. CNI/CSI/add-ons
4. Ceph/Rook-Ceph
5. Load balancer, GitLab, Nexus, Harbor
6. Monitoring components
7. Air-gapped: import artifacts first, then upgrade from internal mirrors
