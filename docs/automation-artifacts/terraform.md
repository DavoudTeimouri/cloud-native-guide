# Terraform Artifacts

## Purpose and scope

Terraform modules for VM provisioning on vSphere and other virtualization platforms, plus state migration and drift detection. Terraform owns the infrastructure layer (VMs, networks, disks); Ansible owns the OS/config layer after boot. All artifacts live under `automation/terraform/`.

## Directory layout

```text
automation/terraform/
├── main.tf            # VM, network, disk resources (vSphere provider)
├── variables.tf       # Input variable definitions with defaults
├── outputs.tf         # Outputs (new_node_ips, vm_ids) fed to Ansible inventory
├── terraform.tfvars.example  # Copy to terraform.tfvars and adjust
├── virtualization.md  # Supported platforms and provider notes
├── vsphere.md         # vSphere-specific configuration
├── vsphere-example.md # Example vSphere deployment
├── state-migration-procedure.md  # State migration between backends
├── drift-detection.md            # Detect and remediate drift
└── ansible-integration.md        # How Terraform outputs feed Ansible
```

## Customization points

### 1. terraform.tfvars (copy from example)

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars for your environment
```

Example `terraform.tfvars`:

```hcl
vm_username   = "ansible"
vm_os_image   = "oracle-linux-9"
vm_flavor     = "m4.large"
vm_network    = "internal"
target_cluster = "application"
node_count    = 3
internal_registry = "harbor.internal:5000"
vault_addr    = "https://vault.internal:8200"
```

| Variable | Default | Customize when |
| --- | --- | --- |
| `vm_username` | `ansible` | Your SSH admin user differs |
| `vm_os_image` | `oracle-linux-9` | You use Ubuntu/RHEL/Windows |
| `vm_flavor` | `m4.large` | Your VM sizing differs |
| `vm_network` | `internal` | Your network name differs |
| `target_cluster` | `application` | You provision management/storage/LB nodes |
| `node_count` | `1` | You need more/fewer VMs |
| `internal_registry` | `harbor.internal:5000` | Your Harbor address differs |
| `vault_addr` | `https://vault.internal:8200` | Your Vault address differs |

### 2. variables.tf

Add new variables here when you need new inputs. Never hardcode values in `main.tf` — reference `var.*` instead.

### 3. outputs.tf

Outputs that feed Ansible inventory:

- `new_node_ips` — IPs of newly provisioned VMs
- `vm_ids` — VM identifiers for tagging

## How to run

### Prerequisites

```bash
cd automation/terraform
terraform version  # >= 1.5
```

### Initialize

```bash
terraform init
```

### Plan (dry-run)

```bash
terraform plan -var-file=terraform.tfvars
```

### Apply

```bash
terraform apply -var-file=terraform.tfvars -auto-approve
```

### Destroy

```bash
terraform destroy -var-file=terraform.tfvars -auto-approve
```

### Feed outputs to Ansible

After `terraform apply`, capture `new_node_ips` and write them into `automation/ansible/inventories/<env>/hosts.ini` under the appropriate group. See [ansible-integration.md](../automation/terraform/ansible-integration.md).

## Secrets handling

`terraform.tfvars.example` contains no secrets. Create `terraform.tfvars` locally (gitignored) and populate sensitive values from Vault or an `.env` file. Never commit `terraform.tfvars`.

## Related

- [Automation Artifacts overview](index.md)
- [Terraform vsphere config](../automation/terraform/virtualization.md)
- [Terraform state migration](../automation/terraform/state-migration-procedure.md)
- [Terraform drift detection](../automation/terraform/drift-detection.md)
