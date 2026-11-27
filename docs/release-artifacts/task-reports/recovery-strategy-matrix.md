# TASK 007.4 — Recovery Strategy Decision Matrix

**Task:** Git History Integrity, Archive Delta Reconciliation & Recovery Planning
**Scope:** Read-only comparison of recovery strategies (NOT executed)

## Strategies Compared

### Strategy A — Fast-forward archival update

**Viability:** NOT VIABLE as described. The archival remote branch (`7c40489c`) already equals the local integration HEAD (`7c40489c`). There is nothing to fast-forward — they are identical. A fast-forward push would be a no-op.

| Assessment | Rating |
|------------|--------|
| Data-loss risk | None (no-op) |
| History preservation | Preserved (already archived) |
| Recovery complexity | Minimal |
| Auditability | High |
| GitHub publication risk | None |
| PR #2 compatibility | N/A |
| User authorization required | No (already done) |

### Strategy B — New archival branch for newer HEAD

**Viability:** NOT NEEDED. Current integration HEAD == archival SHA. No newer HEAD exists that isn't already archived. Creating a second archival branch would be redundant.

| Assessment | Rating |
|------------|--------|
| Data-loss risk | None |
| History preservation | Preserved |
| Recovery complexity | Low (but redundant) |
| Auditability | Medium (duplicate refs could confuse) |
| GitHub publication risk | Low |
| PR #2 compatibility | N/A |
| User authorization required | No (not needed) |

### Strategy C — Independent recovery references (RECOMMENDED)

Preserve all existing references as independent, immutable recovery points without merging or rewriting any history:

1. **`archive/integration-reconcile-remote-content` = `7c40489c`** — GitHub archival of integration branch (complete, immutable)
2. **`backup/local-history-before-online-reset` = `be42bd3f`** — Local backup branch (same tree as `890a351c`, ancestor of remote main)
3. **`refs/original/refs/heads/master` = `890a351c`** — Dangling filter-branch backup (same tree as `be42bd3f`, not in any branch)
4. **Local backup at `/workspace/release-artifacts/backup-cloud-native-guide-worktree-20261126T070617Z/`** — Working tree patch + untracked copies + verified manifest
5. **Local `main` = `3a72a3b`** — Preserved as-is (diverged from remote main)
6. **Remote `main` = `ebbafc2aa`** — Preserved as-is (disjoint from local main)

| Assessment | Rating |
|------------|--------|
| Data-loss risk | Lowest — all commits and working-tree changes have multiple recovery references |
| History preservation | Highest — no history is rewritten, merged, or deleted |
| Recovery complexity | Low — each reference is independently checkable |
| Auditability | High — all SHAs documented, all checksums verified |
| GitHub publication risk | Low — no force push, no branch deletion, no metadata changes |
| PR #2 compatibility | High — PR #2 left untouched |
| User authorization required | No (all references already exist) |

### Strategy D — Keep histories separate until content reconciliation

Maintain the current state: disjoint histories (integration vs origin/main, local main vs remote main), no merge, no cherry-pick, no content copying. Content reconciliation proceeds later via controlled file-level copy, not history integration.

| Assessment | Rating |
|------------|--------|
| Data-loss risk | Low |
| History preservation | High |
| Recovery complexity | Medium — requires future content-level reconciliation |
| Auditability | High — clear separation of concerns |
| GitHub publication risk | Low — no remote writes |
| PR #2 compatibility | High — PR #2 unaffected |
| User authorization required | Yes (to proceed to content reconciliation) |

## Recommendation

**Strategy C — Independent recovery references** is recommended because:

1. All committed history (80 integration commits) is archived on GitHub at `archive/integration-reconcile-remote-content = 7c40489c`
2. All uncommitted working-tree changes (8 tracked + 6 untracked) are backed up with verified SHA256 checksums
3. Additional safety references exist (`be42bd3f`, `890a351c`) as redundant recovery points
4. No history is rewritten, merged, or deleted — fully compliant with all safety rules
5. PR #2 remains untouched and open
6. No GitHub publication risk — no force push, no branch deletion

Strategy D is compatible with C — keeping histories separate is the natural continuation of C. Future content reconciliation (TASK 007.5+) should proceed via controlled file-level copy from the archival/reference branches, not via history merge.

## Strategies NOT Recommended

- **Fast-forward merge of integration into origin/main:** Not possible — disjoint histories (no merge base). Would require `--allow-unrelated-histories` with high conflict risk in shared files (README.md, catalog/catalog.json, version-matrix.md, .github/workflows/*).
- **Cherry-pick all 80 integration commits:** Would lose logical commit grouping and dependency chains (e.g., `cluster_methods.py → catalog.json → site/data.json → site/modules/*`).
- **Rebase integration onto origin/main:** Would rewrite the 80 local commits, breaking the archival remote ref.
- **Force push any branch:** Explicitly forbidden by safety rules.

## Conditions That Would Change the Recommendation

| Condition | Impact |
|-----------|--------|
| Archival remote SHA changes (new commit on integration not yet pushed) | Would require Strategy B (new archival ref) or re-push |
| Local backup becomes invalid or incomplete | Would require regenerating backup before any future work |
| PR #2 is merged or closed | Would change PR #2 compatibility assessment |
| Remote main is force-pushed or rewritten | Would invalidate remote main observations; requires re-verification |

**No strategy is executed in this task.** All are read-only assessments.
