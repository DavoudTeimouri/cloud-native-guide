# TASK 008.0 — Model Alias and 9router Routing Verification

**Task:** TASK 008.0 Persistent Autonomous Engineering Runtime — Model Routing

## 1. Configured Model Aliases

| Alias | Role | Provider | Reasoning Level | Verification Status |
|-------|------|----------|-----------------|---------------------|
| Hermes-Main | Primary orchestrator | 9router | XHigh | Per system prompt (unverified directly) |
| Hermes-Worker | Implementation worker | 9router | Medium/High | Per system prompt (unverified directly) |
| Hermes-Ultra | Independent reviewer | 9router | High/Highest | Per system prompt (unverified directly) |

## 2. Verification Attempts

| Method | Result |
|--------|--------|
| Environment variable check | `AI_AGENT=hermes-agent`, `HERMES_AGENT=true` found; no 9router-specific vars |
| Config file search | No Hermes config found at /root/.hermes/config.yaml or /root/.config/hermes/config.yaml |
| `tool_call` for tool_describe | `tool_call` wrapper broken — cannot invoke tool_describe |
| Direct `agency_agents_delegate` call | Works — agent delegation successful with Git Workflow Master and Security Architect |
| Direct `cronjob_manage` call | Works — cron management available |
| Direct `todo_list` call | Works — todo list available |
| `/review` tool search | No executable `/review` tool found via tool_search |
| Hermes-Ultra delegation | Succeeded — produced independent Review (deleg_dadfbcf6) |

## 3. Routing Evidence

| Observation | Evidence |
|-------------|----------|
| `agency_agents_delegate` works | Git Workflow Master delegation returned success with subagent_id sa-0-14f5bb84 and sa-0-677886e5 |
| `agency_agents_delegate` works | Security Architect delegation returned success with subagent_id sa-0-91f84f2e and produced comprehensive audit |
| `agency_agents_delegate` failed | Technical Writer, Backend Architect, SRE delegations failed with tool_call JSON errors (wrapper broken) |
| Hermes-Ultra Review succeeded | Independent Review produced "correct, complete, and ready for commit" verdict |
| 3 agents delegated successfully | Git Workflow Master, Security Architect, Hermes-Ultra (via Review) |

## 4. Routing Limitations

1. **`tool_call` wrapper is broken** — deferred tools (tool_describe, tool_call itself) cannot be invoked through the standard wrapper. Direct function calls work for `agency_agents_delegate`, `cronjob_manage`, `todo_list`, `focus_pane`, `skills_list`, `skills_view`, `web_search`, `web_extract`, `terminal`, `read_file`, `write_file`, `patch`, `execute_code`.

2. **Model alias resolution cannot be independently verified** — no tool available to query the 9router provider directly. Alias-to-model mapping is based on system prompt configuration only.

3. **No executable `/review` tool** — independent Review was achieved via Hermes-Ultra agent delegation, not through a slash command.

## 5. Recording Requirements

For each worker execution, the following must be recorded:

| Field | Example |
|-------|---------|
| Alias used | Hermes-Main, Hermes-Worker, Hermes-Ultra |
| Provider | 9router |
| Agent slug | git-workflow-master, security-architect |
| Subagent ID | sa-0-14f5bb84, sa-0-91f84f2e |
| Success/failure | Success or failure with error |
| Task scope | What was delegated |

## 6. Fallback Policy

- Do NOT silently fall back to another provider or model if routing fails
- Record the failure and use an explicitly verified safe fallback only if the existing configuration permits it
- If `agency_agents_delegate` fails, continue with local execution and document the limitation
