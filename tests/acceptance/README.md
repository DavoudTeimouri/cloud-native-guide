# Acceptance test evidence directory

Per `requirements/test-registry.md` and `requirements/acceptance-criteria.md`, every executed acceptance test stores evidence here:

```
tests/acceptance/<TEST-ID>/
  procedure.md    # exact commands used
  result.md       # observed output, timestamped
  verdict.md      # PASS/FAIL, tester, date
  environment.md  # tool versions, cluster state, deploy profile
  logs/           # command output, scan reports (sanitized: no secrets or credentials)
```

## Rules

- A test is PASS only when executed with evidence stored under its ID directory. Never mark a test passed from documentation.
- A test is FAIL only when executed and it failed, with evidence stored.
- Use BLOCKED when a required infrastructure component or prerequisite is unavailable.
- Use NOT RUN when execution has not started and no specific blocker is established.
- N/A requires a documented justification.
- No placeholder or fake evidence may be committed. No secrets or credentials in Git.

## Current state

This directory contains only this README. No acceptance test has been executed; all 86 test IDs in `requirements/test-registry.md` read **NOT RUN**. Per-test evidence directories are created only when a test is executed.

The acceptance test runner (`tests/acceptance/run.sh`) does not exist yet — its creation is a future CI task (see `requirements/test-registry.md`, section 10 and `automation/gitlab-ci/pipeline.md`).
