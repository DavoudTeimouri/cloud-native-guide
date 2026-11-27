# Cleanup Manifest — Repository Consolidation

Date: 2026-11-27
Repository: DavoudTeimouri/cloud-native-guide
Branch: fix/mkdocs-documentation-site

## Purpose

Record all project-owned files consolidated from outside the canonical repository path, what was moved, regenerated, retained, and deleted.

## Canonical Repository Path

`/workspace/project/github/public-repository/cloud-native-guide/`

## Files Moved Into Canonical Repository

### From Phase Worktrees

| Source | File | Action | Reason |
|--------|------|--------|--------|
| cloud-native-guide.phase6 (untracked) | kubespray/auto-test-offline-deployment.md | Copied | Kubespray offline deployment procedure not in canonical repo |

### From Release Artifacts (`/workspace/release-artifacts/`)

| Source Directory | Files Copied | Destination |
|-----------------|--------------|-------------|
| TASK-PARALLEL-EXECUTION/ | 7 .md files | docs/release-artifacts/parallel-execution/ |
| TASK-008.6-kanban-board/ | 11 .md files | docs/release-artifacts/kanban-board/ |
| TASK-007.*/ (phases 3-8) | 56 .md files | docs/release-artifacts/task-reports/ |
| TASK-008.*/ (0-7, except 008.6) | 4 .md files | docs/release-artifacts/task-reports/ |
| TASK-STATUS-AUDIT-* / TASK-STATUS-REVIEW-* | 10 .md files | docs/release-artifacts/status-review/ |

Total release-artifact docs copied: 88 files

## Files Retained Outside (Protected)

| Path | Reason |
|------|--------|
| /workspace/project/github/public-repository/cloud-native-infra/ | Repository 2 — ABSOLUTELY PROTECTED, not touched |
| /workspace/project/github/public-repository/cloud-native-guide-next/ | Migration source repository — not part of this project |
| /workspace/release-artifacts/backup-cloud-native-guide-worktree-*/ | Backup artifact — preserved per deletion rules |
| /workspace/release-artifacts/cloud-native-guide-*.zip | Build artifacts — preserved |
| /workspace/release-artifacts/daily-reports/ | Shared workspace — preserved |
| /workspace/release-artifacts/offline-site/ | Build output — preserved |
| /workspace/release-artifacts/source-bundle/ | Build artifact — preserved |
| /data/kanban.db | Kanban database — cleaned, not deleted |
| /data/projects.db | Projects database — preserved |
| /data/config.yaml | Hermes configuration — preserved |

## Files Deleted Outside

None yet — external files remain in place pending verification that all required content exists in Repository 1.

## Kanban DB State

Project: cloud-native-stack
Total tasks: 170
Status distribution: To be cleaned/organized

## Next Steps

1. Verify all external project content is in Repository 1
2. Clean up Kanban DB (organize tasks, remove stale entries)
3. Remove confirmed project-specific temporary files from outside canonical path
4. Commit consolidated changes
5. Push branch and create/update PR

## Repository 2 Protection

Repository 2 (`cloud-native-infra`) was verified clean before and after this consolidation. No files were modified, created, or deleted in Repository 2.