# Inventory Management

This document describes the Ansible inventory structure and management for the Cloud-Native Stack.

## Overview

Inventories define the target hosts for Ansible playbooks. They are organized by environment and role, following the topology defined in the reference architecture.

## Inventory Structure

```
inventories/
├── production/
│   ├── site.yml                    # Main playbook entry point
│   ├── group_vars/
│   │   ├── all.yml                 # Global variables
│   │   ├── control-plane.yml       # Control plane variables
│   │   ├── worker.yml              # Worker node variables
│   │   ├── storage.yml             # Ceph storage variables
│   │   ├── gpu.yml                 # GPU node variables
│   │   ├── management.yml          # Management cluster variables
│   │   ├── networking.yml          # Network/CNI/MetalLB variables
│   │   ├── storage.yml             # Ceph/Rook variables
│   │   ├── security.yml            # Security/PSS/Gatekeeper variables
│   │   ├── monitoring.yml          # Prometheus/Grafana/Loki variables
│   │   └── vault.yml               # Vault integration variables
│   ├── host_vars/
│   │   ├── k8s-cp-1.yml
│   │   ├── k8s-cp-2.yml
│   │   ├── k8s-cp-3.yml
│   │   ├── k8s-w-1.yml
│   │   └── ...
│   └── inventory.ini               # Host inventory (generated)
├── staging/
│   ├── site.yml
│   ├── group_vars/
│   │   └── ...
│   └── host_vars/
│       └── ...
└── dr/
    ├── site.yml
    └── ...
```

## Inventory File Format

### inventory.ini (Generated)
```ini
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13

[worker]
k8s-w-1 ansible_host=10.30.0.11
k8s-w-2 ansible_host=10.30.0.12
k8s-gpu-1 ansible_host=10.50.0.11

[storage]
ceph-st-1 ansible_host=10.40.0.11
ceph-st-2 ansible_host=10.40.0.12
ceph-st-3 ansible_host=10.40.0.13

[management-control-plane]
mgmt-cp-1 ansible_host=10.10.0.11
mgmt-cp-2 ansible_host=10.10.0.12
mgmt-cp-3 ansible_host=10.10.0.13

[management-infra]
mgmt-infra-1 ansible_host=10.10.0.21
mgmt-infra-2 ansible_host=10.10.0.22
mgmt-infra-3 ansible_host=10.10.0.23

[automation]
ams-1 ansible_host=10.10.0.10
ams-2 ansible_host=10.10.0.11  # standby

[lb]
lb-1 ansible_host=10.60.0.10
lb-2 ansible_host=10.60.0.11

[identity]
keycloak-1 ansible_host=10.10.0.31
keycloak-2 ansible_host=10.10.0.32

[vault]
vault-1 ansible_host=10.10.0.41
vault-2 ansible_host=10.10.0.42
vault-3 ansible_host=10.10.0.43

[gitlab]
gitlab-1 ansible_host=10.10.0.51
gitlab-2 ansible_host=10.10.0.52

[harbor]
harbor-1 ansible_host=10.10.0.61
harbor-2 ansible_host=10.10.0.62

[nexus]
nexus-1 ansible_host=10.10.0.71
nexus-2 ansible_host=10.10.0.72

[registry]
registry-1 ansible_host=10.10.0.81
registry-2 ansible_host=10.10.0.82

[gitlab-runner]
runner-1 ansible_host=10.10.0.91
runner-2 ansible_host=10.10.0.92

[monitoring]
prometheus-1 ansible_host=10.10.0.101
grafana-1 ansible_host=10.10.0.102
loki-1 ansible_host=10.10.0.103

[all:vars]
ansible_user=ansible
ansible_become=true
ansible_python_interpreter=/usr/bin/python3
```

## Group Variables

### all.yml (Global)
```yaml
# Global settings applied to all hosts
ansible_user: ansible
ansible_become: true
ansible_python_interpreter: /usr/bin/python3

# Timezone
timezone: UTC

# NTP
ntp_servers:
  - 10.10.0.1
  - 10.10.0.2

# DNS
dns_servers:
  - 10.10.0.53
  - 10.10.0.54

# Internal registries
internal_registry: "harbor.internal:5000"
internal_helm_repo: "https://harbor.internal/charts"
internal_nexus: "https://nexus.internal"

# Internal CA
internal_ca_cert: "/etc/ssl/certs/internal-ca.crt"
internal_ca_key: "/etc/ssl/private/internal-ca.key"

# Vault
vault_addr: "https://vault.internal:8200"
vault_namespace: "platform"
vault_kubernetes_auth_path: "kubernetes"
vault_kubernetes_role: "platform"

# Keycloak
keycloak_url: "https://keycloak.internal"
keycloak_realm: "platform"

# Monitoring
prometheus_retention: "30d"
grafana_admin_user: "admin"
loki_retention: "30d"

# Backup
velero_schedule: "0 2 * * *"
velero_ttl: "720h"
```

### control-plane.yml
```yaml
# Control plane specific settings
kubernetes_version: "1.36.5"
kube_api_server_port: 6443
etcd_version: "3.6.15"
containerd_version: "2.3.7"

# HA
control_plane_endpoint: "10.20.0.100"
control_plane_vip: "10.20.0.100"

# CNI
cilium_version: "1.20.3"
cilium_hubble_enabled: true
cilium_hubble_relay_enabled: true

# Metrics
metrics_server_version: "3.14.0"
metrics_server_replicas: 2
```

### worker.yml
```yaml
# Worker node settings
kubelet_max_pods: 110
kubelet_pods_per_core: 10

# Resource reservations
kube_reserved:
  cpu: "500m"
  memory: "512Mi"
  ephemeral-storage: "1Gi"
system_reserved:
  cpu: "500m"
  memory: "512Mi"
  ephemeral-storage: "1Gi"
eviction_hard:
  memory.available: "500Mi"
  nodefs.available: "10%"
  imagefs.available: "15%"
```

### storage.yml (Ceph)
```yaml
# Ceph cluster settings
ceph_version: "tentacle-20.2.4"
ceph_public_network: "10.40.0.0/24"
ceph_cluster_network: "10.41.0.0/24"
ceph_mon_count: 3

# Rook
rook_version: "v1.21.0"
rook_ceph_version: "20.2.4"
ceph_csi_version: "3.11.0"

# Storage classes
storage_classes:
  - name: "ceph-rbd"
    provisioner: "rook-ceph.rbd.csi.ceph.com"
    reclaim_policy: "Delete"
    volume_binding_mode: "Immediate"
    parameters:
      clusterID: "rook-ceph"
      pool: "replicapool"
      imageFormat: "2"
      imageFeatures: "layering"
      csi.storage.k8s.io/provisioner-secret-name: "rook-csi-rbd-provisioner"
      csi.storage.k8s.io/provisioner-secret-namespace: "rook-ceph"
      csi.storage.k8s.io/controller-expand-secret-name: "rook-csi-rbd-provisioner"
      csi.storage.k8s.io/controller-expand-secret-namespace: "rook-ceph"
      csi.storage.k8s.io/node-stage-secret-name: "rook-csi-rbd-node"
      csi.storage.k8s.io/node-stage-secret-namespace: "rook-ceph"

  - name: "cephfs"
    provisioner: "rook-ceph.cephfs.csi.ceph.com"
    reclaim_policy: "Delete"
    volume_binding_mode: "Immediate"
    parameters:
      clusterID: "rook-ceph"
      fsName: "cephfs"
      csi.storage.k8s.io/provisioner-secret-name: "rook-csi-cephfs-provisioner"
      csi.storage.k8s.io/provisioner-secret-namespace: "rook-ceph"
      csi.storage.k8s.io/controller-expand-secret-name: "rook-csi-cephfs-provisioner"
      csi.storage.k8s.io/controller-expand-secret-namespace: "rook-ceph"
      csi.storage.k8s.io/node-stage-secret-name: "rook-csi-cephfs-node"
      csi.storage.k8s.io/node-stage-secret-namespace: "rook-ceph"
```

### gpu.yml
```yaml
# GPU node settings
nvidia_driver_version: "595.71.05"
nvidia_container_toolkit_version: "1.20.1"
nvidia_gpu_operator_version: "26.7.2"

# MIG
mig_enabled: true
mig_strategy: "mixed"

# Device plugin
device_plugin_enabled: true
device_plugin_config:
  deviceListStrategy: "envvar"
  deviceIDStrategy: "uuid"
```

### management.yml
```yaml
# Management cluster
rancher_version: "v2.15.2"
rancher_hostname: "rancher.internal"
rancher_replicas: 3

argocd_version: "v3.5.6"
argocd_replicas: 2
argocd_dex_enabled: true
argocd_oidc_enabled: true

keycloak_version: "26.8.1"
keycloak_replicas: 2
keycloak_db_vendor: "postgres"
keycloak_db_host: "postgres.internal"

prometheus_stack_version: "92.11.0"
prometheus_retention: "30d"
thanos_enabled: false
grafana_version: "13.2.4"
loki_version: "v3.7.9"
```

### networking.yml
```yaml
# MetalLB
metallb_version: "0.16.1"
metallb_ip_pools:
  - name: "production"
    addresses: ["10.61.0.10-10.61.0.30"]
    protocol: "layer2"
    auto_assign: true

# NGINX Ingress (F5)
nginx_ingress_version: "2.8.0"
nginx_ingress_controller_replicas: 3

# Gateway API
gateway_api_version: "v1.6.3"
nginx_gateway_fabric_version: "2.8.0"

# CoreDNS
coredns_forwarders: "10.10.0.53 10.10.0.54"
coredns_forward_policy: "sequential"

# Cilium
cilium_version: "1.20.3"
cilium_hubble_enabled: true
cilium_hubble_relay_enabled: true
cilium_hubble_ui_enabled: true
cilium_ipam_mode: "cluster-pool"
cilium_cluster_pool_ipv4_cidr: "10.30.0.0/16"
cilium_cluster_pool_ipv4_mask_size: "24"
```

### security.yml
```yaml
# Pod Security Standards
pod_security_standards:
  restricted:
    enabled: true
    exempt_namespaces:
      - kube-system
      - cert-manager
      - external-dns

# Gatekeeper
gatekeeper_version: "v3.23.1"
gatekeeper_audit_interval: "60s"
gatekeeper_constraint_templates:
  - k8srequiredlabels
  - k8spspprivilegedcontainer
  - k8spsphostfilesystem
  - k8spsphostnetworkingports
  - k8spsphostpid
  - k8spspprivilegeescalation

# Kyverno
kyverno_version: "v1.19.2"
kyverno_policies:
  - require-labels
  - restrict-privileged
  - restrict-host-path

# Falco
falco_version: "0.45.1"
falco_rules:
  - falco-rules
  - k8s-audit-rules
  - k8s-network-rules

# Trivy
trivy_version: "v0.76.1"
trivy_severity: "CRITICAL,HIGH"
trivy_ignore_unfixed: true
```

### monitoring.yml
```yaml
# Prometheus
prometheus_version: "v3.15.1"
prometheus_operator_version: "v0.94.1"
prometheus_retention: "30d"
prometheus_storage: "50Gi"

# Alertmanager
alertmanager_version: "v0.34.1"
alertmanager_replicas: 3
alertmanager_config:
  receivers:
    - name: "default"
      email_configs:
        - to: "alerts@internal"
          smtp_smarthost: "smtp.internal:587"

# Grafana
grafana_version: "13.2.4"
grafana_datasources:
  - name: "Prometheus"
    type: "prometheus"
    url: "http://prometheus.monitoring.svc:9090"
  - name: "Loki"
    type: "loki"
    url: "http://loki.logging.svc:3100"

# Loki
loki_version: "v3.7.9"
loki_retention: "30d"
loki_storage: "100Gi"

# Thanos (optional)
thanos_enabled: false
thanos_version: "v0.42.4"
```

### vault.yml
```yaml
# Vault integration
vault_addr: "https://vault.internal:8200"
vault_namespace: "platform"
vault_kubernetes_auth_path: "kubernetes"
vault_kubernetes_role: "platform"
vault_pki_path: "pki/sign/platform"
vault_pki_ttl: "8760h"  # 1 year

# cert-manager
cert_manager_version: "v1.21.2"
cert_manager_cluster_issuer:
  name: "vault-pki"
  vault_path: "pki/sign/platform"
  auth:
    kubernetes:
      role: "cert-manager"
      mount_path: "/v1/auth/kubernetes"
      service_account_ref:
        name: "cert-manager-vault-issuer"
        key: "token"

# External Secrets Operator
eso_version: "v2.13.0"
eso_cluster_secret_store:
  name: "vault-backend"
  provider:
    vault:
      server: "https://vault.internal:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mount_path: "kubernetes"
          role: "external-secrets"
          service_account_ref:
            name: "external-secrets-vault"
            namespace: "external-secrets"
```

## Inventory Generation

### From Terraform
```bash
# Generate inventory from Terraform outputs
terraform output -json vm_ips | python3 scripts/generate_inventory.py --output inventories/production/inventory.ini
```

### From GitLab CI
```yaml
# .gitlab-ci.yml
generate_inventory:
  stage: prepare
  script:
    - terraform output -json vm_ips > vm_ips.json
    - python3 scripts/generate_inventory.py --input vm_ips.json --output inventory.ini
    - cp inventory.ini inventories/production/
  artifacts:
    paths:
      - inventories/production/inventory.ini
```

## Inventory Validation

```bash
# Validate inventory syntax
ansible-inventory -i inventories/production/inventory.ini --list

# Test connectivity
ansible all -i inventories/production/inventory.ini -m ping

# Check group vars
ansible-inventory -i inventories/production/inventory.ini --host k8s-cp-1
```

## Inventory per Environment

| Environment | Path | Purpose |
|---|---|---|
| Production | `inventories/production/` | Production workloads |
| Staging | `inventories/staging/` | Pre-production validation |
| DR | `inventories/dr/` | Disaster recovery |

Each environment has its own `group_vars` and `host_vars` for environment-specific configuration.
