# Terraform — Ansible integration

Terraform provisions the VM; Ansible configures it. Terraform outputs the VM IPs; Ansible reads them as inventory.

## Symptom: Ansible cannot reach the new VM

**Likely cause:** Terraform output not consumed by Ansible inventory, or the guest is not yet booted when Ansible runs.

**Fix:** Generate the Ansible inventory from Terraform output (or from a static hosts file updated by Terraform via `local_exec`/`null_resource`). Wait for SSH readiness before running Ansible.

**Self-check:** `ansible all -m ping` from the automation host reaches every new VM.

## Symptom: Ansible configures a VM that Terraform is still changing

**Likely cause:** Terraform and Ansible run in parallel instead of sequence.

**Fix:** Sequence: `terraform apply` → wait → `ansible-playbook`. Never run both against the same VM concurrently.

**Self-check:** `terraform plan` shows no changes before Ansible runs; Ansible reports 0 changed on a second run.

**Ponytail:** Scope ceiling — sequential provision then configure. Add dynamic inventory plugins (e.g. `community.vmware.vmware_vm_inventory`) and parallel batch provisioning when those patterns are used.
