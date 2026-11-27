# TASK 008.2 — Agency Router Evidence

**Task:** TASK 008.2 — Agency Router Evidence

## 1. Tool Invocation Rule

`agency_agents_delegate` is called **directly as its own top-level function name**, not through `tool_call`. The `tool_call` wrapper is broken (returns JSON parse errors).

## 2. Successful Delegations

| # | Agent | Slug | Division | Subagent ID | Result | Workstream |
|---|-------|------|----------|-------------|--------|------------|
| 1 | Git Workflow Master | git-workflow-master | engineering | sa-0-14f5bb84 | success | Git safety & branch validation (8/10 checks passed) |
| 2 | Security Architect | security-architect | security | sa-0-91f84f2e | success | Security audit of Phase 5 candidate files |
| 3 | Hermes-Ultra | (independent reviewer) | security | deleg_dadfbcf6 | success | Independent Review of Phase 5-6 reconciliation work |

## 3. Failed Delegations

| Agent | Error | Classification |
|-------|-------|----------------|
| Technical Writer | tool_call JSON parse error | tool_call wrapper broken |
| Backend Architect | tool_call JSON parse error | tool_call wrapper broken |
| SRE / Site Reliability Engineer | tool_call JSON parse error | tool_call wrapper broken |

## 4. Available Agents (Discovered)

25+ specialists across 10 divisions including: Git Workflow Master, Technical Writer, Backend Architect, SRE, Security Architect, Agents Orchestrator, Master Plan Architect, Senior Project Manager, Evidence Collector, and others.

## 5. Invocation Pattern

### Correct (works)
Call `agency_agents_delegate` directly as its own top-level function.
