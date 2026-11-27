# TASK 008.1 — Queue Design

**Task:** TASK 008.1 — Queue Design

## 1. Queue Type

**File-based task queue** (Kanban DB at /data/kanban.db is read-only in the execute_code context)

## 2. Queue Location

`/workspace/release-artifacts/TASK-008.0-persistent-runtime/tasks/`

## 3. Directory Structure

| Directory | Purpose | Current Count |
|-----------|---------|---------------|
| pending/ | Tasks waiting to be executed | 1 |
| in-progress/ | Tasks currently being executed | 0 |
| completed/ | Tasks successfully completed | 65 |
| blocked/ | Tasks blocked by external dependencies | 4 |

## 4. Task File Format

Each task is a Markdown file with the following fields:

| Field | Description |
|-------|-------------|
| ID | Task identifier (e.g., TASK-008.1-P09-01) |
| Title | Human-readable task title |
| Scope | What the task does |
| Source | Source file location (integration branch @ SHA + file path) |
| Target | Target worktree |
| Deliverables | What the task produces |
| Acceptance criteria | Validation requirements |
| Validation commands | Commands to run |
| Completion condition | When the task is done |
| Dependencies | Task IDs that must complete first |
| Priority | 0-9 (higher = more urgent) |
| Assignee | Worker alias (Hermes-Worker) |
| Status | pending/in-progress/completed/blocked/failed |

## 5. State Transitions

```
pending → in-progress → completed
pending/in-progress → blocked
```

Transitions are performed by:
1. Moving the task file between directories (atomic via `shutil.move`)
2. Updating the `**Status:**` field in the file content

## 6. Dependency Enforcement

Dependencies are stored as task IDs in the `**Dependencies:**` field. A task is eligible only when all its dependencies have task IDs present in the `completed/` directory. Dependency strings like "TASK-008.1-P09-07 (ADR-0028)" are parsed by taking the first whitespace-delimited token as the task ID.

## 7. Concurrency Control

- Only one dispatcher process should run at a time
- Task files are moved atomically from pending/ to in-progress/ before execution
- No file locking is needed since the dispatcher is single-process
- After execution, files are moved to completed/ or blocked/

## 8. Recovery

On dispatcher restart:
1. Scan in-progress/ for abandoned tasks
2. Move abandoned in-progress tasks back to pending/
3. Resume dispatching from pending/

## 9. Current Queue State

| Metric | Count |
|--------|-------|
| Total tasks | 70 |
| Completed | 65 |
| Pending | 1 (P10-14: site/app.js, blocked by P10-15 catalog conflict) |
| Blocked | 4 (P09-17 kubespray version contradiction, P09-18 lifecycle upgrades catalog conflict, P09-19 cluster_methods.py catalog conflict, P10-15 site/data.json catalog conflict) |
| In-progress | 0 |
