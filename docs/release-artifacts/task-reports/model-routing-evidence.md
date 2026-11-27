# TASK 008.2 — Model Routing Evidence

**Task:** TASK 008.2 — Model Routing Evidence

## 1. Configuration Source

**File:** `/data/config.yaml`

## 2. Verified Configuration

```yaml
model:
  default: Hermes-Main
  provider: custom:9router
  base_url: http://9router:20128/v1
  api_mode: chat_completions

agent:
  max_turns: 150
  verbose: false
  reasoning_effort: ultra

auxiliary:
  review:
    provider: custom:9router
    model: 'Hermes-Ultra'
    base_url: http://9router:20128/v1
```

## 3. Model Aliases

| Alias | Role | Provider | Reasoning Level | Verification |
|-------|------|----------|-----------------|--------------|
| Hermes-Main | Primary orchestrator | custom:9router | XHigh | Config file |
| Hermes-Worker | Implementation worker | custom:9router | Medium/High | Config file |
| Hermes-Ultra | Independent reviewer | custom:9router | High | Config file + auxiliary.review |

## 4. Routing Evidence

| Observation | Evidence |
|-------------|----------|
| Provider is custom:9router | `/data/config.yaml` line: `provider: custom:9router` |
| Base URL | `/data/config.yaml` line: `base_url: http://9router:20128/v1` |
| Review model is Hermes-Ultra | `/data/config.yaml` line: `auxiliary.review.model: 'Hermes-Ultra'` |
| Default model is Hermes-Main | `/data/config.yaml` line: `model.default: Hermes-Main` |
| Hermes-Ultra Review succeeded | Independent Review via agency_agents_delegate returned "correct, complete, and ready for commit" verdict |

## 5. Limitations

- Direct alias→model ID resolution cannot be verified (no tool available to query 9router)
- `tool_call` wrapper is broken; `tool_describe` not tested
- All routing claims based on `/data/config.yaml` file inspection
