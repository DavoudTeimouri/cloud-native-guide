# Terraform — vSphere VM example

Minimal Terraform configuration that clones a template, sets hardware, network, and customizes the guest. All versions pinned; no `latest` tags.

```hcl
terraform {
  required_version = ">= 1.9.0, < 1.10.0"
  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = ">= 2.4.0, < 3.0.0"
    }
  }
}

provider "vsphere" {
  user           = var.vsphere_user
  password       = var.vsphere_password
  vsphere_server = var.vsphere_server
  allow_unverified_ssl = true
}

variable "vsphere_user"   { type = string }
variable "vsphere_password" { type = string, sensitive = true }
variable "vsphere_server" { type = string }

variable "vm_name"        { type = string }
variable "vm_template"    { type = string }   # e.g. /DC01/vm/template/ubuntu-2404
variable "vm_datacenter"  { type = string }
variable "vm_cluster"     { type = string }
variable "vm_datastore"   { type = string }
variable "vm_network"     { type = string }   # e.g. /DC01/network/VM Network
variable "vm_cpu"         { type = number, default = 4 }
variable "vm_memory"      { type = number, default = 8192 }
variable "vm_disk_gb"     { type = number, default = 100 }

data "vsphere_datacenter" "dc" {
  name = var.vm_datacenter
}

data "vsphere_compute_cluster" "cluster" {
  name          = var.vm_cluster
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_datastore" "ds" {
  name          = var.vm_datastore
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_network" "net" {
  name          = var.vm_network
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_virtual_machine" "template" {
  name          = var.vm_template
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_resource_pool" "pool" {
  name          = "Resources"
  datacenter_id = data.vsphere_datacenter.dc.id
}

resource "vsphere_virtual_machine" "vm" {
  name             = var.vm_name
  resource_pool_id = data.vsphere_resource_pool.pool.id
  datastore_id     = data.vsphere_datastore.ds.id
  num_cpus         = var.vm_cpu
  memory           = var.vm_memory
  guest_id         = data.vsphere_virtual_machine.template.guest_id
  scsi_type        = data.vsphere_virtual_machine.template.scsi_type

  network_interface {
    network_id   = data.vsphere_network.net.id
    adapter_type = data.vsphere_virtual_machine.template.network_adapter_type
  }

  disk {
    label            = "disk0"
    size             = var.vm_disk_gb
    eagerly_scrub    = false
    thin_provisioned = true
  }

  clone {
    template_uuid = data.vsphere_virtual_machine.template.id
  }

  # Guest customization: static IP, DNS, hostname. Applied on first boot.
  # Requires VMware Tools in the template.
  customization {
    timeout        = 0
    dns_suffix     = var.vm_dns_suffix
    dns_server_list = [var.vm_dns_server]
    ipv4_gateway   = var.vm_ipv4_gateway
    wait_for_guest_ip_timeout = 0

    network_interface {
      ipv4_address  = var.vm_ipv4_address
      ipv4_netmask  = var.vm_ipv4_netmask
    }
  }
}
```

## Symptom: Customization fails (guest IP never appears)

**Likely cause:** VMware Tools not installed in the template, or the customization spec conflicts with the guest OS network config.

**Fix:** Install open-vm-tools / VMware Tools in the template; use DHCP or match the guest's existing network config.

**Self-check:** `terraform apply` output shows the VM's `ip_address` after `wait_for_guest_ip_timeout`.

**Ponytail:** Scope ceiling — single VM from template with static customization. Add VM tags, storage policies, resource pools with limits, and anti-affinity rules when those patterns are used.
