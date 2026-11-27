# Maintenance and Operations

## Purpose and scope
Document ongoing operational procedures: daily/weekly/monthly operations, quarterly reviews, security patching, certificate renewal, backup verification, recovery testing, storage/cluster health, monitoring review, vulnerability management, repo sync, log retention, config drift, hardware maintenance, node replacement, DR exercises. Provides reusable operational checklists and runbooks.

## Subsections
| Subsection | Covers |
|---|---|
| [Daily, Weekly, Monthly Operations](11-daily-weekly-monthly.md) | Daily health checks, weekly checks, monthly checks |
| [Quarterly Capacity Review](11-quarterly-capacity-review.md) | Quarterly reviews, capacity reviews, growth estimates |
| [Security Patching & Certificate Renewal](11-security-patching-cert-renewal.md) | Security patching, certificate renewal, PKI/CA rotation, Vault unseal shares |
| [Backup Verification & Recovery Testing](11-backup-verification-recovery-test.md) | Backup verification, recovery testing, Velero restore drills, etcd snapshot restore |
| [Storage & Cluster Health](11-storage-cluster-health.md) | Storage health, Ceph health, cluster health monitoring |
| [Monitoring Review & Vulnerability Management](11-monitoring-review-vuln-mgmt.md) | Monitoring review, vulnerability management, security scanning |
| [Repo Sync, Log Retention, Config Drift](11-repo-sync-log-retention-drift.md) | Repository synchronization, log retention, configuration drift detection |
| [Hardware Maintenance, Node Replacement, DR Exercise](11-hardware-node-replacement-dr-exercise.md) | Hardware maintenance, node replacement, DR exercises, RTO/RPO measurement |

## Cross-references
- Backup/recovery details in [03 · Repository & Registry Management (3.7)](../03-repository-registry/3.7-validation-operations.md) and [08 · Troubleshooting](../08-troubleshooting-and-diagnostics/index.md)
- Upgrade procedures in [10 · Upgrade and Lifecycle Management](../10-upgrade-and-lifecycle-management/index.md)
- Versions from [shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
