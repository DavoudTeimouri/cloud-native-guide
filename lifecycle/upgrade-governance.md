# Section 14: Upgrade Governance and Change Management

## Definitions

| Term | Definition |
|------|------------|
| **Upgrade ownership** | The team or individual responsible for planning, executing, and signing off on the upgrade. Primary ownership lies with the release engineering team; component owners retain accountability for their subsystem. |
| **Change window** | A pre‑approved time interval during which upgrades may be performed without additional approval. Default windows: maintenance weekends (Saturday 02:00‑06:00 UTC), emergency windows require CAB approval. |
| **Risk classification** | Categorization of the upgrade based on potential impact to the error budget and service availability: `low`, `medium`, `high`, `critical`. Classification drives approval level and required evidence. |
| **Approval criteria** | Checklist of conditions that must be met before a upgrade stage may proceed. See § Approval Points per Phase (upgrade-strategy.md) for the 10‑phase model. |
| **Maintenance notifications** | Communicative outreach to all stakeholders (on‑call, SRE, product, customers) at T‑48h, T‑24h, T‑2h, and post‑completion. Templates stored in `operations/operational-readiness.md`. |
| **Pre‑upgrade evidence** | The documented artifact bundle required before any upgrade may begin: inventory sign‑off, compatibility matrix entry, backup verification, canary test results, and risk‑classification approval. |
| **Execution log** | Immutable record (via change‑record template below) of every step performed, timestamps, responsible party, and outcome during the upgrade. |
| **Rollback decision deadline** | The latest time by which a rollback must be decided and initiated. Typically set at 80% of the allocated change window; after this point, only disaster‑recovery paths are authorized. |
| **Post‑upgrade acceptance** | Formal sign‑off that all post‑upgrade checks pass, the error budget is healthy, and the change record is complete. SRE declares stabilization; CAB closes the change. |
| **Version inventory updates** | Automatic and manual updates to `compatibility/version-matrix.md` and `offline-artifacts/artifact-matrix.md` after a successful upgrade, including source URL and check date. |
| **Exception handling** | A documented process for proceeding despite a known risk or missing control. Requires CAB exception approval, a risk Acceptance of Record (AoR), and a defined expiration or re‑evaluation trigger. |

---

## Mandatory Controls vs Recommended Operational Practices

| Category | Controls | Description |
|----------|----------|-------------|
| **Mandatory** | **Backup before change** — A verified backup must exist and be test‑restored before any upgrade that modifies stateful data (K8s, Ceph, databases). | Not "a backup exists" — the backup must be confirmed valid, documented, and within RTO/RPO. |
| | **Compatibility verification** — The version‑matrix must be updated with the target version, source URL, and check date *before* the upgrade starts. | Prevents unsupported skew and unknown API‑breakage. |
| | **Rollback feasibility check** — Before the upgrade, explicitly state whether rollback is possible. If not, the change record must record the risk and obtain CAB approval. | Ensures no "surprise" rollback scenarios during execution. |
| | **Error‑budget accounting** — Consuming the error budget must be recorded; if budget would be exceeded, feature work is deferred to reliability fixes. | Drives the "ship if budget remains, fix if not" principle. |
| | **Canary first** — Every upgrade runs on a staging copy of the production inventory (or a canary node-pool) before production touch. | Validates the upgrade path in a controlled environment. |
| | **Execution log completed** — The change record template (below) must be filled in real‑time; incomplete logs are a compliance finding. | Provides audit trail and post‑mortem clarity. |
| | **Post‑upgrade acceptance sign‑off** — SRE and component owners must sign off that all checklist items pass before the change is closed. | Guaranteates no unresolved issues remain open. |
| **Recommended** | **Staging / lab validation** — Running the upgrade on a full‑stack lab cluster before production is best practice but may be waived for low‑risk patch updates with approved exceptions. | Speeds low‑risk changes but adds risk if skipped. |
| | **Extended monitoring window** — Monitoring for 30 days or two SLO windows beyond the upgrade is recommended for major version updates. | Catches latent issues that do not manifest immediately. |
| | **Change‑window flexibility** — If a business‑critical feature must ship outside the default window, an emergency CAB process may approve a narrow off‑hours window. | Provides agility at the cost of reduced review rigor. |
| | **Post‑upgrade documentation draft** — Draft the documentation updates during the upgrade; finalize within 48 hours of acceptance. | Prevents documentation drift and keeps the inventory current. |

---

## Upgrade Change Record Template

> **Fill this template in real‑time during the upgrade.** Do not complete after the fact. Store the completed record in `lifecycle/change-records/` with a timestamped filename.

```markdown
# Upgrade Change Record

**Date:** YYYY‑MM‑DD  
**Upgrade ID:** `prefix-YYYYMMDD-N` (increment per change)  
**Change Window:** [start‑timestamp] – [end‑timestamp]  
**Risk Classification:** low / medium / high / critical  
**Error‑Budget Impact:** % consumed during/after upgrade (pre‑ and post‑upgrade values)  

## 1. Upgrade Scope
| Component | Current Version | Target Version | Type (upgrade/patch/minor/major/migration/reinstall/rollback/DR) | Reversible? |
|-----------|----------------|---------------|---------------------------------------------------------------|-------------|

## 2. Ownership
| Role | Name | Team | Contact |
|------|------|------|---------|
| Upgrade owner |  | Release Engineering |  |
| Component owners |  |  |  |
| SRE lead |  | SRE |  |
| CAB approver |  |  |  |

## 3. Pre‑Upgrade Evidence (check all that apply and attach links)
- [ ] Version & dependency inventory signed off (`inventory/` or config repo HEAD)
- [ ] Compatibility matrix updated with target version and check date
- [ ] Verified backup exists and test‑restore successful (backup‑id: ______)
- [ ] Canary/staging upgrade completed successfully (link to results)
- [ ] Rollback feasibility documented; if not reversible, CAB exception approved
- [ ] Error‑budget status recorded (pre‑upgrade: ____%, post‑upgrade target: ____%)
- [ ] Maintenance notifications sent (T‑48h, T‑24h, T‑2h templates used)

## 4. Execution Log (populate as steps complete)
| Step | Timestamp | Action | Outcome (pass/fail/blocked) | Notes |
|------|-----------|--------|-----------------------------|-------|
| 1 |  | Version inventory check |  |  |
| 2 |  | Compatibility verification |  |  |
| 3 |  | Backup verification |  |  |
| 4 |  | Canary/staging validation |  |  |
| 5 |  | Controlled rollout – step 1 |  |  |
| 6 |  | Controlled rollout – step 2 |  |  |
| … |  | … |  |  |

## 5. Post‑Upgrade Verification
| Check | Result | Evidence |
|-------|--------|----------|
| Node readiness (all Ready) |  |  |
| API server & etcd health |  |  |
| CNI health |  |  |
| CSI health |  |  |
| Storage health (PVs, Ceph) |  |  |
| Pod availability (no CrashLoopBackOff) |  |  |
| PDB compliance |  |  |
| DNS & networking |  |  |
| Admission policy health |  |  |
| Monitoring & alert delivery |  |  |
| Logging |  |  |
| Registry access |  |  |
| Identity & secrets |  |  |
| GitOps synchronization |  |  |
| Application‑level validation |  |  |

**Status:** `accepted` / `deferred` / `rollback initiated`  
**Rollback decision deadline met?** `yes` / `no`  
**Post‑upgrade acceptance sign‑off:** SRE lead __________, Component owner __________  

## 6. Version Inventory Updates
| Component | New Version | `version-matrix.md` updated? | `artifact-matrix.md` updated? | Check date |
|-----------|-------------|------------------------------|-------------------------------|------------|

## 7. Exception Handling (if applicable)
| Exception ID | Reason for exception | Approved by | Expiration / re‑evaluation date |
|--------------|----------------------|-------------|----------------------------------|

## 8. Lessons Learned
| Item | Action | Owner | Target date |
|------|--------|-------|-------------|
|  |  |  |  |
```

---

## Governance Flow Summary

```
               +----------------------+
               |  Initiate upgrade request |
               +----------+--------------+
                          |
                          v
    +-------------------+-------------------+
    |  Pre‑upgrade evidence package   |  (mandatory controls)
    +----------+----------+---------------+
               |              |
               v              v
    +-------------------+-------------------+
    |  CAB / Risk Approval         |  (approval criteria)
    +----------+----------+---------------+
               |              |
               v              v
    +-------------------+-------------------+
    |  Execution phase (10‑phase)   |  (canary → production)
    +----------+----------+---------------+
               |              |
               v              v
    +-------------------+-------------------+
    |  Post‑upgrade verification   |  (all checklists)
    +----------+----------+---------------+
               |              |
               v              v
    +-------------------+-------------------+
    |  Acceptance & closure       |  (SRE sign‑off, CAB close)
    +----------------------+--------------+
                          |
                          v
                +-------------------+
                | Version inventory |
                | updates + archival |
                +-------------------+
```

---

## Key Principles

1. **SLOs drive decisions** — If error budget remains, ship. If not, fix reliability first.
2. **Measure before optimizing** — No upgrade proceeds without baseline health‑check data.
3. **Automate toil, don't heroic through it** — If an upgrade step was done manually twice, script or automate it.
4. **Blameless culture** — Systems fail, not people. The change record documents what the system did, not who did it.
5. **Progressive rollouts** — Canary → percentage → full. Never big‑bang deploys for major or minor upgrades.