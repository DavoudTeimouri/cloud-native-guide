# TASK 008.2 — Catalog Conflict Analysis

**Task:** TASK 008.2 — Catalog Conflict Analysis

## 1. Conflict Overview

The catalog conflict involves three files that exist on the integration branch but are deleted on origin/main:

| File | Status on integration | Status on origin/main | Type |
|------|----------------------|----------------------|------|
| catalog/catalog.json | EXISTS (2936 lines) | DELETED | Pure addition on integration |
| site/app.js | EXISTS (1712 lines) | DELETED | Pure addition on integration |
| site/data.json | EXISTS (4223 lines) | DELETED | Pure addition on integration |

## 2. Conflict Classification

**Not a true merge conflict.** These files are unique additions to the integration branch. They do not exist on origin/main, so there is no conflicting content to merge.

The "conflict" classification in the TASK-007.3 inventory was based on:
- site/app.js: "conflicts on site.yml workflow" — site.yml is in the 20 conflicting files and site/app.js may reference it
- site/data.json: "must be rebuilt after catalog changes" — depends on catalog/catalog.json

However, since all three files (catalog/catalog.json, site/app.js, site/data.json) are pure additions on integration, they can be safely copied to the worktree without git merge conflicts.

## 3. Downstream Dependencies

| File | Depends On | Dependency Status |
|------|-----------|-------------------|
| site/app.js | catalog/catalog.json, site/data.json | Both are pure additions on integration |
| site/data.json | catalog/catalog.json, scripts/build_site.py | catalog/catalog.json is pure addition; build_site.py is on origin/main |
| scripts/cluster_methods.py | catalog/catalog.json | Pure addition on integration |
| lifecycle/upgrades/upgrade-procedures.md | catalog/upgrades.json | Pure addition on integration |

## 4. Resolution

**Unblock P10-14 (site/app.js), P10-15 (site/data.json), P09-18 (upgrade-procedures.md), P09-19 (cluster_methods.py):**

All four tasks involve files that are pure additions on the integration branch. They can be safely copied to the worktree without conflict concerns.

**Keep P09-17 (kubespray-deployment.md) blocked:**

kubespray/kubespray-deployment.md is modified on both branches with genuine content differences:
- Integration removed navigation links and OIDC CA certificate section
- origin/main has different content
- Requires human architectural decision

## 5. Validation

After copying, each file should be validated with:
- `git diff --check` (whitespace)
- File existence check
- Content diff vs integration branch (should match exactly)
- For .py files: `python3 -m py_compile`

## 6. Regression Risk

Low. These files are additive — they don't modify existing origin/main content. The only risk is cross-branch consistency (e.g., site/app.js referencing site.yml which may differ between branches), but this is a Review concern, not a copy concern.
