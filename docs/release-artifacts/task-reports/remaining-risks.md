# TASK 007.5 — Phase 1 Remaining Risks

**Task:** Controlled Content Reconciliation, Phase 1
**Scope:** Risks and next steps after Phase 1

## 1. Delegation Blocker

| Risk | Description | Mitigation |
|------|-------------|------------|
| Agency Router delegation non-functional | `tool_call`/`agency_agents_delegate` failed on all attempts (JSON parse error) | All 5 specialist workstreams completed by Main as substitute. Retry delegation when tool is functional. |

## 2. Validation Limitations

| Risk | Description | Mitigation |
|------|-------------|------------|
| Full repo validation suite not run | `build_site.py`, `validate_catalog.py`, `check_links.py`, `test_repo_tools.py` not executed | Not applicable — selected files don't touch catalog, scripts, tests, workflows, or site data |
| `management-cluster/keycloak/keycloak.md` not verified | Optional SSO prerequisite referenced in awx/index.md | Not a blocking dependency; awx/index.md notes it as conditional ("if SSO is required") |

## 3. Cross-Reference Risk

| Risk | Description | Mitigation |
|------|-------------|------------|
| awx/index.md references 4 external docs | All 4 verified to exist on destination (origin/main) except keycloak.md | 3 of 4 confirmed; keycloak.md is optional |

## 4. Future Content Group Selection

The next content group should be selected from the remaining 91 unique files in `unique-files-inventory.csv`, applying the same Phase 2 criteria:

- Classified as `preserve` (or low-risk adapt)
- No dependency on any of the 20 conflicting files
- No dependency on scripts, catalog schemas, generated site data, or workflows not yet reconciled
- No conflict with PR #2 content
- No unnecessary duplication

Candidates that may require special attention:
- Files depending on `catalog/catalog.json` (e.g., `scripts/cluster_methods.py`, `site/app.js`, `site/data.json`, `site/modules/*`) — blocked until catalog is reconciled
- Files depending on `compatibility/version-matrix.md` (e.g., `kubespray/kubespray-deployment.md`, `requirements/technology-selection-matrix.md`) — blocked until version matrix is reconciled
- `identity/sssd-realmd.md` — deleted on integration, conflict file; do not select
- `secrets-management/vault/vault-architecture.md` — BSL license unverified; requires legal review before selection

## 5. Branch Status

| Item | Value |
|------|-------|
| Local branch `task-007.5-phase1-content` | Exists at commit `e454a46` |
| Push to GitHub | Not performed (forbidden) |
| Worktree path | `/workspace/project/github/public-repository/cloud-native-guide.phase1` |

## 6. Proposed Next Step (Requires Authorization)

Select the next small content group from the remaining 91 unique files and repeat Phase 2-6. Do not start without explicit user authorization.

**STOP after Phase 1. No push, no merge, no second content group without explicit user authorization.**
