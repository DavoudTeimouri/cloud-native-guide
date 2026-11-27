# Disaster-Recovery Exercises

## Overview

This document outlines practical disaster-recovery (DR) exercises for the cloud-native platform, covering cluster failure simulation, recovery runbooks, RTO/RPO validation, and sign-off procedures. All exercises are designed to be repeatable, measurable, and documented so that a real incident is never the first time the team runs a DR playbook.

---

## Exercise 1: Cluster Failure Simulation

### Purpose

Validate that a primary node failure can be recovered automatically (or manually) within the target RTO without data loss, and that the system converges to a healthy state.

### Prerequisites

- Patroni/orchestrator-managed PostgreSQL cluster with etcd consensus.
- A sync replica promoted to primary via automated failover.
- Stable VIP/service‑discovery endpoint that apps follow (no hard‑coded primary addresses).
- Fencing mechanism (STONITH or equivalent) to prevent split‑brain.

### Steps

1. **Record baseline metrics**
   - Replication lag = 0 (or < threshold).
   - Connection pool status.
   - Current primary address.

2. **Simulate primary failure**
   - Halt the primary node (e.g., `kill -9` on the process, or poweroff the VM).
   - Observe the orchestrator health checks and consensus.
   - Verify a new primary is elected within **RTO ≤ 30 minutes** (target).

3. **Validate application failover**
   - Ensure traffic routes to the new primary via the VIP/service‑discovery endpoint.
   - Perform a smoke write/read test.

4. **Fence the old primary** (if it comes back)
   - Confirm the old primary cannot accept writes after promotion.

5. **Record outcomes**
   - Time from failure to new primary elected.
   - Any write loss (compare WAL positions before/after).
   - Application errors during switchover.

### Post‑exercise

- Update the runbook with any observed gaps.
- Schedule the next failure‑simulation drill (recommended: quarterly).

---

## Exercise 2: Recovery Runbook

### Purpose

Provide a step‑by‑step procedure to restore from a base backup + WAL replay to a target timestamp, verifying point‑in‑time recovery (PITR).

### Prerequisites

- Latest physical base backup stored in object storage.
- Continuous WAL/archive shipping enabled.
- Throw‑away deployment environment (e.g., a separate Kubernetes cluster or VM pool).

### Steps

1. **Spin up a throw‑away instance**
   - Provision a fresh PostgreSQL instance (same version as production).

2. **Restore the base backup**
   - `pg_restore` / `pg_basebackup` to copy the base backup into the instance.

3. **Replay WAL to target timestamp**
   - `pg_waldump` + `pg_recvlogical` or `restore_command` to replay WAL up to the desired point‑in‑time.

4. **Run integrity checks**
   - Row‑count comparisons against known tables.
   - checksum verification (pg_checksum, pg_tarcheck, or custom query set).
   - Smoke query set: primary key lookups, aggregate checks.

5. **Record measured RTO**
   - Wall‑clock time from start (step 1) to successful smoke queries.
   - Alert if RTO exceeds the **30‑minute budget**.

6. **Tear down the throw‑away instance**.

### Post‑exercise

- If the restore failed or exceeded RTO, document the root cause and adjust backup frequency, compression, or archival strategy.
- Ensure the next automated restore test is scheduled (recommended: monthly).

---

## Exercise 3: RTO/RPO Validation

### Purpose

Measure actual Recovery Time Objective (RTO) and Recovery Point Objective (RPO) against the targets defined in the reliability charter.

### RPO Target: ≤ 1 minute (WAL archived continuously)

1. **Trigger a simulated data loss event**
   - Delete or corrupt a known row in the primary.

2. **Perform point‑in‑time recovery to a timestamp just before the loss**
   - Follow the Recovery Runbook steps.

3. **Compare data state**
   - Verify the restored data matches the pre‑loss state within the RPO window.

4. **Record RPO metric**
   - Actual minutes of potential data loss = `time_of_loss - restored_timestamp`.

### RTO Target: ≤ 30 minutes (measured by actual restore drill)

1. **Execute the Recovery Runbook** (Exercise 2) on a scheduled basis.

2. **Measure wall‑clock time** from start of base‑backup restore to final smoke‑query success.

3. **Compare against budget**
   - If RTO > 30 min, investigate: backup size, WAL volume, network throughput, instance provisioning speed.

4. **Report** the measured RTO/RPO in the reliability dashboard.

### Automation

- The team should configure an automated monthly restore test that posts results to the dashboard and raises an alert if thresholds are breached.

---

## Exercise 4: Sign‑Off Procedures

### Purpose

Ensure every completed DR exercise is formally signed off before the runbook is considered current.

### Sign‑Off Checklist (per exercise)

| Item | Completed? | Comments |
|---|---|---|
| Failure‑simulation or restore drill executed | ☐ | |
| Measured RTO ≤ 30 min (or documented exception) | ☐ | |
| Measured RPO ≤ 1 min (or documented exception) | ☐ | |
| All integrity checks passed (row counts, checksums) | ☐ | |
| Fencing/STONITH verified (if applicable) | ☐ | |
| Application smoke test passed | ☐ | |
| Runbook updated with any gaps found | ☐ | |
| Team lead approval | ☐ | |
| Date of sign‑off | ☐ | |

### Approval Workflow

1. **Exercise leader** fills the checklist and notes any issues.
2. **Team lead** reviews the checklist and either approves or requests remediation.
3. **Documentation owner** merges runbook updates into the main branch.
4. **Record** the sign‑off in the `DR_EXERCISES_LOG` (e.g., a YAML or markdown table in the repo) for auditability.

### Frequency

- **Cluster failure simulation**: quarterly.
- **Recovery runbook / RTO‑RPO validation**: monthly (automated) + quarterly (live drill).
- **Sign‑off**: immediately after each exercise; the runbook is not considered current until all items are green.

---

## Additional Notes

- **Never treat an untested backup as a recovery plan.** The first restore test must never occur during a real incident.
- **Replication lag is a correctness issue.** Before any failover, confirm lag < threshold; otherwise promote‑a‑lagging replica leads to write loss.
- **Connection pooling is mandatory.** A pooler (PgBouncer/ProxySQL) with per‑service caps prevents connection‑exhaustion‑induced outages during DR events.
- **Capacity forecast.** Storage growth, IOPS ceilings, and connection headroom should be projected ahead of any DR scale‑up.

---

*Document maintained by the Database Reliability Engineer team. Review quarterly or after any significant topology change.*