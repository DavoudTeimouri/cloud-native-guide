# Terraform — VM provisioning overview

Terraform provisions VMs across virtualization platforms. vSphere is the primary platform; the same pattern applies to other providers (libvirt, Proxmox, oVirt, OpenStack) where a provider plugin exists.

## Supported platforms

| Platform | Terraform provider | Notes |
|----------|-------------------|-------|
| VMware vSphere | `hashicorp/vsphere` | Primary platform. Template clone + customization spec. |
| libvirt / KVM | `dmacvicar/libvirt` | Local lab and CI runners. QEMU/KVM on Linux hosts. |
| Proxmox | `bpg/proxmox` | Alternative hypervisor for on-prem labs. |
| oVirt / RHEV | `terraform-provider-ovirt` | RHEV-based virtualization. |
| OpenStack | `terraform-provider-openstack` | Private cloud with Nova. |

## Symptom: Provider not found at `terraform init`

**Likely cause:** `required_providers` block missing or pinned to an unavailable version.

**Fix:** Add a `required_providers` block and run `terraform init` to install the provider.

**Self-check:** `terraform init` completes with `Providers are fully installed.`; `terraform providers` lists the expected provider.

## Symptom: Template not found

**Likely cause:** The vSphere template path or name does not match, or the datacenter/folder is wrong.

**Fix:** Use the full inventory path (`/DC01/vm/template/ubuntu-2404`) and confirm the template exists in vCenter.

**Self-check:** `terraform plan` lists the template as the `source` for `vsphere_virtual_machine`.

**Ponytail:** Scope ceiling — provider selection and template cloning. Add multi-region vCenter, storage-policy-based placement, and VM affinity rules when those patterns are used.
