# Risks and Blockers

**Source:** Read-only audit of Kanban DB, repository, agent state, cron job state, and validation results.

---

## Unresolved Architectural Decisions

### R-1: Kubespray Version Pin Contradiction (Pre-existing, Blocker)

**Description:** Three sources disagree on Kubespray/Kubernetes version pins:
- `kubespray/kubespray-deployment.md`: kube_version v1.31.x, containerd 1.7.x
- `kubespray/group-vars-template.md`: v1.36.5, containerd 2.3.7
- `compatibility/version-matrix.md`: v1.36.5 default, v1.34.0 minimum

**ADR-0026** enforces a hard floor of v1.34.0 for Kubespray release-2.32. v1.31.x is below this floor.

**Impact:** Cannot proceed with Kubespray deployment validation without resolving which version is authoritative. This blocks E02 (Kubespray Engineering) tasks that depend on a stable version target.

**Required:** Human architectural decision. Cannot be resolved autonomously.

**Evidence:** `kubespray/kubespray-deployment.md`, `kubespray/group-vars-template.md`, `compatibility/version-matrix.md`, ADR-0026. Documented in `/workspace/release-artifacts/TASK-008.6-kanban-board/evidence/kubespray-version-decision.md`.

---

## Blocker 1: No Hermes-Ultra Independent Review (Blocking Local Commits)

**Description:** Per project policy (ASK 008.6 §9, ASK 008.7 §8), no local commits can be made until an independent Hermes-Ultra Review succeeds. Maximum one review per calendar day.

**Current state:** `last_review_date: null`, `reviews_today: 0`. Hermes-Ultra agent is in "standby" status and has never been invoked.

**Impact:** All 27 new repository files created during TASK-008.7 remain uncommitted. No work can be promoted from working tree to committed state.

**Required:** Run Hermes-Ultra independent review on the 27 new files. After successful review, local commits may be created.

**Evidence:** `organization-state.json` (last_review_date: null), `daily-report-2026-11-27.md` §6.

---

## Blocker 2: Supervisor Does Not Dispatch to Agents

**Description:** cronjob_manage job `4a751a9bb83f` fires `supervisor.py` every 30 minutes, but supervisor.py does not call `agency_agents_delegate`. It only queries Kanban, performs backlog discovery, and logs state.

**Impact:** No autonomous agent execution is occurring. The "continuous engineering loop" is not actually looping — it only discovers backlog and waits for manual delegation.

**Evidence:** `supervisor.py` source code (lines 315-358) — `main()` function contains no `agency_agents_delegate` call. `supervisor.log` shows only discovery cycles, no delegation.

**Required:** Update supervisor.py to delegate Ready tasks to domain agents via `agency_agents_delegate`, respecting WIP limits.

---

## Blocker 3: Kanban-Done Does Not Equal Repository-Done

**Description:** 72 of 98 Done tasks have assignee "None" and no task_events execution history. These were created during ASK 008.6 before TASK-008.7 agent delegation. Repository files exist for many, but the link between Kanban task and actual file is not recorded.

**Impact:** Cannot verify which Kanban-completed tasks actually have corresponding repository implementation. The board shows 100% completion but repository evidence is incomplete for 72 tasks.

**Evidence:** Kanban DB query — 72 tasks with assignee="None", 0 task_events for pre-TASK-008.7 tasks.

**Required:** Reconcile Done tasks with actual repository files. For each Done task, verify the corresponding file exists and record the link in task_events if missing.

---

## Blocker 4: Validation Failure — Trailing Whitespace

**Description:** test_repo_tools.py reports 1 FAIL: trailing whitespace in 5 newly created files:
- `management-cluster/argocd/fleet-argocd-decision-matrix.md:40`
- `offline-artifacts/offline-upgrade-test.md:25,28,36`
- `kubespray/offline-deployment-test.md:5`

**Impact:** These files fail structural validation. Per project policy, tasks should not be marked Done until validation passes.

**Evidence:** Direct execution of `python3 tests/test_repo_tools.py` — FAIL on "docs are structurally sane".

**Required:** Fix trailing whitespace in 5 files.

---

## Blocker 5: 12-Hour Execution Target Not Met

**Description:** ASK 008.6 §7 requires at least 720 minutes (12 hours) of productive execution per cycle. Current state: 150 productive minutes (21% of target).

**Impact:** Cycle cannot be reported as complete per ASK 008.6 definition of success.

**Evidence:** `organization-state.json` — productive_work_minutes: 150, target_minutes: 720, percent_complete: 21.

**Required:** Continue execution until 720 minutes are verified with timestamps and execution evidence.

---

## Blocker 6: No Hermes-Ultra Review Means No Commits

**Description:** Related to Blocker 1 but distinct — the absence of any independent review means the entire TASK-008.7 body of work (27 files, 26 agent-delegated tasks) cannot be committed to the repository.

**Impact:** Work exists only in the untracked working tree. If the session is lost, this work is not committed to Git.

**Evidence:** `git status` shows ~100 untracked files, 0 commits made during TASK-008.7.

**Required:** Hermes-Ultra review → local commits.

---

## Summary: Top Unresolved Blockers (Prioritized)

| # | Blocker | Severity | Required Action |
|---|---------|----------|-----------------|
| 1 | No Hermes-Ultra review → no local commits | High | Run Hermes-Ultra review on 27 new files |
| 2 | Supervisor doesn't delegate to agents | High | Update supervisor.py to call agency_agents_delegate |
| 3 | Kubespray version pin contradiction | High | Human architectural decision (v1.31.x vs v1.36.5) |
| 4 | Kanban-Done ≠ Repository-Done (72 tasks) | Medium | Reconcile Done tasks with repository files |
| 5 | Trailing whitespace in 5 files | Medium | Fix whitespace, re-run test_repo_tools.py |
| 6 | 12-hour target not met (150/720 min) | Medium | Continue execution to 720 minutes |
