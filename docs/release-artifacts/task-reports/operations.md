# TASK 008.2 — Operations

**Task:** TASK 008.2 — Operations

## 1. Starting a Session

1. Verify preservation boundaries (original HEAD, remote main, archival branch, backup, PR #2)
2. Read task queue at `/workspace/release-artifacts/TASK-008.0-persistent-runtime/tasks/`
3. Check `/workspace/release-artifacts/TASK-008.2-runtime-integrity/` for previous state
4. Resume eligible tasks (dependencies satisfied, status=pending)

## 2. Dispatching Tasks

1. Select task from `tasks/pending/` with status='pending', no unresolved dependencies, not blocked
2. Run `python3 dispatcher.py --max-tasks N` (N = number of tasks to execute)
3. Dispatcher copies files from integration branch, validates, moves to completed/
4. Review results in dispatcher log at `tasks/dispatcher-logs/dispatcher.log`

## 3. Daily Review

1. At end of working day, dispatch Hermes-Ultra for independent Review via `agency_agents_delegate`
2. Review scope: all changes since last successful Review
3. If Review passes: create local commit(s) in phase worktrees, produce daily report
4. If Review fails: do not commit, record findings, create corrective tasks
5. If Review unavailable: preserve work, record blocker, continue next session

## 4. Recovering After Restart

1. Check `tasks/in-progress/` for abandoned tasks
2. Move abandoned in-progress tasks back to `tasks/pending/`
3. Fix any status fields stuck at "failed" or "in-progress"
4. Run dispatcher to resume execution

## 5. Adding New Tasks

Create a Markdown file in `tasks/pending/` with the standard task format. Include task ID, scope, source, target, deliverables, acceptance criteria, validation commands, dependencies, priority, assignee, and status.

## 6. Tool Invocation Patterns

### Working (direct function calls)
- `agency_agents_delegate` — delegation to specialists
- `cronjob_manage` — cron job management
- `todo_list` — todo list management
- `focus_pane` — show desktop pane
- `skills_list` / `skills_view` — skill management
- `web_search` / `web_extract` — web access
- `terminal` / `read_file` / `write_file` / `patch` / `execute_code` — file and command operations

### Broken (do not use)
- `tool_call` — returns JSON parse errors

## 7. Git Safety Rules

- Never push, merge, reset --hard, clean, stash, or amend
- Never delete branches, tags, worktrees, or untracked files
- Never modify original repo, archival branch, backup, PR #2
- Use isolated worktrees with dedicated branches
- Create local commits only after successful independent Review

## 8. Daily Cycle

1. Process Kanban queue continuously via dispatcher
2. Dispatch eligible tasks to workers
3. Validate all completed work (git diff --check, markdown structure, Python syntax)
4. At end of day: independent Review via Hermes-Ultra
5. If Review passes: commit locally, produce daily report
6. If Review fails: preserve work, record findings, continue next day
