# Kubespray Deployment Guide (English)

This guide covers the automated deployment of Kubernetes clusters using Kubespray v2.32.0 for the Cloud-Native Stack platform.

## Overview

The deployment workflow separates concerns:
1. **Control Node Preparation** - Python environment, pinned dependencies, Kubespray source
2. **Node Prerequisites** - OS baseline, containerd, Kubernetes host prerequisites (see OS Preparation Guide)
3. **Deployment Preflight** - Validation of all configuration before deployment
4. **Cluster Deployment** - Explicit operator-invoked Kubespray execution

## Prerequisites

### Control Node
- Oracle Linux 9 or Ubuntu 22.04/24.04
- Python 3.11
- Internet access or internal mirrors for initial staging
- SSH key access to all target nodes (passwordless sudo)

### Target Nodes
- Completed OS baseline (playbooks/base.yml)
- Completed repository configuration (playbooks/repositories.yml)
- Completed security hardening (playbooks/security.yml)
- Completed time synchronization (playbooks/time-sync.yml)
- Completed containerd installation (playbooks/containerd.yml)
- **Completed Kubernetes node prerequisites** (playbooks/k8s-node-prereqs.yml)

### Internal Infrastructure
- Nexus repository mirror (DNF/APT)
- Harbor container registry with CA certificate
- Internal DNS/NTP servers
- Vault for secrets (optional)

## Quick Start

### 1. Prepare Control Node
```bash
cd automation/ansible
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-control-node.yml
```

### 2. Prepare Target Nodes
```bash
# Run OS baseline (if not already done)
ansible-playbook -i inventories/production/hosts.yml site.yml

# Run Kubernetes node prerequisites
ansible-playbook -i inventories/production/hosts.yml playbooks/k8s-node-prereqs.yml
```

### 3. Run Deployment Preflight
```bash
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-deploy.yml
```

Review the preflight output. If all checks pass:

### 4. Verify Kubernetes Version
Manually verify `kubespray_kubernetes_version: "1.36.5"` is the default Kubernetes version in Kubespray v2.32.0 (per upstream README.md component versions).
Set `kubernetes_version_verified: true` in group vars after verification.

### 5. Deploy Cluster (Explicit Operator Action)
```bash
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-deploy.yml \
  -e '{"kubespray_deploy_mode":"deploy","kubespray_operator_approval":true}'
```

**Note**: The approval variable MUST be a JSON boolean (`true`), not a string (`"true"`). String values will be rejected by the preflight check.

## Version Pinning

All versions are explicitly pinned for reproducibility. **Versions marked with ⚠️ are project overrides not from Kubespray v2.32.0 defaults.**

| Component | Version | Source | Status |
|-----------|---------|--------|--------|
| Kubespray | v2.32.0 | GitHub release tag | Verified |
| Kubernetes | 1.36.5 | Kubespray v2.32.0 default | Verified (default) |
| Ansible Core | 2.19.3 | PyPI / Kubespray v2.32.0 | Verified |
| Ansible | 12.3.0 | PyPI / Kubespray v2.32.0 | Verified |
| Cilium CNI | 1.20.3 | Kubespray v2.32.0 default | Verified (default) |
| Calico CNI | 3.31.7 | Kubespray v2.32.0 default | Verified (default) |
| Containerd | 2.3.7 | Kubespray v2.32.0 default | Verified (default) |
| Etcd | 3.6.15 | Kubespray v2.32.0 default | Verified (default) |
| CoreDNS | 1.14.2 | Kubespray v2.32.0 default | Verified (default) |
| Metrics Server | 0.8.0 | Kubespray v2.32.0 default | Verified (default) |
| cni-plugins | 1.9.1 | Kubespray v2.32.0 default | Verified (default) |

## Inventory Architecture

### Required Groups
| Group | Purpose | Minimum Nodes |
|-------|---------|---------------|
| kube_control_plane | Control plane nodes | 3 (HA) |
| kube_node | All Kubernetes nodes | 3+ |
| etcd | Etcd cluster (stacked) | 3 |

### Optional Groups
| Group | Purpose |
|-------|---------|
| kube_gpu | GPU worker nodes |
| kube_storage | Storage nodes (Ceph/Rook) |
| calico_rr | Calico route reflectors |

### Inventory Variables (per host)
```yaml
kubespray_node_labels:
  topology.kubernetes.io/zone: zone-a
  workload-type: general
kubespray_node_taints:
  - key: "dedicated"
    value: "gpu"
    effect: "NoSchedule"
```

## CNI Configuration

### Cilium (Primary Baseline)
```yaml
kubespray_cni_plugin: "cilium"
kubespray_cilium_tunneling_mode: "vxlan"  # vxlan, geneve, disabled
kubespray_cilium_hubble_enabled: true
kubespray_cilium_kube_proxy_replacement: "strict"  # disabled, partial, strict
kubespray_cilium_ipam_mode: "cluster-pool"
```

**Required Ports:**
- VXLAN: UDP 8472 (when tunneling_mode=vxlan)
- Geneve: UDP 6081 (when tunneling_mode=geneve)
- Hubble Relay: TCP 4245
- Hubble UI: TCP 12000

### Calico (Alternative)
```yaml
kubespray_cni_plugin: "calico"
kubespray_calico_vxlan_enabled: false
kubespray_calico_wireguard_enabled: false
kubespray_calico_typha_enabled: false
```

**Required Ports (when VXLAN enabled):**
- VXLAN: UDP 4789
- WireGuard: UDP 51820 (when enabled)

## Registry and Offline Integration

### Internal Registry
```yaml
kubespray_container_registry: "harbor.internal:5000"
kubespray_registry_ca_cert_path: "/etc/ssl/certs/harbor-ca.crt"
kubespray_registry_auth_enabled: true
```

### Offline Artifact Staging
```bash
# On connected staging host:
# 1. Pull all required images
kubespray-offline-images.sh --registry harbor.internal:5000 --output /tmp/kubespray-images.tar

# 2. Transfer to air-gapped environment
# 3. Load images into internal Harbor
```

**Required Image Categories:**
- Kubernetes components (kube-apiserver, kube-controller-manager, kube-scheduler, kube-proxy, etcd, coredns, pause)
- CNI (Cilium/Calico, Hubble, operator)
- Containerd (if not using system package)
- Add-ons (metrics-server, local-path-provisioner, etc.)

## Deployment Safety

### Preflight Checks
The deployment preflight validates:
- Kubespray release tag matches v2.32.0 (verified via `git describe --tags`)
- Kubernetes version in supported range (1.34.x - 1.36.x)
- Kubernetes version verified flag (`kubernetes_version_verified: true`)
- CNI selection valid and configured (cilium or calico)
- CIDRs don't overlap
- Required inventory groups exist with correct counts
- Etcd nodes are subset of control plane (stacked topology)
- Registry CA certificate exists
- Control node environment prepared (venv, collections, Kubespray source)
- Target node prerequisites completed (k8s-node-prereqs role)

### Operator Approval Required
Deployment **will not run** without explicit approval. The approval MUST be a JSON boolean:
```bash
-e '{"kubespray_deploy_mode":"deploy","kubespray_operator_approval":true}'
```

**Important**: String values (`"true"`, `"yes"`, `"1"`) are rejected. Only boolean `true` passes the preflight check.

### No Automatic Changes
- Preflight makes NO changes to target hosts
- Deployment only runs after explicit operator action
- No unattended or automatic cluster reset

## Upgrade and Scale-Out

**Not implemented in this task.** Future workflows will cover:
- Kubernetes version upgrade (rolling)
- Control plane scale-out
- Worker node scale-out
- Etcd member management
- CNI migration

## Troubleshooting

### Preflight Failures
```bash
# Check specific validation
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-deploy.yml -e kubespray_preflight_check_all=true -v
```

### Control Node Issues
```bash
# Verify virtual environment
/opt/kubespray-venv/bin/ansible --version
/opt/kubespray-venv/bin/ansible-galaxy collection list

# Verify Kubespray source
cd /opt/kubespray && git describe --tags
```

### Target Node Issues
```bash
# Verify prerequisites
ansible all -i inventories/production/hosts.yml -m shell -a "crictl info"
ansible all -i inventories/production/hosts.yml -m shell -a "swapon --show"
ansible all -i inventories/production/hosts.yml -m shell -a "stat -fc %T /sys/fs/cgroup"
```

## Limitations

1. **No automatic cluster deployment** - Requires explicit operator action
2. **No upgrade workflow** - Separate future task
3. **No scale-out workflow** - Separate future task
4. **Kubernetes patch verification required** - Manual step; deployment blocked if `kubernetes_version_verified: false`
5. **Full Air-Gap not yet supported** - Control node dependencies need staging; Ansible collections/Python deps lack internal staging path
6. **GPU worker configuration not implemented** - Requires GPU role
7. **Cilium/Calico kernel config verification incomplete** - Some kernel configs require operator manual check (no `/boot/config-*` or `/proc/config.gz` on all systems)

## References

- [OS Preparation Guide](os-preparation.md)
- [Kubespray v2.32.0 Release Notes](https://github.com/kubernetes-sigs/kubespray/releases/tag/v2.32.0)
- [Kubespray v2.32.0 README Component Versions](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/README.md#supported-components)
- [Kubespray v2.32.0 Requirements.txt](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/requirements.txt)
- [Cilium 1.20 Documentation](https://docs.cilium.io/en/v1.20/)
- [Calico 3.31 Documentation](https://docs.tigera.io/calico/3.31/)

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-24*
