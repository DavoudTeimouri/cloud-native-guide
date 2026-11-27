# TASK 007.3 — Reconciliation Roadmap

**Task:** Parallel Content Reconciliation & Dependency Analysis
**Scope:** Phased reconciliation plan (read-only — no implementation)
**Prerequisite:** TASK 007.2 preservation complete (archive branch + local backup verified)

## Phase 0 — Prerequisite Preservation & Safety Checks (Complete)

| Item | Status |
|------|--------|
| Original repo HEAD verified: `7c40489c` | Verified |
| Archival remote branch `archive/integration-reconcile-remote-content` = `7c40489c` | Verified (TASK 007.2) |
| Local backup with checksums at `/workspace/release-artifacts/backup-cloud-native-guide-worktree-20261126T070617Z/` | Verified (TASK 007.2) |
| No git operations performed during analysis | Verified |
| PR #2, GitHub Pages, repo metadata unchanged | Verified |

**Note:** Integration branch HEAD advanced to `...b7d70b8c54c21457a2` after archive push. Archival branch preserves `...b3e7e6407c16419717`. Reconcile this delta before merging.

## Phase 1 — Git Safety & Branch Setup

1. Create isolated worktree for reconciliation work (do not modify original dirty worktree).
2. Branch from `origin/main` (`ebbafc2aa`) — do not modify `main`, `task-007-migration-publication`, or `archive/*`.
3. Verify archival branch still points to `7c40489c` (immutable recovery reference).
4. Confirm working tree dirtiness (8 tracked + 6 untracked) is preserved in original worktree.

**Git safety:** No force push, no history rewrite, no branch deletion, no PR #2 merge.

## Phase 2 — Dependency Cluster Reconciliation (in order)

### Group 1 — Site Generation Pipeline (Cluster A)
Files: `.github/workflows/site.yml`, `scripts/build_site.py`, `scripts/check_links.py`, `scripts/validate_catalog.py`, `scripts/acceptance_status.py`, `tests/test_repo_tools.py`, `tests/test_site_render.py`, `catalog/catalog.json`, `catalog/exports.json`, `catalog/upgrades.json`, `compatibility/version-matrix.md`

**Actions:**
- Resolve 6 conflict files in this group (site.yml, catalog.json, exports.json, upgrades.json, version-matrix.md, build_site.py, check_links.py, validate_catalog.py, test_repo_tools.py — actually 9 of the 20 conflicts)
- Run `build_site.py --check` to verify data.json staleness
- Run `validate_catalog.py` after catalog changes
- Run `check_links.py` — target 0 broken links
- Run `tests/test_repo_tools.py` — all tests pass

**Validation:** CI pipeline (`site.yml`) runs end-to-end without failure.

### Group 2 — ADRs (Cluster E)
Files: `decisions/ADR-0004`, `ADR-0015`, `ADR-0015-linux-directory-integration`, `ADR-0028`, `ADR-0029`, `ADR-0030`, `ADR-0031`

**Actions:**
- Consolidate ADR-0004 + ADR-0028 (load-balancing overlap) with cross-reference
- Preserve ADR-0016/0025 (not in conflict set; already consistent)
- Verify `gen_adrs.py` consistency with ADR files

**Validation:** No contradictory ADRs; ADR-0016/0025/0015 consistency confirmed.

### Group 3 — Security/Identity (Cluster D)
Files: `identity/directory-integration.md`, `identity/sssd-realmd.md`, `secrets-management/pki/index.md`, `secrets-management/pki/root-ca-rotation.md`, `secrets-management/vault/vault-architecture.md`, `security/host-baseline.md`, `service-mesh/evaluation.md`, `management-cluster/rancher/rancher.md`

**Actions:**
- Decide on `identity/sssd-realmd.md` (deleted on integration; do not restore unless user approves)
- Resolve `identity/directory-integration.md` conflict
- Verify Vault BSL 1.1 licensing check date recorded in version-matrix.md
- Confirm ADR-0016/0025 consistency with identity content

**Validation:** No secrets published; ADR consistency; security risks documented.

### Group 4 — Kubernetes/Lifecycle (Cluster B)
Files: `kubespray/kubespray-deployment.md`, `lifecycle/backup/backup-and-dr.md`, `lifecycle/disaster-recovery/index.md`, `lifecycle/upgrades/upgrade-procedures.md`, `kubernetes/control-plane/index.md`, `kubernetes/addons/cert-manager.md`, `kubernetes/networking/coredns-forwarding.md`, `kubernetes/node-resource-reservation.md`, `kubernetes/security/security-controls.md`

**Actions:**
- Resolve kube_version pin contradiction (v1.31.x vs 1.36.5)
- Resolve Rook/Ceph version mismatch (v18.2.x vs Tentacle 20.2.4)
- Verify OIDC CA cert provisioning design

**Validation:** Version pins align with version-matrix.md; upgrade procedures reference valid catalog/upgrades.json flows.

### Group 5 — Networking/External LB (Cluster C)
Files: `network-matrix/external-load-balancer.md`, `network-matrix/cloud-native-dmz.md`, `network-matrix/network-communication-matrix.md`, `network-matrix/port-requirements.md`, `manifests/external-lb/*` (6 files), `management-cluster/rancher/rancher.md`

**Actions:**
- Resolve external-load-balancer.md conflict
- Verify manifests match documented design (HAProxy recommended, unicast VRRP peers)
- Confirm Tier 1/2/3 LB architecture

**Validation:** Config files consistent with documentation; VRRP unicast peers for DMZ.

### Group 6 — Site Modules (Cluster F)
Files: `site/modules/00-10/*/app.js` + `index.html` (22 files), `site/modules/module.css`, `site/app.js`, `site/data.json`, `site/styles.css`, `site/index.html`, `site/README.md`, `site/adoption.md`

**Actions:**
- Rebuild `site/data.json` via `build_site.py` after catalog changes
- Verify all 10 modules render correctly
- Run `test_site_render.py`

**Validation:** Site build passes; all modules have page coverage; no broken links.

### Group 7 — Platform, GPU/AI, Requirements (Clusters G, H, I)
Files: `platform/backstage/catalog-info.yaml`, `platform/golden-paths/cloudnative-service.json`, `scripts/golden_path.py`, `scripts/cluster_methods.py`, `scripts/sync_github.py`, `scripts/verify_github.py`, `scripts/gh_refs.py`, `scripts/compare_tree.py`, `scripts/report_adoption.py`, `gpu-ai/monitoring/index.md`, `gpu-ai/scheduling/index.md`, `requirements/component-guide-backlog.md`, `requirements/implementation-roadmap.md`, `requirements/technology-selection-matrix.md`, `PLAN-future.md`, `CONTRIBUTING.md`, `README.md`, `ansible/README.md`, `automation/ansible/*`, `automation/awx/index.md`, `automation/terraform/vsphere-example.md`, `architecture/*`, `offline-artifacts/artifact-matrix.md`

**Actions:**
- Preserve 78 unique files as-is
- Adapt 12 files (golden-path platform config, README table formatting, CONTRIBUTING consolidation)
- Consolidate 3 files (ADR-0004+ADR-0028 cross-reference)

**Validation:** No duplication; cross-references intact.

## Phase 3 — Conflict-Resolution Checkpoints (User Approval Required)

| Checkpoint | Conflicts | Decision needed |
|------------|-----------|-----------------|
| CP1 | catalog/catalog.json | Which version's entries for shared components |
| CP2 | compatibility/version-matrix.md | Integration (10-26) vs origin/main (10-17) check date |
| CP3 | identity/sssd-realmd.md | Restore deleted doc or keep integration deletion |
| CP4 | service-mesh/istio/istio-deployment.md | Contradicts ADR-0030 (no service mesh initially)? |
| CP5 | kubespray-deployment.md kube_version | v1.31.x vs 1.36.5 — which is authoritative |
| CP6 | rook-ceph.md ceph image | v18.2.x vs Tentacle 20.2.4 — align with Rook release notes |
| CP7 | All 14 remaining conflicts | 3-way merge strategy per file |

## Phase 4 — Validation After Each Group

| Validation | Command | Target |
|------------|---------|--------|
| Catalog integrity | `python3 scripts/validate_catalog.py` | All tests pass |
| Link check | `python3 scripts/check_links.py` | 0 broken links |
| Site build staleness | `python3 scripts/build_site.py --check` | Not stale |
| Repo tools tests | `python3 tests/test_repo_tools.py` | All pass |
| Site render | `python3 tests/test_site_render.py` | Renders without error |
| Acceptance status | `python3 scripts/acceptance_status.py` | Gate summary clean |

## Phase 5 — Final Integration Validation

1. Full CI pipeline (`site.yml`) runs end-to-end.
2. `build_site.py --check` confirms data.json is current.
3. `validate_catalog.py` passes all assertions.
4. `check_links.py` reports 0 broken links.
5. All `tests/test_repo_tools.py` tests pass.
6. No contradictory ADRs; ADR-0016/0025/0015 consistent.
7. Version pins in all docs match version-matrix.md.
8. No secrets or credentials in any file.

## Phase 6 — Publication Readiness Checks

1. Archival branch `archive/integration-reconcile-remote-content` intact as immutable reference.
2. Local backup intact and checksum-verified.
3. Original dirty worktree unchanged (8 tracked + 6 untracked).
4. PR #2 still open, unmerged (`91d3f22`).
5. Default branch still `main` (`ebbafc2aa`).
6. No GitHub Pages or repository metadata changes.

## Recommended Commit Strategy

Small, auditable commits rather than one large migration:
- Commit per dependency cluster (Groups 1-7 above)
- Conventional commit format (`docs:`, `fix:`, `chore:`)
- Each commit independently revertible
- No squashing of the 80 original integration commits

## Stop Conditions

- Archival branch diverges from expected SHA
- Cannot create isolated worktree
- User has not approved conflict resolutions at CP1-CP7
- Any validation fails (build, links, catalog, tests)

**STOP — Roadmap complete. Do not start TASK 007.4 or any reconciliation without explicit user authorization.**
