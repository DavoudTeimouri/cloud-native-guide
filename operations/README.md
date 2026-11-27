# Operations Guides

This directory contains operational runbooks for the Cloud-Native Stack.

## Installation Operations

| Guide | Description |
|---|---|
| [OS Provisioning](../operations/installation/os-provisioning.md) | Bare metal to hardened node via Ansible |
| [Kubernetes Install](../operations/installation/kubernetes-install.md) | Kubespray deployment with offline images |
| [Ceph Deployment](../operations/installation/ceph-deployment.md) | cephadm standalone deployment |
| [Management Cluster](../operations/installation/management-cluster.md) | Rancher, Argo CD, Keycloak setup |

## Upgrade Operations

| Guide | Description |
|---|---|
| [Kubernetes Upgrade](../operations/upgrade/kubernetes-upgrade.md) | Kubespray minor version upgrade |
| [Add-on Upgrade](../operations/upgrade/addon-upgrade.md) | Helm chart upgrades for platform add-ons |
| [Ceph Upgrade](../operations/upgrade/ceph-upgrade.md) | Ceph version upgrade with rebalance |
| [Vault Upgrade](../operations/upgrade/vault-upgrade.md) | Vault version upgrade with unseal |
| [OS Upgrade](../operations/upgrade/os-upgrade.md) | OS patching and kernel upgrades |

## Migration Operations

| Guide | Description |
|---|---|
| [Kubespray Migration](../operations/migration/kubespray-migration.md) | Migrate between Kubespray releases |
| [Ceph Migration](../operations/migration/ceph-migration.md) | Ceph major version migration |
| [Vault Migration](../operations/migration/vault-migration.md) | Vault major version migration |
| [OS Migration](../operations/migration/os-migration.md) | OS major version migration |

## Troubleshooting Runbooks

| Runbook | Description |
|---|---|
| [Kubernetes Issues](../troubleshooting/kubernetes.md) | API server, etcd, kubelet, CNI |
| [Ceph Issues](../troubleshooting/ceph.md) | MON, OSD, PG, pool issues |
| [Vault Issues](../troubleshooting/vault.md) | Seal/unseal, auth, policies |
| [Network Issues](../troubleshooting/network.md) | CNI, DNS, MetalLB, firewall |
| [Storage Issues](../troubleshooting/storage.md) | CSI, PVC, CephFS, RBD |
| [Identity Issues](../troubleshooting/identity.md) | Keycloak, OIDC, SSSD, LDAP |
| [Vault Issues](../troubleshooting/vault.md) | Seal/unseal, auth, policies |
| [GPU Issues](../troubleshooting/gpu.md) | GPU Operator, drivers, MIG |
| [Registry Issues](../troubleshooting/registry.md) | Harbor, Nexus, GitLab registry |
| [GitOps Issues](../troubleshooting/gitops.md) | Argo CD, drift, sync failures |

## Backup and Recovery

| Guide | Description |
|---|---|
| [etcd Backup/Restore](../backup-recovery/etcd-backup-restore.md) | etcd snapshot and restore |
| [Velero Backup/Restore](../backup-recovery/velero-backup-restore.md) | Velero cluster backup/restore |
| [Vault Backup/Restore](../backup-recovery/vault-backup-restore.md) | Vault snapshot and unseal |
| [Ceph Backup/Restore](../backup-recovery/ceph-backup-restore.md) | Ceph backup and disaster recovery |
| [GitLab Backup/Restore](../backup-recovery/gitlab-backup-restore.md) | GitLab backup and restore |
| [Harbor Backup/Restore](../backup-recovery/harbor-backup-restore.md) | Harbor backup and restore |

## Maintenance Procedures

| Procedure | Frequency | Owner |
|---|---|---|
| OS Patching | Monthly | Platform |
| Kubernetes Minor Upgrade | Quarterly | Platform |
| Certificate Renewal | Automatic (cert-manager) | Platform |
| Vulnerability DB Refresh | Monthly | Security |
| Restore Drill (App) | Quarterly | SRE |
| Restore Drill (Full Env) | Annually | Platform |
| DR Exercise | Annually | Platform |
| ADR Review | Annually | Architects |