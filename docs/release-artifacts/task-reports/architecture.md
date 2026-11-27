# TASK 008.0 — Current vs Target Architecture

**Task:** TASK 008.0 Persistent Autonomous Engineering Runtime — Architecture

## 1. Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Agent Session                     │
│  (single session, in-memory state, no persistence across    │
│   restarts, no durable task queue, no automated dispatch)   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Kanban DB (/data/kanban.db) — EXISTS but EMPTY             │
│  tables: tasks, task_links, task_runs, task_events,         │
│          task_comments, task_attachments, kanban_notify_subs│
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Agency Agents Router — ENABLED                             │
│  agency_agents_delegate works as direct function call       │
│  25+ specialist agents discovered across divisions          │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Cron — AVAILABLE but 0 jobs configured                     │
│  cronjob_manage works as direct function call               │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Git worktrees (phase1-6) — all committed, clean            │
│  Original repo preserved (integration/reconcile-remote-content)│
└─────────────────────────────────────────────────────────────┘
```

**Current limitations:**
- No durable task population — Kanban DB has 0 tasks
- No automated dispatch — tasks executed manually one at a time
- No parallel execution — single workstream at a time
- No dependency-aware scheduling — no task_links populated
- No daily Review automation — Review done manually via Hermes-Ultra delegation
- No daily report automation — reports written manually
- No cross-session persistence of execution state beyond Kanban DB and file reports

## 2. Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Persistent Autonomous Engineering Runtime      │
└─────────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Kanban DB    │ │  Cron Scheduler│ │  File Reports  │
│  (durable     │ │  (daily Review │ │  (audit trail)  │
│   task queue) │ │   + reporting) │ │                  │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
                  ┌───────────────┐
                  │ Orchestrator  │
                  │ (Hermes-Main) │
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Worker 1     │ │  Worker 2     │ │  Worker N     │
│  (Hermes-     │ │  (Hermes-     │ │  (Hermes-     │
│   Worker)     │ │   Worker)     │ │   Worker)     │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Agency Agents Router (delegation to specialists)           │
│  Git worktrees (isolated execution)                         │
│  Independent Review (Hermes-Ultra)                          │
└─────────────────────────────────────────────────────────────┘
```

## 3. Architecture Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Durable task queue | Kanban DB (SQLite) at /data/kanban.db | Persistent task storage, dependencies, status, heartbeats |
| Task dispatch | Kanban tasks + agency_agents_delegate | Dispatch tasks to workers/agents |
| Parallel execution | Concurrent agency_agents_delegate calls | Independent workstreams run concurrently |
| Dependency tracking | Kanban task_links table | Parent/child task relationships prevent premature execution |
| Worker lifecycle | Kanban task_runs table | Run status, heartbeats, claim locks, outcomes |
| Daily scheduling | cronjob_manage | Schedule daily Review and reporting |
| Independent Review | Hermes-Ultra agent delegation | Independent assessment of completed work |
| Local commits | Git worktrees + branches | Scoped commits after successful Review |
| Daily reporting | File-based markdown | /workspace/release-artifacts/TASK-008.0-persistent-runtime/daily-reports/ |
| Cross-session persistence | Kanban DB + file reports | State survives session termination |
| Recovery | Kanban task status + task_runs | Unfinished tasks resumable after restart |

## 4. Migration Path

1. Populate Kanban DB with all 56 remaining tasks from TASK-007.x inventory
2. Configure task dependencies via task_links table
3. Implement orchestrator loop (read Kanban, dispatch eligible tasks, collect results)
4. Configure cron for daily Review at end of each day
5. Demonstrate lifecycle: dispatch → execute → validate → review → commit → report

## 5. Constraints Honored

- Docker NOT available → no container orchestration, file-based and Kanban-native
- No executable `/review` tool → use Hermes-Ultra agent delegation for independent Review
- `tool_call` wrapper broken → call agency_agents_delegate and other tools directly as function names
- No systemd inside container → use Hermes-native cron and Kanban mechanisms
- All preservation boundaries maintained — original repo, branches, backups, worktrees, PR #2 untouched
- No push, merge, or PR modification
