# Recovery Procedures — TASK-008.6

**Board:** Cloud-Native Stack
**Generated:** 2026-11-27T02:20:00Z

## 1. Worker Failure

| Step | Action |
|------|--------|
| 1 | Record failure in task_events table |
| 2 | Retry only when technically justified |
| 3 | Reassign to another appropriate agent if needed |
| 4 | Preserve partial work |
| 5 | Verify repository before resuming |

## 2. Blocked Task

| Step | Action |
|------|--------|
| 1 | Record exact block reason |
| 2 | Create or identify the dependency |
| 3 | Move to another independent task |
| 4 | Continue execution |

## 3. Gateway Restart

| Step | Action |
|------|--------|
| 1 | Recover Board state from /data/kanban.db |
| 2 | Reconcile task status with actual files and processes |
| 3 | Resume interrupted work safely from last checkpoint |

## 4. Scheduler Stop

| Step | Action |
|------|--------|
| 1 | Detect the failure |
| 2 | Restore execution loop through supported runtime mechanisms |
| 3 | Record interruption and recovery |

## 5. Checkpoints

Checkpoints are stored at:
/workspace/release-artifacts/TASK-008.6-kanban-board/checkpoints/

Cycle state is persisted at:
/workspace/release-artifacts/TASK-008.6-kanban-board/state/cycle-state.json

## 6. Never Silent Termination

Do not silently terminate the program when one component fails. Always:
- Record the failure
- Attempt recovery
- Continue with independent tasks if available
- Preserve all evidence
