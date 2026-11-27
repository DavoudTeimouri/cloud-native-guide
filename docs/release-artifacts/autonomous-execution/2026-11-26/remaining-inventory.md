# Remaining Inventory — 2026-11-26

**Total unique files from TASK 007.3 inventory:** 93

**Reconciled to date:**
- Phase 1: 2 files (automation/awx/index.md, platform/backstage/catalog-info.yaml)
- Phase 2: 2 files (lifecycle/backup/backup-and-dr.md, lifecycle/disaster-recovery/index.md)
- Phase 3: 2 files (offline-artifacts/artifact-matrix.md, architecture/00-overview.md)
- Phase 4: 3 files (scripts/compare_tree.py, scripts/gh_refs.py, scripts/verify_github.py)

**Remaining: 85 files**

**By disposition (from inventory):**
- preserve: ~82
- adapt: 3 (CONTRIBUTING.md, README.md, platform/golden-paths/cloudnative-service.json)
- consolidate: 2 (ADR-0004, ADR-0028 — overlap with each other)

**High-coupling clusters to avoid until dependencies reconciled:**
- Catalog system: catalog/catalog.json, catalog/exports.json, catalog/upgrades.json, scripts/cluster_methods.py, scripts/golden_path.py, site/app.js, site/data.json, site/modules/*
- Kubespray deployment: kubespray/kubespray-deployment.md (coupled_to_conflict=Yes, version pin contradiction)
- External LB: network-matrix/external-load-balancer.md, manifests/external-lb/* (coupled_to_conflict=Yes)
- Version matrix: compatibility/version-matrix.md (in conflict list)
- Identity: identity/directory-integration.md, identity/sssd-realmd.md (in conflict list)

**Recommended Phase 5 group:**
- architecture/02-deployment-topology.md
- architecture/03-failure-domains.md
- security/host-baseline.md

All three are low-risk standalone documentation modifications, no conflict dependencies.

**Files requiring special attention:**
- secrets-management/vault/vault-architecture.md: BSL 1.1 license unverified — legal review required
- kubespray/kubespray-deployment.md: Version pin contradiction (v1.31.x vs 1.36.5) — architectural decision needed
- identity/sssd-realmd.md: Deleted on integration; do not restore without user approval
- service-mesh/istio/istio-deployment.md: Potential contradiction with ADR-0030 (no service mesh initially)
