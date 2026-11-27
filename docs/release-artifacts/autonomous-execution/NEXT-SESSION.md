# NEXT-SESSION — Cloud-Native Stack Migration

**Resume point:** TASK 007.11 Phase 7 — create Phase 7 worktree from latest Phase 6 commit 51da5642c5b743f9de3914f67da98f1de79cba5c

**All work committed** — no uncommitted changes.

**Next task candidates:**
1. architecture/01-logical-diagram.md — standalone documentation, low risk
2. decisions/ADR-0015-identity-integration-layer.md — ADR, depends on ADR-0031
3. decisions/ADR-0031-identity-integration-with-ldap-ad-federation.md — ADR, depends on ADR-0015
4. kubernetes/addons/cert-manager.md — K8s addon, depends on kubernetes/control-plane/index.md
5. kubernetes/control-plane/index.md — K8s control plane, depends on kubernetes/addons/*

**Preconditions to verify at session start:**
- Phase 6 commit 51da564 preserved exactly
- Phase 5 commit 7ee2d04 preserved exactly
- Remote main still at ebbafc2aa
- Original integration HEAD still at 7c40489c
- Original working tree still has 8 tracked + 6 untracked
- Archival branch still at 7c40489c
- Backup checksums still valid
- PR #2 still open, unmerged

**Remaining inventory:** 56 unique files
**Estimated phases remaining:** ~8 (7 files per phase at current rate)
