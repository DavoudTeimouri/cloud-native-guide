# Ansible Troubleshooting

## Symptoms

- `ansible-playbook` fails with "unreachable" on targets
- Module not found or "No module named ansible"
- Playbook fails with syntax error
- Variable not defined error
- Permission denied on remote hosts

## Likely causes

- SSH key not deployed to target hosts
- Wrong inventory path or host groups
- Ansible version mismatch with Kubespray release
- Python not installed on target hosts
- Sudo/become not configured correctly

## Diagnostic commands

```bash
# Test connectivity
ansible -i inventory/<cluster>/hosts.ini all -m ping

# Check Ansible version
ansible --version

# Check Python on targets
ansible -i inventory/<cluster>/hosts.ini all -m raw -a "python3 --version"

# Debug variables
ansible -i inventory/<cluster>/hosts.ini <host> -m debug -a "var=ansible_host"

# Check become/sudo
ansible -i inventory/<cluster>/hosts.ini all -m raw -a "whoami" --become
```

## Expected healthy state

- All hosts respond to `ansible -m ping` with "pong"
- Ansible version matches Kubespray release requirements (>=2.19.0, <2.20.0)
- Python 3.11-3.13 installed on all targets
- `ansible --become` shows root on targets
- Inventory variables resolve correctly

## Remediation

- Deploy SSH keys to target hosts
- Fix inventory file (hosts, groups, variables)
- Install correct Ansible version in virtualenv per Kubespray release
- Install Python 3 on target hosts
- Configure passwordless sudo for Ansible user

## Risks

- Wrong inventory can cause changes to wrong hosts
- Running playbooks without `--check` can make unintended changes
- Mixing Ansible versions across Kubespray releases causes unpredictable failures

## Verification

```bash
ansible -i inventory/<cluster>/hosts.ini all -m ping
ansible-playbook -i inventory/<cluster>/hosts.ini site.yml --check --diff
ansible --version | head -3```
