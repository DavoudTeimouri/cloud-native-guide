# Compatibility, Order, Backup, Rollback

## Purpose and scope
Version compatibility, upgrade order, backup, pre/post validation, rollback strategy, downtime considerations.

## Rules
- Never recommend an upgrade without checking component compatibility and supported upgrade paths
- Check shared version & compatibility matrix before starting
- Backup before upgrade (etcd, application data, configuration)
- One control-plane node at a time to preserve etcd quorum
- Rollback strategy documented per component

## Upgrade order (recommended)
1. Management cluster components (Rancher, Argo CD, Keycloak, Vault)
2. Application cluster control plane (one node at a time)
3. Application cluster workers
4. Add-ons (CNI, CSI, ingress, monitoring)
5. OS/firmware/hypervisor (one node at a time)

## Rollback strategy
- Documented per component
- etcd snapshot restore for control plane
- Helm rollback for add-ons
- VM snapshot restore for OS/hypervisor

## Related
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
- [Troubleshooting (08-ha-and-failover.md)](../08-troubleshooting-and-diagnostics/08-ha-and-failover.md)
- [Maintenance and Operations (11-backup-verification-recovery-test.md)](../11-maintenance-and-operations/11-backup-verification-recovery-test.md)
