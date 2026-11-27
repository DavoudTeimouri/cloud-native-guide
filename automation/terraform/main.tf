terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 2.0"
    }
    vsphere = {
      source  = "terraform-provider-vsphere/vsphere"
      version = "~> 2.0"
    }
  }
}

provider "openstack" {
  identity_endpoint = var.vault_addr # resolved via Vault at plan time
}

data "openstack_network" "internal" {
  name = var.vm_network
}

data "openstack_images_image" "os_image" {
  name = var.vm_os_image
}

resource "openstack_compute_instance_v2" "node" {
  count      = var.node_count
  name       = "${var.target_cluster}-node-${count.index + 1}"
  image_id   = data.openstack_images_image.os_image.id
  flavor_name = var.vm_flavor
  key_pair   = var.vm_username
  networks   = [
    {
      uuid = data.openstack_network.internal.id
    }
  ]
  metadata = {
    cluster = var.target_cluster
    role    = var.target_cluster
  }
}

output "new_node_ips" {
  value       = openstack_compute_instance_v2.node[*].access_ip_v4
  description = "IPs of newly provisioned nodes"
}

output "new_node_names" {
  value       = openstack_compute_instance_v2.node[*].name
  description = "Names of newly provisioned nodes"
}
