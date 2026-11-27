# TASK 008.0 — Worker Profile Configuration

**Task:** TASK 008.0 Persistent Autonomous Engineering Runtime — Worker Profiles

## 1. Model Aliases (via 9router provider)

| Alias | Role | Reasoning Level | Usage |
|-------|------|-----------------|-------|
| Hermes-Main | Primary orchestrator | XHigh | Task board management, prioritization, dependency management, worker coordination, integration, daily Review orchestration, final decisions |
| Hermes-Worker | Implementation worker | Medium/High | Routine documentation, Ansible, Python scripts, YAML, config changes, test execution, bounded bug fixes, technical research |
| Hermes-Ultra | Independent reviewer | High/Highest | Independent security-sensitive Reviews, regression assessment, complex debugging, architecture verification, final validation of high-risk changes |

**Provider:** 9router (per system prompt configuration)

**Verification status:** Aliases configured per system prompt. Direct alias→model resolution could not be verified through available tools (`tool_call` wrapper broken; `tool_describe` not tested).

## 2. Worker Assignment Matrix

| Task Type | Primary Worker | Review Worker | Agents |
|-----------|---------------|---------------|--------|
| Documentation reconciliation | Hermes-Worker | Hermes-Ultra | Technical Writer, Git Workflow Master |
| Security-sensitive changes | Hermes-Worker | Hermes-Ultra | Security Architect, Technical Writer |
| Architecture decisions | Hermes-Main | Hermes-Ultra | Backend Architect, Master Plan Architect |
| Git/branch operations | Hermes-Main | N/A | Git Workflow Master |
| CI/validation | Hermes-Worker | Hermes-Ultra | SRE, Evidence Collector |
| Daily Review | N/A | Hermes-Ultra | N/A |

## 3. Worker Configuration

### Hermes-Main (Orchestrator)
- **Concurrency:** 1 (single orchestrator manages task board)
- **Max runtime:** Unbounded (continuous operation during session)
- **Heartbeat:** Not applicable (orchestrator is the session itself)
- **Responsibilities:**
  - Read Kanban task queue
  - Identify eligible tasks (dependencies satisfied, status=pending)
  - Prioritize by dependency order, technical risk, migration blockers
  - Dispatch independent tasks concurrently via agency_agents_delegate
  - Monitor execution and collect results
  - Run validations (git diff --check, markdown structure, etc.)
  - Update task states
  - Orchestrate daily Review via Hermes-Ultra
  - Create local commits only after successful Review
  - Produce daily reports

### Hermes-Worker (Implementation)
- **Concurrency:** Up to 5 concurrent workers for independent tasks
- **Max runtime:** 300 seconds per task (bounded)
- **Heartbeat:** Required — workers must report progress to avoid stale classification
- **Responsibilities:**
  - Copy files from integration branch to isolated worktree
  - Validate file structure and content
  - Run git diff --check
  - Report results to orchestrator

### Hermes-Ultra (Independent Reviewer)
- **Concurrency:** 1 (one Review per day)
- **Max runtime:** 600 seconds (bounded)
- **Heartbeat:** Not applicable
- **Responsibilities:**
  - Inspect all changes since last successful Review
  - Evaluate correctness, regressions, security, consistency, scope compliance
  - Identify missing tests and incomplete acceptance criteria
  - Check implementation reports match actual repository state
  - Produce actionable findings with severity and affected files
  - Return clear pass/fail result

## 4. Worker Lifecycle

| Phase | Action | Mechanism |
|-------|--------|-----------|
| Dispatch | Assign task to worker, set status=in-progress | Kanban task update + agency_agents_delegate |
| Execute | Worker performs task, reports progress | Worker execution, heartbeats via task_runs |
| Complete | Worker reports result, status=completed | Kanban task update, task_runs outcome |
| Review | Hermes-Ultra inspects all changes | agency_agents_delegate to Hermes-Ultra |
| Commit | Orchestrator creates local commit after Review pass | Git commit on isolated worktree branch |
| Recover | On restart, reconcile stale runs, resume pending tasks | Kanban task status + task_runs reconciliation |

## 5. Concurrency Limits

| Resource | Limit | Reason |
|----------|-------|--------|
| Concurrent workers | 5 | Avoid uncontrolled parallelism |
| Concurrent agent delegations | 5-7 | Match specialist count to workstreams |
| Per-task max runtime | 300 seconds | Bounded execution |
| Max retries per task | 3 | Bounded retries, failure classification |
| Daily Review | 1 per calendar day | Per protocol |
| Worker heartbeat interval | 60 seconds | Stale-worker detection |

## 6. Failure Handling

| Failure Type | Response | Max Attempts |
|--------------|----------|--------------|
| Transient error (network, timeout) | Retry with backoff | 3 |
| Validation failure | Do not retry, create corrective task | N/A |
| Review failure | Do not commit, retain work, record findings | N/A |
| Agent delegation failure | Fall back to local execution | 1 |
| Worker stale (no heartbeat) | Mark task as failed, re-queue | N/A |
