# TASK 007.3 — Conflict Analysis

**Task:** Parallel Content Reconciliation & Dependency Analysis
**Scope:** 20 conflict files (present in both integration diff and PR #2 diff)
**Status:** READ-ONLY analysis — no conflicts resolved

## Conflict Inventory

| # | File | Integration diff size | PR #2 diff size | Nature of conflict | User approval required? |
|---|------|----------------------|-----------------|-------------------|------------------------|
| 1 | `.github/workflows/site.yml` | 86 insertions | (PR#2 touches) | CI workflow for site generation; integration adds full site.yml, origin/main lacks it | Yes |
| 2 | `addons/platform-addons.md` | 250 insertions | (PR#2 touches) | K8s platform addons documentation | Yes |
| 3 | `catalog/catalog.json` | 2,936 insertions | (PR#2 touches) | Core catalog — version tracking, components, methods; highest conflict risk | Yes |
| 4 | `catalog/exports.json` | 624 insertions | (PR#2 touches) | Export templates for catalog rendering | Yes |
| 5 | `catalog/upgrades.json` | 124 insertions | (PR#2 touches) | Upgrade flow definitions | Yes |
| 6 | `compatibility/version-matrix.md` | 38 insertions, 9 deletions | (PR#2 touches) | Version compatibility matrix; check date differs (10-17 vs 10-26) | Yes |
| 7 | `identity/directory-integration.md` | 117 insertions | (PR#2 touches) | Application-layer identity via Keycloak | Yes |
| 8 | `identity/sssd-realmd.md` | 225 deletions | (PR#2 touches) | Host-level SSSD/realmd — deleted on integration, present on origin/main | Yes |
| 9 | `kubernetes/access/end-user-access.md` | 125 insertions | (PR#2 touches) | K8s end-user access documentation | Yes |
| 10 | `kubernetes/multiple-clusters.md` | 70 insertions | (PR#2 touches) | Multi-cluster management | Yes |
| 11 | `kubernetes/windows-workers.md` | 53 insertions | (PR#2 touches) | Windows worker nodes | Yes |
| 12 | `management-cluster/alternatives.md` | 60 insertions | (PR#2 touches) | Management cluster alternatives | Yes |
| 13 | `network-matrix/external-load-balancer.md` | 456 insertions | (PR#2 touches) | External load balancer architecture | Yes |
| 14 | `operating-systems/host-configuration.md` | 229 insertions | (PR#2 touches) | OS host configuration | Yes |
| 15 | `scripts/acceptance_status.py` | 112 insertions | (PR#2 touches) | Acceptance status validation script | Yes |
| 16 | `scripts/build_site.py` | 229 insertions | (PR#2 touches) | Site generation script | Yes |
| 17 | `scripts/check_links.py` | 92 insertions | (PR#2 touches) | Link checking script | Yes |
| 18 | `scripts/validate_catalog.py` | 521 insertions | (PR#2 touches) | Catalog validation script | Yes |
| 19 | `service-mesh/istio/istio-deployment.md` | 179 insertions | (PR#2 touches) | Istio service mesh deployment | Yes |
| 20 | `tests/test_repo_tools.py` | 420 insertions, 7 deletions | (PR#2 touches) | Repository tool tests | Yes |

## Per-Conflict Analysis

### 1. `.github/workflows/site.yml`
**Origin/main:** File does not exist (empty on origin/main side).
**Integration:** Full CI workflow — build_site.py → validate_catalog.py → check_links.py → test_repo_tools.py → test_site_render.py → upload-pages-artifact. Strict sequential chain with cancel-in-progress.
**Unique info in integration:** Complete site generation pipeline.
**Must not lose:** CI gating for stale site data; catalog integrity checks.
**Dependencies:** `scripts/build_site.py`, `scripts/validate_catalog.py`, `scripts/check_links.py`, `tests/test_repo_tools.py`, `tests/test_site_render.py`.
**Recommended strategy:** Adopt integration version (origin/main lacks it entirely).
**User approval:** Yes — adds CI infrastructure.

### 2. `addons/platform-addons.md`
**Origin/main:** Pre-PR#2 version.
**Integration:** 250 insertions — expanded platform addons documentation.
**Recommended strategy:** Compare line-by-line; adopt integration version if it supersedes, otherwise 3-way merge.
**User approval:** Yes.

### 3. `catalog/catalog.json` (HIGHEST RISK)
**Origin/main:** Base catalog.
**Integration:** 2,936 insertions — major catalog expansion with version-tracking logic, components, methods.
**Unique info in both:** Each branch has unique catalog entries.
**Must not lose:** Version alias mappings (34 VERSION_ALIASES), component defaults, page coverage.
**Dependencies:** `scripts/build_site.py`, `scripts/validate_catalog.py`, `catalog/exports.json`, `catalog/upgrades.json`, `site/data.json`.
**Recommended strategy:** 3-way merge with catalog schema validation; run `validate_catalog.py` after merge.
**User approval:** Yes — critical data file.

### 4. `catalog/exports.json`
**Integration:** 624 insertions — export templates.
**Recommended strategy:** 3-way merge; validate export template placeholders resolve.
**User approval:** Yes.

### 5. `catalog/upgrades.json`
**Integration:** 124 insertions — 8 upgrade flows.
**Recommended strategy:** 3-way merge; verify upgrade flow gates reference valid ids.
**User approval:** Yes.

### 6. `compatibility/version-matrix.md`
**Origin/main:** Check date 2026-10-17.
**Integration:** Check date 2026-10-26. Same structure; 38 insertions / 9 deletions.
**Must not lose:** Verified version pins; official source URLs; check date semantics (Last updated vs Last verified).
**Recommended strategy:** Use integration version (newer check date) but preserve any origin/main-only verified rows.
**User approval:** Yes — version pins affect deployments.

### 7. `identity/directory-integration.md`
**Integration:** Application-layer identity via Keycloak; no host SSSD/realmd.
**Recommended strategy:** Adopt integration version (architecturally superior — recovery independence).
**User approval:** Yes — security architecture decision.

### 8. `identity/sssd-realmd.md`
**Origin/main:** Full SSSD/realmd host-level directory integration doc (225 lines).
**Integration:** Deleted.
**Must not lose:** Decision rationale if host-level join is ever needed as exception.
**Recommended strategy:** Do not restore (integration explicitly removed it per ADR-0015). Archive content in analysis only.
**User approval:** Yes — removes documentation.

### 9. `kubernetes/access/end-user-access.md`
**Integration:** 125 insertions — end-user access guide.
**Recommended strategy:** 3-way merge; check for duplicate content with directory-integration.md.
**User approval:** Yes.

### 10. `kubernetes/multiple-clusters.md`
**Integration:** 70 insertions — multi-cluster management.
**Recommended strategy:** 3-way merge.
**User approval:** Yes.

### 11. `kubernetes/windows-workers.md`
**Integration:** 53 insertions — Windows worker nodes.
**Recommended strategy:** 3-way merge; verify Windows support status (conditional per TASK 004-P11.1).
**User approval:** Yes.

### 12. `management-cluster/alternatives.md`
**Integration:** 60 insertions — management cluster alternatives.
**Recommended strategy:** 3-way merge.
**User approval:** Yes.

### 13. `network-matrix/external-load-balancer.md`
**Integration:** 456 insertions — external LB architecture (HAProxy vs Nginx, VRRP, keepalived).
**Must not lose:** Tier 1/2/3 LB design; unicast VRRP peers recommendation.
**Dependencies:** `manifests/external-lb/*`, `network-matrix/cloud-native-dmz.md`, `network-matrix/network-communication-matrix.md`.
**Recommended strategy:** 3-way merge; adopt integration version (more detailed).
**User approval:** Yes.

### 14. `operating-systems/host-configuration.md`
**Integration:** 229 insertions — OS host configuration.
**Recommended strategy:** 3-way merge; verify OL8/RHEL8 kernel 4.18 notes.
**User approval:** Yes.

### 15. `scripts/acceptance_status.py`
**Integration:** 112 insertions — acceptance status validation.
**Recommended strategy:** 3-way merge; integrate into CI if not already.
**User approval:** Yes.

### 16. `scripts/build_site.py`
**Integration:** 229 insertions — site generation script.
**Must not lose:** `--check` mode for stale data detection.
**Dependencies:** `catalog/catalog.json`, `compatibility/version-matrix.md`, `site/data.json`.
**Recommended strategy:** 3-way merge; verify build_site --check works after merge.
**User approval:** Yes.

### 17. `scripts/check_links.py`
**Integration:** 92 insertions — link checker.
**Recommended strategy:** 3-way merge; verify backtick-wrapped filename parsing issue noted in TASK 005-P11.8.
**User approval:** Yes.

### 18. `scripts/validate_catalog.py`
**Integration:** 521 insertions — catalog validation (assert-based).
**Must not lose:** test_docs_exist, test_pages, test_exports_render_cleanly, test_upgrade_flows.
**Dependencies:** `site/data.json` (generated by build_site.py).
**Recommended strategy:** 3-way merge; run validation after merge.
**User approval:** Yes.

### 19. `service-mesh/istio/istio-deployment.md`
**Integration:** 179 insertions — Istio deployment.
**Recommended strategy:** 3-way merge; check consistency with ADR-0030 (no service mesh initially).
**User approval:** Yes — potential contradiction with ADR-0030.

### 20. `tests/test_repo_tools.py`
**Integration:** 420 insertions, 7 deletions — repo tool tests.
**Recommended strategy:** 3-way merge; verify test coverage for build_site.py, validate_catalog.py.
**User approval:** Yes.

## Conflict Clusters Requiring Coordinated Resolution

| Cluster | Files | Reason |
|---------|-------|--------|
| **CI/Site pipeline** | .github/workflows/site.yml, scripts/build_site.py, scripts/check_links.py, scripts/validate_catalog.py, tests/test_repo_tools.py | Sequential pipeline; break at any step cascades |
| **Catalog system** | catalog/catalog.json, catalog/exports.json, catalog/upgrades.json | Interdependent JSON; schema changes propagate |
| **Identity/security** | identity/directory-integration.md, identity/sssd-realmd.md | Architectural decision (host SSO vs app-layer Keycloak) |
| **External LB** | network-matrix/external-load-balancer.md, manifests/external-lb/* | Config files reference each other |

## Unresolved Items Requiring User Approval

All 20 conflicts require explicit user approval before resolution. Key decisions:
1. Which version's catalog entries to keep for shared components in catalog/catalog.json
2. Whether to use integration's newer version-matrix.md (check date 10-26) or origin/main's (10-17)
3. Whether to permanently delete identity/sssd-realmd.md
4. Whether istio-deployment.md contradicts ADR-0030 (no service mesh initially)
5. Version pin contradictions: kubespray-deployment.md (v1.31.x) vs version-matrix.md (1.36.5); rook-ceph.md (ceph v18.2.x) vs Tentacle 20.2.4

**STOP — No conflicts resolved in this task.**
