output "vm_ssh_command" {
  value = "ssh -i ~/.ssh/id_ed25519 ${var.vm_username}@${openstack_compute_instance_v2.node[0].access_ip_v4}"
}

output "ansible_inventory_snippet" {
  value = formatlist("%s ansible_host=%s", openstack_compute_instance_v2.node[*].name, openstack_compute_instance_v2.node[*].access_ip_v4)
}
