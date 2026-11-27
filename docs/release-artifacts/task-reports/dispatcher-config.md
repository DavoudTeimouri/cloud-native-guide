# TASK 008.0 — Gateway Dispatcher Configuration

**Task:** TASK 008.0 Persistent Autonomous Engineering Runtime — Dispatcher Config

## 1. Dispatcher Architecture

Since Docker is not available and no separate daemon can be safely installed inside the container, the dispatcher is implemented as an orchestrator loop within the Hermes session, using:

- **Kanban DB** at `/data/kanban.db` as the durable task queue and dispatch state store
- **`agency_agents_delegate`** (direct function call) for agent dispatch
- **Git worktrees** for isolated task execution
- **File-based reports** under `/workspace/release-artifacts/TASK-008.0-persistent-runtime/daily-reports/`

## 2. Dispatcher Loop

```
1. READ Kanban tasks with status='pending'
2. FILTER: dependencies satisfied (no unresolved parent in task_links)
3. FILTER: not blocked (block_kind is null)
4. SORT: by priority (desc), then by dependency order
5. SELECT: up to 5 independent tasks (no shared worktree or file)
6. DISPATCH: call agency_agents_delegate for each selected task (concurrent)
7. MONITOR: collect results, update task status in Kanban
8. VALIDATE: run git diff --check, markdown structure, cross-reference checks
9. INTEGRATE: worker outputs into worktree
10. REVIEW: at end of day, dispatch Hermes-Ultra for independent Review
11. COMMIT: if Review passes, create local commit(s)
12. REPORT: produce daily report
13. LOOP: repeat from step 1
```

## 3. Task Selection Algorithm

```
eligible_tasks = SELECT * FROM tasks
  WHERE status = 'pending'
  AND block_kind IS NULL
  AND id NOT IN (SELECT child_id FROM task_links WHERE parent_id NOT IN (SELECT id FROM tasks WHERE status = 'completed'))

sorted_tasks = ORDER BY eligible_tasks.priority DESC, eligible_tasks.created_at ASC

selected = []
for task in sorted_tasks:
    if len(selected) >= 5: break
    if task.workspace_path not in [t.workspace_path for t in selected]:
        if task.id not in [t.id for t in selected]:
            selected.append(task)

return selected
```

## 4. Worker Health Monitoring

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| Heartbeat | task_runs.last_heartbeat_at | > 300 seconds stale | Mark task failed, re-queue |
| Run status | task_runs.status | 'failed' or 'timeout' | Classify error, bounded retry |
| Consecutive failures | tasks.consecutive_failures | >= max_retries | Mark task blocked, escalate |
| Claim lock | tasks.claim_lock / claim_expires | Expired lock | Release task, re-queue |

## 5. Dependency-Aware Scheduling

- Tasks with unresolved parent dependencies (via task_links) remain `pending`
- When a parent task reaches `completed`, child tasks become eligible
- Circular dependencies are prevented by task_links schema (parent_id, child_id composite key)
- No task starts before its prerequisites are satisfied

## 6. Idempotency

- Each task has an `idempotency_key` to prevent duplicate execution
- Before dispatching, check if a task with the same idempotency_key already exists or is completed
- Completed tasks are not re-dispatched

## 7. Recovery After Restart

On session restart, the orchestrator:

1. Restores Kanban task board (SQLite is persistent)
2. Identifies unfinished tasks (status != 'completed')
3. Reconciles stale worker states:
   - Runs with claim_expired → release lock, re-queue task
   - Runs with no heartbeat > 300s → mark failed, re-queue
   - Tasks with consecutive_failures >= max_retries → mark blocked
4. Checks existing worktree and Git state
5. Resumes eligible tasks without duplicating completed work
6. Preserves previous Review and reporting records

## 8. Configuration Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| kanban_db_path | /data/kanban.db | Existing Kanban DB |
| max_concurrent_workers | 5 | Resource control |
| per_task_max_runtime_seconds | 300 | Bounded execution |
| max_retries_per_task | 3 | Bounded retries |
| heartbeat_stale_threshold_seconds | 300 | Stale-worker detection |
| daily_review_time | End of day | One per calendar day |
| reports_path | /workspace/release-artifacts/TASK-008.0-persistent-runtime/daily-reports/ | Durable storage |
| worktrees_base | /workspace/project/github/public-repository/ | Isolated execution |
