# Terraform — VM provisioning on vSphere and virtualization platforms

Terraform provisions VMs on vSphere and other virtualization platforms; Ansible (see `automation/ansible/`) configures them after provisioning. One tool owns each layer:

| Layer | Tool | Responsibility |
|-------|------|----------------|
| VM create / destroy / resize | Terraform | vSphere provider, VM hardware, network, disk, template clone |
| OS and service config after boot | Ansible | base OS, users, ssh, sudo, repos, runtime, identity |
| Secrets | Vault | looked up at execution time, never in Git |

## Symptom: VM provisioned but not reachable

**Likely cause:** vSphere template has no cloud-init / no customization spec, or the VM network is on the wrong portgroup.

**Fix:** Set `network` and `customization` in the Terraform resource; confirm the template has an IP source (DHCP or static via customization spec).

**Self-check:** `terraform show` lists the VM with the expected `network_interface` and `ip_address`; `ping` the guest from the automation host.

## Symptom: Terraform plan always shows drift

**Likely cause:** A value set in vSphere directly (e.g. vCPU manually changed) diverges from the Terraform state.

**Fix:** Never edit VM settings in vSphere outside Terraform. Re-run `terraform apply` after correcting state, or `terraform import` to adopt an existing VM.

**Self-check:** `terraform plan` reports `No changes. Your infrastructure matches the configuration.`

**Ponytail:** Scope ceiling — VM provisioning lifecycle only. Add VM snapshots, clones from existing VMs (not templates), and VM-to-VM migration when those patterns are used.
