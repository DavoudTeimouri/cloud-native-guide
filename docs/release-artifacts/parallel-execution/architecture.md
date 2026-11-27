# Architecture — Real Autonomous Parallel Worker Execution

**Review ID:** TASK-PARALLEL-EXECUTION
**Date:** 2026-11-27
**Component:** TASK-008.7 Autonomous Engineering Supervisor

---

## 1. Supported Integration Mechanism Verified

The Hermes config (`/data/config.yaml`) defines:
- `delegation.backend: default`
- `delegation.max_concurrent_children: 6`
- `delegation.max_spawn_depth: 2`
- `delegation.orchestrator_enabled: true`
- `delegation.model: Hermes-Worker`
- `delegation.provider: custom:9router`

The `agency_agents_delegate` tool is a Hermes top-level tool (not importable from standalone Python). It accepts:
- `agent` (slug or display name) — required
- `task` (task description string) — required
- `slug` (alias for agent)

The `agency_agents_search` tool searches the installed Agency Agents roster (268 agents found). Verified agents include:
- `sre-site-reliability-engineer` (Kubernetes/observability/networking)
- `devops-automator` (Kubespray/automation/IAaC)
- `database-reliability-engineer` (Ceph/storage/disaster-recovery)
- `cloud-security-architect` (security/secrets/Vault)

**Conclusion:** `agency_agents_delegate` cannot be called from a standalone Python process. It must be invoked by the Hermes agent as a top-level tool. The supervisor prepares a dispatch queue; the Hermes agent processes it via direct `agency_agents_delegate` calls.

---

## 2. Component Architecture

Three cleanly separated components:

### A. Discovery — Cron Supervisor (`supervisor.py`)
- Triggered by cronjob `4a751a9bb83f` every 30 minutes
- Queries Kanban DB for Ready tasks
- Checks WIP limits (In Progress < 3, Review < 2, Testing < 2)
- Selects up to 3 eligible Ready tasks (assignee IS NULL)
- Moves selected tasks to In Progress with worker_started_at and assignee
- Registers workers in `worker-tracker.json` with session IDs
- Writes `dispatch_queue.json` for orchestrator processing
- Performs backlog discovery when Ready column is empty
- Detects stalled In Progress tasks (>24h)
- Updates `organization-state.json` with current state

### B. Assignment/Dispatch — Hermes Agent (via `agency_agents_delegate`)
- Reads `dispatch_queue.json`
- Calls `agency_agents_delegate` for each queued item (can be batched for concurrency)
- Each call delegates to a domain-specialist agent with a self-contained task
- Returns subagent_id and execution result

### C. Result Collection — Hermes Agent + Supervisor
- After delegation completes, updates Kanban task to Done with evidence
- Records task_events with completion payload
- Updates `worker-tracker.json` (completed/failed workers)
- Validates output with `check_links.py` (0 broken links required)
- Logs all dispatch decisions, failures, Worker IDs, session IDs

---

## 3. Concurrency Model

Three genuinely independent concurrent Workers:

| Worker | Agent Slug | Domain | Model Alias |
|--------|-----------|--------|-------------|
| Worker 1 | sre-site-reliability-engineer | kubernetes-platform, monitoring-observability, networking | Hermes-Worker |
| Worker 2 | database-reliability-engineer | storage-ceph, disaster-recovery | Hermes-Worker |
| Worker 3 | cloud-security-architect | security, secrets-identity | Hermes-Worker |

**Concurrency mechanism:** Three `agency_agents_delegate` calls dispatched in a single batch (independent, no shared resources). Each call creates a distinct subagent with its own subagent_id and session_id.

**Safeguards:**
- WIP limits enforced in executable code (not just board config)
- Domain-based ownership prevents concurrent edits to same files
- `assignee IS NULL` check prevents double assignment
- `task_events` checked for existing completion before dispatch
- Worker tracker records session IDs for recovery
- Stalled task detection (>24h) for recovery

---

## 4. Execution Lifecycle

1. **Discover:** Supervisor queries Kanban for Ready tasks
2. **Check eligibility:** WIP limits, assignee IS NULL, status = Ready
3. **Assign:** Domain-matched agent selected via `agent_for_task()`
4. **Dispatch:** `agency_agents_delegate` called (up to 3 concurrently)
5. **Track:** Worker registered in worker-tracker.json with session ID
6. **Validate:** Agent runs check_links.py; result returned
7. **Integrate:** Task moved to Done with evidence in task_events
8. **Replenish:** Backlog discovery creates new Ready tasks when column empties

---

## 5. State Files

| File | Purpose |
|------|---------|
| `/data/kanban.db` | Single source of truth for task status |
| `/data/projects.db` | Board config (WIP limits, columns, swimlanes, labels) |
| `state/organization-state.json` | Org-level state (updated by supervisor each cycle) |
| `state/dispatch_queue.json` | Dispatch queue (written by supervisor, read by Hermes agent) |
| `state/worker-tracker.json` | Active/completed/failed worker sessions |
| `logs/supervisor.log` | Cycle execution log |
| `evidence/` | Validation evidence directory |

---

## 6. Safety and Git Boundaries

- No push, merge, PR modification, or history rewrite
- No destructive Git operations
- Local commits only after successful Hermes-Ultra review
- Kubespray version contradiction left explicitly blocked (requires human approval)
- 72 unverified Done tasks not reconciled (requires evidence examination first)
- All existing changes, branches, worktrees, backups preserved
