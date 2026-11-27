variable "vm_username" {
  description = "SSH username for provisioned VMs"
  type        = string
  default     = "ansible"
}

variable "vm_os_image" {
  description = "OS image to provision"
  type        = string
  default     = "oracle-linux-9"
}

variable "vm_flavor" {
  description = "VM flavor/size"
  type        = string
  default     = "m4.large"
}

variable "vm_network" {
  description = "Network name for VMs"
  type        = string
  default     = "internal"
}

variable "target_cluster" {
  description = "Cluster to scale: management, application, storage, load-balancers"
  type        = string
  default     = "application"
}

variable "node_count" {
  description = "Number of nodes to provision"
  type        = number
  default     = 1
}

variable "internal_registry" {
  description = "Internal container registry address"
  type        = string
  default     = "harbor.internal:5000"
}

variable "vault_addr" {
  description = "Vault address for secrets"
  type        = string
  default     = "https://vault.internal:8200"
}

variable "dns_servers" {
  description = "DNS servers for VMs"
  type        = list(string)
  default     = ["10.10.0.53"]
}

variable "ntp_servers" {
  description = "NTP servers for VMs"
  type        = list(string)
  default     = ["10.10.0.1", "10.10.0.2"]
}
