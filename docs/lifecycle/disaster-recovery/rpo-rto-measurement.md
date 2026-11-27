# RPO/RTO Measurement Procedure

## A. Purpose and scope

Document how to measure actual Recovery Point Objective (RPO) and Recovery Time Objective (RTO) during backup drills, where to record results, and how to compare against declared targets.

Referenced by `lifecycle/backup/backup-and-dr.md` and `lifecycle/disaster-recovery/index.md`.

## B. Definitions

| Term | Definition | How to measure |
|------|-----------|----------------|
| RPO | Maximum acceptable data loss (time) | Time between last successful backup and failure point |
| RTO | Maximum acceptable downtime (time) | Time from disaster declaration to verified service restoration |

## C. Measurement procedure

### 1. Declare the drill

Record the drill start time, scenario, and declared targets:

| Field | Value |
|-------|-------|
| Drill ID | Unique identifier (e.g., DR-2026-11-26-01) |
| Scenario | e.g., "Single control-plane node lost", "etcd quorum lost", "Full site rebuild" |
| Declared RPO | From `lifecycle/backup/backup-and-dr.md` table |
| Declared RTO | From `lifecycle/backup/backup-and-dr.md` table |
| Declared by | Person authorizing the drill |
| Start time | ISO 8601 timestamp |

### 2. Execute the recovery procedure

Follow the applicable runbook from `lifecycle/disaster-recovery/index.md`:

| Scenario | Runbook |
|----------|---------|
| Single control-plane node lost | `kubernetes/control-plane/index.md` §Backup |
| etcd quorum lost | `kubernetes/control-plane/index.md` §Backup |
| Management cluster lost | `lifecycle/disaster-recovery/management-cluster.md` |
| Application cluster lost | `lifecycle/disaster-recovery/application-cluster.md` |
| Vault lost or sealed | `secrets-management/vault/recovery/restore.md` |
| Storage cluster degraded | `storage/ceph/cephadm-deployment.md` §Recovery |
| Full site rebuild | `lifecycle/backup/backup-and-dr.md` §G |

### 3. Record timestamps

| Event | Timestamp | Notes |
|-------|-----------|-------|
| Disaster declared | T0 | Start of the drill |
| Last successful backup | T1 | From backup logs/monitoring |
| Recovery started | T2 | First recovery command executed |
| Service restored | T3 | All health checks pass |
| Verification complete | T4 | Verified with test transactions |

### 4. Calculate RPO and RTO

| Metric | Formula | Result |
|--------|---------|--------|
| Actual RPO | T0 − T1 | Time since last successful backup |
| Actual RTO | T3 − T0 | Time from declaration to restoration |

### 5. Compare against declared targets

| Metric | Declared | Actual | Met? |
|--------|----------|--------|------|
| RPO | From backup-and-dr.md | Actual RPO | Yes/No |
| RTO | From backup-and-dr.md | Actual RTO | Yes/No |

### 6. Record results

Append to `lifecycle/backup/backup-and-dr.md` §G (or a dedicated drill log):

```markdown
## Drill: DR-2026-11-26-01

| Field | Value |
|-------|-------|
| Scenario | etcd quorum lost |
| Declared RPO | 24 h |
| Declared RTO | 1 h |
| Actual RPO | 6 h |
| Actual RTO | 45 min |
| RPO met | Yes |
| RTO met | Yes |
| Issues | None |
| Next drill | 2026-12-26 |
```

## D. Drill cadence

| Component | Frequency | Declared RPO | Declared RTO |
|-----------|-----------|-------------|-------------|
| etcd snapshot restore | Quarterly | 24 h | 1 h |
| Velero restore (K8s resources + PVs) | Quarterly | 24 h | 4 h |
| Ceph/RBD restore | Quarterly | 24 h | 4 h |
| Vault raft snapshot restore | Quarterly | 24 h | 1 h |
| Full site rebuild | Annually | 24 h | Depends on scope |

## E. Evidence requirements

For each drill, retain:

1. Drill declaration record (scenario, targets, authorizer)
2. Recovery procedure logs (commands executed, output)
3. Timestamp records (T0-T4)
4. Comparison table (declared vs actual)
5. Issues found and corrective actions
6. Sign-off from the person who ran the drill

## F. Cross-references

- `lifecycle/backup/backup-and-dr.md` — Backup mechanics, RPO/RTO table, drill recording location
- `lifecycle/disaster-recovery/index.md` — Recovery order, scenario index, runbook references
- `kubernetes/control-plane/index.md` §Backup — etcd snapshot procedure
- `secrets-management/vault/recovery/restore.md` — Vault recovery procedure
