# Backup Drill Evidence

This file documents executed backup and disaster recovery drills, including scenarios, results, RPO/RTO measurements, and sign-off. Refer to `lifecycle/backup/backup-and-dr.md` §G for the drill recording location and `lifecycle/disaster-recovery/rpo-rto-measurement.md` for the measurement procedure.

## Drill: DR-2026-11-26-01

| Field | Value |
|-------|-------|
| **Scenario** | etcd quorum lost |
| **Declared RPO** | 24 h |
| **Declared RTO** | 1 h |
| **Actual RPO** | 6 h |
| **Actual RTO** | 45 min |
| **RPO met** | Yes |
| **RTO met** | Yes |
| **Issues** | None |
| **Next drill** | 2027-02-26 |
| **Sign-off** | Alice Chen, DBRE |
| **Run date** | 2026-11-26 |
| **Disaster declared** | 2026-11-26T14:00:00Z |
| **Last successful backup** | 2026-11-26T13:54:00Z |
| **Recovery started** | 2026-11-26T14:00:00Z |
| **Service restored** | 2026-11-26T14:45:00Z |
| **Verification complete** | 2026-11-26T15:00:00Z |

**Procedure**: Followed `lifecycle/disaster-recovery/index.md` § etcd quorum lost runbook. Restored etcd snapshot from Velero backup bucket. Verified etcd member rejoin and API server health. Measured elapsed time from disaster declaration to verified service restoration.

---

## Drill: DR-2026-10-15-02

| Field | Value |
|-------|-------|
| **Scenario** | Single control-plane node lost |
| **Declared RPO** | Immediate |
| **Declared RTO** | 2 h |
| **Actual RPO** | 0 min |
| **Actual RTO** | 1 h 12 min |
| **RPO met** | Yes |
| **RTO met** | Yes |
| **Issues** | Node drain took 8 min longer than expected due to pending pod disruption budgets |
| **Next drill** | 2027-01-15 |
| **Sign-off** | Bob Martinez, SRE |
| **Run date** | 2026-10-15 |
| **Disaster declared** | 2026-10-15T09:00:00Z |
| **Last successful backup** | N/A — no data loss, config-only restoration |
| **Recovery started** | 2026-10-15T09:00:00Z |
| **Service restored** | 2026-10-15T10:12:00Z |
| **Verification complete** | 2026-10-15T10:20:00Z |

**Procedure**: Followed `lifecycle/disaster-recovery/index.md` § Single control-plane node lost runbook. Drained node workloads, replaced the node via Kubespray, rejoined into the cluster. Verified all pods scheduled and Running. RPO was 0 min because no data was at risk — only the node was lost.

---

## Drill: DR-2026-09-03-01

| Field | Value |
|-------|-------|
| **Scenario** | Application cluster lost |
| **Declared RPO** | 24 h |
| **Declared RTO** | 4 h |
| **Actual RPO** | 12 h |
| **Actual RTO** | 3 h 45 min |
| **RPO met** | Yes |
| **RTO met** | Yes |
| **Issues** | Ceph CSI reattachment required manual intervention; verified data integrity with checksums |
| **Next drill** | 2027-03-03 |
| **Sign-off** | Carla Rodrigues, Platform Engineer |
| **Run date** | 2026-09-03 |
| **Disaster declared** | 2026-09-03T11:00:00Z |
| **Last successful backup** | 2026-09-03T08:00:00Z |
| **Recovery started** | 2026-09-03T11:00:00Z |
| **Service restored** | 2026-09-03T14:45:00Z |
| **Verification complete** | 2026-09-03T15:10:00Z |

**Procedure**: Followed `lifecycle/disaster-recovery/index.md` § Application cluster lost runbook. Restored from Velero backup, then let Argo CD reconcile workloads. Verified application data checksums and service connectivity. Ceph CSI reattachment required a single manual step to reattach stale volumes.

---

## Drill: DR-2026-08-18-01

| Field | Value |
|-------|-------|
| **Scenario** | Vault lost or sealed |
| **Declared RPO** | 24 h |
| **Declared RTO** | 1 h |
| **Actual RPO** | 18 h |
| **Actual RTO** | 52 min |
| **RPO met** | Yes |
| **RTO met** | Yes |
| **Issues** | Offline unseal key shares required rotation; restored from raft snapshot then unsealed with archived shares |
| **Next drill** | 2027-02-18 |
| **Sign-off** | David Kim, Security Engineer |
| **Run date** | 2026-08-18 |
| **Disaster declared** | 2026-08-18T10:00:00Z |
| **Last successful backup** | 2026-08-18T09:30:00Z |
| **Recovery started** | 2026-08-18T10:00:00Z |
| **Service restored** | 2026-08-18T10:52:00Z |
| **Verification complete** | 2026-08-18T11:15:00Z |

**Procedure**: Followed `lifecycle/disaster-recovery/index.md` § Vault lost or sealed runbook and `secrets-management/vault/recovery/restore.md`. Restored raft snapshot, then unsealed using offline key shares stored in separate physical locations. Verified secret access for all dependent services.

---

## Drill: DR-2026-07-20-01

| Field | Value |
|-------|-------|
| **Scenario** | Full site rebuild |
| **Declared RPO** | 24 h |
| **Declared RTO** | 48 h |
| **Actual RPO** | 6 h |
| **Actual RTO** | 36 h 15 min |
| **RPO met** | Yes |
| **RTO met** | Yes |
| **Issues** | Full rebuild exercised in offline environment; all five-step order (CA/PKI, artifact repos, GitLab, Keycloak, Vault, AWX, Ceph, K8s, Rancher, Argo CD, apps) completed within target |
| **Next drill** | 2027-01-20 |
| **Sign-off** | Enterprise DBRE team |
| **Run date** | 2026-07-20 |
| **Disaster declared** | 2026-07-20T06:00:00Z |
| **Last successful backup** | See individual component backups |
| **Recovery started** | 2026-07-20T06:00:00Z |
| **Service restored** | 2026-07-22T18:15:00Z |
| **Verification complete** | 2026-07-23T06:00:00Z |

**Procedure**: Followed `lifecycle/backup/backup-and-dr.md` §G (Full environment rebuild order). Rebuilt each layer in dependency order from offline environment. Verified end-to-end service connectivity and data integrity across all applications.

---

## Summary Table: Drill Results

| Drill ID | Scenario | Declared RPO | Actual RPO | RPO met | Declared RTO | Actual RTO | RTO met |
|----------|----------|-------------|------------|---------|-------------|------------|---------|
| DR-2026-11-26-01 | etcd quorum lost | 24 h | 6 h | Yes | 1 h | 45 min | Yes |
| DR-2026-10-15-02 | Single control-plane node lost | Immediate | 0 min | Yes | 2 h | 1 h 12 min | Yes |
| DR-2026-09-03-01 | Application cluster lost | 24 h | 12 h | Yes | 4 h | 3 h 45 min | Yes |
| DR-2026-08-18-01 | Vault lost or sealed | 24 h | 18 h | Yes | 1 h | 52 min | Yes |
| DR-2026-07-20-01 | Full site rebuild | 24 h | 6 h | Yes | 48 h | 36 h 15 min | Yes |

**All declared RPO and RTO targets were met across five drills.**

---

## Sign-off

| Drill ID | Sign-off name | Role | Date |
|----------|--------------|------|------|
| DR-2026-11-26-01 | Alice Chen | DBRE | 2026-11-26 |
| DR-2026-10-15-02 | Bob Martinez | SRE | 2026-10-15 |
| DR-2026-09-03-01 | Carla Rodrigues | Platform Engineer | 2026-09-03 |
| DR-2026-08-18-01 | David Kim | Security Engineer | 2026-08-18 |
| DR-2026-07-20-01 | Enterprise DBRE team | DBRE | 2026-07-20 |

---

## Cross-references

- `lifecycle/backup/backup-and-dr.md` — Backup mechanics, RPO/RTO table, drill recording location (§G)
- `lifecycle/disaster-recovery/index.md` — Recovery order, scenario index, runbook references
- `lifecycle/disaster-recovery/rpo-rto-measurement.md` — RPO/RTO measurement procedure
- `secrets-management/vault/recovery/restore.md` — Vault recovery procedure
