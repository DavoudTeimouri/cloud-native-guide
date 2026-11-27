# TASK 007.8 — Phase 4 Remaining Inventory

**Task:** Controlled Content Reconciliation, Phase 4
**Scope:** Remaining unique files and recommended next task

## 1. Remaining Unique Files (from TASK 007.3 inventory)

Total unique files: 93
Reconciled in Phase 1: 2 (`automation/awx/index.md`, `platform/backstage/catalog-info.yaml`)
Reconciled in Phase 2: 2 (`lifecycle/backup/backup-and-dr.md`, `lifecycle/disaster-recovery/index.md`)
Reconciled in Phase 3: 2 (`offline-artifacts/artifact-matrix.md`, `architecture/00-overview.md`)
Reconciled in Phase 4: 3 (`scripts/compare_tree.py`, `scripts/gh_refs.py`, `scripts/verify_github.py`)
**Remaining: 85**

## 2. Remaining Files by Disposition (from inventory)

| Disposition | Remaining count |
|-------------|-----------------|
| preserve | ~82 |
| adapt | 3 (CONTRIBUTING.md, README.md, platform/golden-paths/cloudnative-service.json) |
| consolidate | 2 (ADR-0004, ADR-0028 — overlap with each other) |

## 3. High-Coupling Clusters to Avoid Until Dependencies Reconciled

| Cluster | Files | Blocker |
|---------|-------|---------|
| Catalog system | `catalog/catalog.json`, `catalog/exports.json`, `catalog/upgrades.json`, `scripts/cluster_methods.py`, `scripts/golden_path.py`, `site/app.js`, `site/data.json`, `site/modules/*` | All in conflict list or depend on conflict files |
| Kubespray deployment | `kubespray/kubespray-deployment.md` | coupled_to_conflict=Yes (version pin contradiction: v1.31.x vs 1.36.5) |
| External LB | `network-matrix/external-load-balancer.md`, `manifests/external-lb/*` | coupled_to_conflict=Yes |
| Version matrix | `compatibility/version-matrix.md` | In conflict list |
| Identity | `identity/directory-integration.md`, `identity/sssd-realmd.md` | In conflict list |
| Scripts | `scripts/build_site.py`, `scripts/check_links.py`, `scripts/validate_catalog.py`, `scripts/acceptance_status.py` | In conflict list; drive site generation pipeline |

## 4. Recommended Next Phase 5 Candidates

Candidates that are `preserve`, `coupled_to_conflict=No`, no dependency on conflict files/scripts/catalog/site data:

| File | Lines | Type | Notes |
|------|-------|------|-------|
| `scripts/compare_tree.py` | — | Already reconciled in Phase 4 |
| `scripts/gh_refs.py` | — | Already reconciled in Phase 4 |
| `scripts/verify_github.py` | — | Already reconciled in Phase 4 |
| `architecture/02-deployment-topology.md` | ~ | Documentation | Modification to existing file, low risk |
| `architecture/03-failure-domains.md` | ~ | Documentation | Modification to existing file, low risk |
| `automation/ansible/ansible-structure.md` | ~ | Documentation | Standalone |
| `automation/ansible/index.md` | ~ | Documentation | Standalone |
| `requirements/component-guide-backlog.md` | ~ | Documentation | Backlog |
| `requirements/implementation-roadmap.md` | ~ | Documentation | Backlog |
| `requirements/technology-selection-matrix.md` | ~ | Documentation | References version-matrix.md |
| `security/host-baseline.md` | ~ | Documentation | Standalone |
| `service-mesh/evaluation.md` | ~ | Documentation | References ADR-0030 |
| `secrets-management/pki/index.md` | ~ | Documentation | PKI architecture; BSL license unverified — legal review first |
| `tests/acceptance/README.md` | ~ | Documentation | References acceptance_status.py |

**Recommended Phase 5 group:** `architecture/02-deployment-topology.md` + `architecture/03-failure-domains.md` + `security/host-baseline.md` — all low-risk standalone documentation modifications, no conflict dependencies.

## 5. Files Requiring Special Attention Before Selection

| File | Reason |
|------|--------|
| `secrets-management/vault/vault-architecture.md` | BSL 1.1 license unverified — legal review required |
| `kubespray/kubespray-deployment.md` | Version pin contradiction (v1.31.x vs 1.36.5) — architectural decision needed |
| `compatibility/version-matrix.md` | In conflict list; version pin contradictions |
| `identity/sssd-realmd.md` | Deleted on integration; do not restore without user approval |
| `service-mesh/istio/istio-deployment.md` | Potential contradiction with ADR-0030 (no service mesh initially) |
| `kubespray/kubespray-deployment.md` | In conflict list |

## 6. Stop Condition

**STOP after Phase 4.** No push, merge, PR modification, or Phase 5 without explicit user authorization.

**Recommended next action:** User authorization to proceed to Phase 5 with candidate group (e.g., `architecture/02-deployment-topology.md`, `architecture/03-failure-domains.md`, `security/host-baseline.md`).
