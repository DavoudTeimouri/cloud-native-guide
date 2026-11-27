# TASK 007.8 — Phase 4 Selected Files and Rationale

**Task:** Controlled Content Reconciliation, Phase 4
**Scope:** File selection and dependency justification

## 1. Selected Files (3)

| # | Source Path | Type | Lines | Disposition | Reason for Selection |
|---|-------------|------|-------|-------------|---------------------|
| 1 | `scripts/compare_tree.py` | Python script | 55 | preserve | Standalone GitHub API utility — compares remote GitHub tree with local directory, reports remote commit SHA, blob count, local file count, and differences |
| 2 | `scripts/gh_refs.py` | Python script | 48 | preserve | Standalone GitHub API utility — lists GitHub branches, tags, and releases via API; includes delete-repo subcommand (explicit CLI only, irreversible) |
| 3 | `scripts/verify_github.py` | Python script | 38 | preserve | Standalone GitHub API utility — verifies GitHub repo branch content via API, lists root entries, commits, repo metadata, topics |

## 2. Independence Verification

| Condition | compare_tree.py | gh_refs.py | verify_github.py |
|-----------|-----------------|------------|-----------------|
| Classified as preserve | Yes | Yes | Yes |
| `coupled_to_conflict` = No | Yes | Yes | Yes |
| No dependency on 20 conflicting files | Yes | Yes | Yes |
| No dependency on scripts/catalog/site data/workflows | Yes | Yes | Yes |
| Not in cluster_methods.py → catalog.json → site/data.json → site/modules/* chain | Yes | Yes | Yes |
| Not in PR #2 changed files | Yes | Yes | Yes |
| Not pure addition (both exist on origin/main)? | N/A — pure addition | N/A — pure addition | N/A — pure addition |
| Technically consistent with doc architecture | Yes | Yes | Yes |
| Suitable for meaningful validation | Yes | Yes | Yes |
| Excluded from 20 conflict paths | Yes | Yes | Yes |

## 3. Source and Destination Status

| File | Exists on origin/main? | Exists on integration? | Action |
|------|------------------------|------------------------|--------|
| `scripts/compare_tree.py` | No | Yes | Pure addition — copy source content |
| `scripts/gh_refs.py` | No | Yes | Pure addition — copy source content |
| `scripts/verify_github.py` | No | Yes | Pure addition — copy source content |

## 4. Dependencies Checked

| File | Referenced paths | Exist on destination? | Notes |
|------|-----------------|----------------------|-------|
| `scripts/compare_tree.py` | None (stdlib + GitHub API) | N/A | Standalone; uses urllib.request for API calls, os.walk for local dir |
| `scripts/gh_refs.py` | None (stdlib + GitHub API) | N/A | Standalone; uses urllib.request for API calls |
| `scripts/verify_github.py` | None (stdlib + GitHub API) | N/A | Standalone; uses urllib.request for API calls |

**Key findings:**
- None of the 3 scripts reference catalog/catalog.json, exports.json, upgrades.json
- None reference scripts/build_site.py, scripts/check_links.py, scripts/validate_catalog.py, scripts/acceptance_status.py
- None reference tests/test_repo_tools.py or tests/test_site_render.py
- None reference .github/workflows/site.yml or .github/workflows/static-validation.yml
- None reference site/data.json or site/modules/*
- All three use only Python stdlib (json, os, subprocess, sys, urllib.request)
- All three read `$GITHUB_TOKEN` from environment at runtime (no hardcoded secrets)

## 5. Why Safe for Phase 4

- All 3 files are classified `preserve` with `coupled_to_conflict=No`
- None of the 3 files are in the 20 known conflict paths
- None of the 3 files were changed by PR #2
- None of the 3 files touch scripts, catalog JSON, tests, workflows, or generated site data
- All 3 are pure additions (do not exist on origin/main)
- All 3 are stdlib-only Python utilities with no external dependencies
- All 3 are standalone with no mutual dependencies
- Small scope (3 files, 141 insertions) enables complete validation
- gh_refs.py contains delete-repo subcommand but requires explicit CLI invocation; not auto-executed

## 6. Deferred Issues

| Issue | Disposition |
|-------|-------------|
| gh_refs.py contains delete-repo subcommand | Documented as explicit CLI only; not auto-executed; not a blocker for preservation |
| All scripts require $GITHUB_TOKEN at runtime | Expected external dependency; not embedded in scripts; not a blocker |

**No repository state was changed beyond the Phase 4 worktree during selection.**
