# Infrastructure Provisioning with Terraform

This document describes the Terraform-based infrastructure provisioning for the Cloud-Native Stack.

## Overview

Terraform is used as an optional infrastructure provisioning tool alongside Ansible. It provisions VMs across virtualization platforms; Ansible configures them after provisioning.

## Supported Platforms

| Platform | Terraform Provider | Notes |
|---|---|---|
| VMware vSphere | `hashicorp/vsphere` | Primary platform. Template clone + customization spec. |
| libvirt / KVM | `dmacvicar/libvirt` | Local lab and CI runners. QEMU/KVM on Linux hosts. |
| Proxmox | `bpg/proxmox` | Alternative hypervisor for on-prem labs. |
| oVirt / RHEV | `terraform-provider-ovirt` | RHEV-based virtualization. |
| OpenStack | `terraform-provider-openstack` | Private cloud with Nova. |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Terraform Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   vSphere   │  │   libvirt   │  │     Proxmox/ovirt   │  │
│  │  Provider   │  │  Provider   │  │      Provider       │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     Ansible Layer                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              VM Configuration Playbooks                   │ │
│  │  OS Baseline • Security • Monitoring • Ceph Prep        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Workflow

1. **Terraform Plan** → `terraform plan` shows VM changes
2. **Terraform Apply** → `terraform apply` provisions VMs
3. **Wait for SSH** → Wait for VM boot and SSH readiness
4. **Ansible Configure** → `ansible-playbook` configures VMs
4. **Validate** → `ansible all -m ping` confirms readiness

## Provider Version Pinning

```hcl
terraform {
  required_version = ">= 1.9.0, < 1.10.0"
  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = ">= 2.4.0, < 3.0.0"
    }
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = ">= 0.7.0, < 1.0.0"
    }
  }
}
```

## vSphere Example

See [automation/terraform/vsphere-example.md](../automation/terraform/vsphere-example.md) for a complete vSphere VM example with:
- Template clone
- Hardware configuration (CPU, memory, disk)
- Network configuration
- Guest customization (static IP, DNS, hostname)

## Common Patterns

### Template Requirements
- VMware Tools installed
- cloud-init or customization spec configured
- SSH enabled with key-based auth
- Cloud-init datasource configured

### Network Configuration
```hcl
network_interface {
  network_id   = data.vsphere_network.net.id
  adapter_type = data.vsphere_virtual_machine.template.network_adapter_type
}
```

### Guest Customization
```hcl
customization {
  dns_suffix     = var.vm_dns_suffix
  dns_server_list = [var.vm_dns_server]
  ipv4_gateway   = var.vm_ipv4_gateway
  network_interface {
    ipv4_address  = var.vm_ipv4_address
    ipv4_netmask  = var.vm_ipv4_netmask
  }
}
```

## Ansible Integration

Terraform outputs VM IPs; Ansible reads them as inventory:

```hcl
output "vm_ips" {
  value = vsphere_virtual_machine.vm[*].default_ip_address
}
```

```bash
# Generate Ansible inventory from Terraform output
terraform output -json vm_ips | jq -r '.[]' > inventory.yml
ansible-playbook -i inventory.yml site.yml
```

## Air-Gap Considerations

- Provider binaries mirrored to `registry.internal:5000/terraform-providers/`
- Provider cache: `terraform init` with `-plugin-dir`
- Module sources: Local paths or internal GitLab

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Provider not found at `terraform init` | `required_providers` block missing or version unavailable | Add `required_providers` block, run `terraform init` |
| Template not found | vSphere template path/name mismatch or wrong datacenter/folder | Use full inventory path (`/DC01/vm/template/ubuntu-2404`), confirm template exists in vCenter |
| Customization fails (guest IP never appears) | VMware Tools not in template, or customization spec conflicts with guest OS network config | Install open-vm-tools/VMware Tools in template; use DHCP or match guest's existing network config |

## Version Pinning

| Provider | Version | Source |
|---|---|---|
| hashicorp/vsphere | >= 2.4.0, < 3.0.0 | Verified 2026-10-17 |
| dmacvicar/libvirt | >= 0.7.0, < 1.0.0 | Verified 2026-10-17 |
| bpg/proxmox | >= 0.60.0, < 1.0.0 | Verified 2026-10-17 |

## References

- [vSphere Provider Docs](https://registry.terraform.io/providers/hashicorp/vsphere/latest/docs)
- [libvirt Provider Docs](https://registry.terraform.io/providers/dmacvicar/libvirt/latest/docs)
- [Ansible-VMware Integration](../automation/ansible/ansible-structure.md)
- [VM Provisioning Overview](../automation/terraform/virtualization.md)