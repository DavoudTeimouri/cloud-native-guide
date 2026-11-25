# Section 2: Upgrade Lifecycle Architecture

## 10-Phase Reusable Lifecycle Model

| Phase | Name | Description | Key Deliverables | Approval Point |
|-------|------|-------------|------------------|----------------|
| 1 | **Version & Dependency Inventory** | Maintain a canonical inventory of every installed component, its current version, and all direct/transitive dependencies. Cross-reference with the compatibility matrix (`compatibility/version-matrix.md`). | Component list, version numbers, dependency graph, inventory source of truth. | Inventory owner signs off; SRE validates completeness. |
| 2 | **Compatibility Verification** | Verify the target version is compatible with all dependent components. Check the version matrix, release notes, and supported upgrade paths. Note any skew limits (e.g., Kubernetes one-minor-skew, Ceph major-version constraints). | Compatibility sign-off matrix, known blockers, required intermediate upgrades. | Release engineer approves; SRE flags unsupported paths. |
| 3 | **Upgrade Planning** | Define the upgrade scope, sequence, rollback strategy, downtime window, and resource requirements. Document the canary strategy and success criteria. | Upgrade plan document, rollback procedure, downtime estimate, canary targets. | Change advisory board (CAB) or equivalent approves the plan. |
| 4 | **Pre‑Upgrade Validation** | Run baseline health checks against the current state. Confirm node readiness, API server and etcd health, CNI/CSI status, and PDB compliance. | Health‑check report, baseline metrics, identified risks. | SRE leads the validation; ops confirms no blocking issues. |
| 5 | **Backup & Recovery Readiness** | Verify that complete, verified backups exist for etcd, Kubernetes resources, databases, and stateful volumes. Test restore in a sandbox if possible. | Backup artifacts, restore test results, recovery time objective (RTO) confirmation. | Backup owner signs off; SRE confirms RTO/RPO targets. |
| 6 | **Staging / Lab Validation** | Execute the upgrade on a staging copy of the production inventory (or a dedicated lab cluster). Verify all post‑upgrade checks pass before touching production. | Staging upgrade results, issue log, verified post‑upgrade state. | Release engineer approves staging results; SRE signs off on “green” staging. |
| 7 | **Controlled Production Rollout** | Execute the upgrade per the approved sequence. Use canary nodes/pools first, then roll out to the full fleet. Monitor golden signals and error‑budget consumption in real time. | Rollout execution log, canary verification checkpoints, real‑time SLO tracking. | CAB or on‑call approves each stage transition; SRE monitors error budget. |
| 8 | **Post‑Upgrade Verification** | Run the full post‑upgrade checklist: node readiness, API server & etcd health, CNI/CSI health, storage health, pod availability, PDB compliance, DNS/Networking, admission policy health, monitoring/alert delivery, logging, registry access, identity/secrets, GitOps sync, and application‑level validation. | Post‑upgrade health‑check report, issue tracker entries, remediation actions. | SRE leads verification; ops confirms all checks pass. |
| 9 | **Monitoring & Stabilization** | Monitor golden signals (latency, error rate, traffic, saturation) for the stabilization window (typically 30 days or per SLO window). Confirm error‑budget consumption is within acceptable limits. | Monitoring dashboards, alerting stability report, error‑budget consumption chart. | SRE declares stabilization; CAB closes the change if budget is healthy. |
| 10 | **Documentation & Inventory Updates** | Update the version inventory, compatibility matrix, artifact matrix, and all runbooks to reflect the new versions. Record the actual downtime, deviations, and lessons learned. | Updated `compatibility/version-matrix.md`, updated `offline-artifacts/artifact-matrix.md`, change record. | Documentation owner signs off; change record archived. |

---

## Upgrade Type Definitions & Differences

| Type | Definition | Scope | Reversibility | Typical Downtime | When to Choose |
|------|------------|-------|---------------|------------------|----------------|
| **upgrade** | General term for moving from one version to another. | Varies by component. | Depends on component. | Varies | Covers all deliberate version moves. |
| **patch update** | Incremental fix within the same minor version (e.g., v1.28.3 → v1.28.8). | Bug fixes, security patches. | Usually yes, in‑place. | Minimal (often zero‑downtime). | When CVE or bug fixes are needed; safest path. |
| **minor version update** | Next minor release within the same major series (e.g., v1.28 → v1.29). | New features, minor API changes, deprecations. | Usually yes, with rollback backup. | Short (control‑plane first, then workers). | When new minor features are needed but major API breaks are avoidable. |
| **major version update** | Crossing a major boundary (e.g., v1.28 → v1.30, or Ceph Luminous → Nautilus). | Significant API changes, removed/renamed resources, new dependency requirements. | Generally **no** across the major boundary; rollback requires restore from backup. | Longer (planned window, canary required). | When major new capabilities are required; requires full compatibility verification. |
| **migration** | Moving to a different platform or technology (e.g., on‑prem → cloud, Kubernetes → OpenShift, Helm 3 → Helm 4, Cephadm → Rook). | Entire stack or application data move. | Often partially reversible; depends on data format. | Significant (cutover window). | When platform strategy changes or legacy support ends. |
| **reinstallation** | Fresh install of the same or new version, wiping and rebuilding the environment. | Full rebuild from scratch. | Yes — new cluster. | Full deployment window. | When upgrade path is unsupported, debt has accumulated, or a clean slate is desired. |
| **rollback** | Deliberate return to a previous version after a failed upgrade. | Reversal of the upgrade sequence. | Yes, if backup/restore is available; otherwise no. | Varies (restore time). | When post‑upgrade verification fails and the error budget is exceeded. |
| **disaster recovery** | Recovery from a catastrophic failure (cluster loss, region outage, data corruption). | Full or partial restoration from backups. | Yes — restores to last known‑good state. | Depends on backup scope and RTO. | When the cluster is unrecoverable via normal means. |

---

## Responsibilities & Approval Points by Phase

| Phase | Primary Owner | Supporting Roles | Approval Authority |
|-------|---------------|------------------|-------------------|
| 1 — Version & Dependency Inventory | Inventory / Config management team | SRE, Release engineering | Config management lead signs off; SRE validates. |
| 2 — Compatibility Verification | Release engineering | SRE, Component owners | Release engineer approves compatibility sign‑off. |
| 3 — Upgrade Planning | Release engineering | SRE, CAB, Component owners | CAB or equivalent change advisory board approves the plan. |
| 4 — Pre‑Upgrade Validation | SRE | Ops, Component owners | SRE leads; ops confirms no blocking issues. |
| 5 — Backup & Recovery Readiness | Backup / Recovery team | SRE | Backup owner signs off; SRE confirms RTO/RPO. |
| 6 — Staging / Lab Validation | Release engineering | SRE, QA, Component owners | Release engineer approves staging “green” results. |
| 7 — Controlled Production Rollout | On‑call SRE | CAB, Release engineering, Ops | On‑call approves each stage transition; CAB closes the change. |
| 8 — Post‑Upgrade Verification | SRE | Ops, Component owners | SRE signs off on all checks passing. |
| 9 — Monitoring & Stabilization | SRE | Observability team | SRE declares stabilization; CAB closes if budget healthy. |
| 10 — Documentation & Inventory Updates | Documentation / Config management team | SRE, Release engineering | Documentation owner signs off; change record archived. |

---

## Glossary of Terms

- **Error budget** — The remaining reliability budget within an SLO; consuming it defers feature work to reliability fixes.
- **Canary** — A small subset of production nodes or workloads upgraded first to validate the upgrade before full rollout.
- **Skew** — The version difference between components; Kubernetes supports one minor version of skew, Ceph and Istio have explicit paths.
- **Change advisory board (CAB)** — Governance body that approves changes based on risk classification and error‑budget impact.