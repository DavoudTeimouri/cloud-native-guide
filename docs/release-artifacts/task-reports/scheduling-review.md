# TASK 008.0 — Scheduling and Daily Review Configuration

**Task:** TASK 008.0 Persistent Autonomous Engineering Runtime — Scheduling

## 1. Cron Configuration

Cron is available via `cronjob_manage` but currently has 0 jobs configured.

### Planned Cron Jobs

| Job | Schedule | Purpose | Command/Action |
|-----|----------|---------|----------------|
| Daily Review | End of each working day | Independent Review of accumulated changes | Invoke Hermes-Ultra agent delegation |
| Daily Report | After Review | Produce durable daily report | Write to /workspace/release-artifacts/TASK-008.0-persistent-runtime/daily-reports/ |
| Task Queue Check | Every 30 minutes during work hours | Check for eligible pending tasks | Orchestrator loop iteration |

**Note:** Cron is not a substitute for the durable task queue and continuous dispatcher. It is used only for scheduled activities (daily Review, reporting).

## 2. Daily Review Protocol

### Timing
- Exactly one independent Review per calendar day
- Scheduled after a meaningful batch of implementation work
- Preferably at the end of the working day

### Review Scope
- All changes accumulated since the previous successful Review
- Correctness, regressions, security, consistency, scope compliance
- Missing tests and incomplete acceptance criteria
- Implementation reports vs actual repository state

### Review Mechanism
- Primary: Hermes-Ultra agent delegation (independent reviewer)
- Fallback: Primary Hermes session performs Review if Ultra unavailable
- NOT substituted by: worker self-review, agent self-review, focus_pane, ordinary code inspection

### Review Outcomes

| Outcome | Action |
|---------|--------|
| Pass | Create local commit(s) for reviewed changes, produce daily report |
| Fail | Do not commit, record findings, create corrective tasks, continue work |
| Unavailable | Do not commit, record blocker, preserve work for next Review cycle |

### Review Records

| Field | Value |
|-------|-------|
| Review date | Date of Review |
| Reviewer | Hermes-Ultra (or Hermes-Main fallback) |
| Scope | Commit range or diff since last Review |
| Result | pass/fail |
| Findings | Severity + affected files |
| Fixes | Corrective actions taken |
| Commit SHA(s) | If pass, local commit SHAs |

## 3. Daily Report

### Storage
`/workspace/release-artifacts/TASK-008.0-persistent-runtime/daily-reports/YYYY-MM-DD/`

### Required Sections

| Section | Content |
|---------|---------|
| Reporting date | Date of report |
| Overall project status | Completion estimate, phase |
| Tasks completed | Task IDs, deliverables |
| Tasks in progress | Task IDs, status |
| Tasks blocked | Task IDs, reasons |
| Agent delegations | Agents searched, loaded, delegated, outcomes |
| Model routing | Aliases used, provider (9router), observations |
| Validation results | Commands, exit codes, outputs |
| Independent Review | Result, findings, severity |
| Local commits | SHA(s), messages, changed files |
| Files changed | List of all modified/added files |
| Remaining task count | Number of pending tasks |
| Current blockers | Blocker descriptions |
| Next priorities | Next session task candidates |
| Deviations | Deviations from operating spec |

## 4. Orchestrator Schedule

| Activity | Frequency | Trigger |
|----------|-----------|---------|
| Task queue processing | Continuous | Session active |
| Task dispatch | Per loop iteration | Eligible pending tasks exist |
| Validation | Per task | Task execution complete |
| Daily Review | Once per day | End of working day |
| Daily report | Once per day | After Review |
| Commit | Once per day | After successful Review |

## 5. Retry and Backoff

| Failure Type | Retry Policy | Backoff | Max Attempts |
|--------------|--------------|---------|--------------|
| Agent delegation failure | Retry once | Immediate | 1 |
| Transient execution error | Retry with exponential backoff | 2s, 4s, 8s | 3 |
| Validation failure | No retry | N/A | N/A |
| Review failure | No retry (next day) | N/A | N/A |
