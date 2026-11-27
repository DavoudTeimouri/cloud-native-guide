# Section 15: Acceptance Criteria and Go/No-Go Model

## Acceptance Matrix

| # | Criterion | PASS Conditions | FAIL Conditions | BLOCKED Conditions | NOT APPLICABLE | NOT TESTED |
|---|-----------|-----------------|-----------------|-------------------|----------------|------------|
| 1 | Static YAML schema validation | All configs conform to OpenAPI/Kubernetes schema; `kubeval`/`kustomize` report 0 errors | Any schema violation; missing required fields | Dependency resolution failure without live cluster | Config set is empty or placeholder-only | Test not yet executed in this cycle |
| 2 | Component-level artifact validation | Images downloadable; CRDs parseable; checksums match | Image pull fails; checksum mismatch; CRD schema error | Artifact not available in mirror/registry | No artifact produced for this component | Test skipped for this release cycle |
| 3 | Interface/dependency contract | API specs match CRD schemas; CLI flags resolved; no contract diffs | Spec/CRD mismatch; CLI flag missing or ambiguous | Contract test environment unavailable | Component has no external interface | Not tested this cycle |
| 4 | Cross-component integration (ephemeral) | All components reach Ready state or expected degraded; no crash loops; events normal | Component crash loop; infinite waiting for dependency; events showing unresolved dependencies | Ephemeral cluster provision failure; resource exhaustion in test environment | No ephemeral cluster available; infrastructure blocked | Not tested this cycle |
| 5 | End-to-end platform (staging) | Platform APIs respond; workloads receive correct responses; no unexpected 5xx; SLO within target | Platform API error; workload misroute; SLO breach > target; crash loops in >1 component | Staging cluster unavailable; resource quota blocking deploy | Platform not yet built for this release | Not tested this cycle |
| 6 | Resilience/failure (lab-safe) | Defined failure mode does not cause cascading outage; graceful degradation or failover observed | Cascading outage; data loss; extended unavailability > acceptable window | Failure simulation method not permitted in this environment | Scenario classified as production-sensitive without approval | Not tested this cycle |
| 7 | Operational acceptance (runbooks) | Operators complete workflows as documented; gaps between docs and reality identified | Runbook step fails; documented step does not match actual API/CLI behavior | Runbook requires production credentials; change window blocked | Operational workflows not yet documented | Not tested this cycle |

**Matrix rules**:
- A cell marked `PASS` means the test executed and met the success criteria.
- A cell marked `FAIL` means the test executed and did not meet the success criteria; a retest is required.
- A cell marked `BLOCKED` means the test could not execute due to environment or infrastructure limitation; root cause documented; retest after unblock.
- A cell marked `NOT APPLICABLE` means the criterion does not apply to this platform configuration (e.g., no LoadBalancer type services).
- A cell marked `NOT TESTED` means the test was not executed this cycle. **Unexecuted test must never be reported as passed.** This is a hard rule — `NOT TESTED` ≠ `PASS`.

## Mandatory vs Conditional Criteria

| Type | Description | Evidence Required | Waiver/Exception Process |
|------|-------------|-------------------|--------------------------|
| **Mandatory** | Criteria that must PASS for the given environment before any promotion. | - Validation reports (schema, checksum)<br>- Integration test logs<br>- Staging acceptance sign-off | Waiver requires SRE lead + platform engineer sign-off; documented reason; tracked in error budget. |
| **Conditional** | Criteria that apply only if the corresponding platform component is deployed/configured. | - Component-specific test results<br>- Deployment status screenshots | If component not deployed, criterion marked `NOT APPLICABLE` with justification. |

### Example: Mandatory Criteria for Staging Acceptance

| Criterion | Type | Evidence |
|-----------|------|----------|
| All platform components reach Ready state | Mandatory | `kubectl get pods -A` screenshot; no `CrashLoopBackOff` |
| End-to-end API smoke test PASS | Mandatory | `curl` output against each platform API endpoint |
| Error budget consumption < 50% for the 30d window | Mandatory | SLO query result (`slo_error_budget_remaining`) |
| Observability stack: metrics ingestion verified | Mandatory | Prometheus target `health="up"` for all expected targets |
| Observability stack: alert routing verified | Mandatory | Fired alert received in Alertmanager; correct receiver |

### Example: Conditional Criteria

| Criterion | Applies If | Evidence |
|-----------|------------|----------|
| LoadBalancer external IP reachability | LoadBalancer services defined in platform | `curl` against external IP; DNS resolution result |
| Registry image pull success | Container images stored in registry | `kubectl describe pod` events; image pull logs |
| Ceph OSD health OK | Ceph storage configured | `ceph health` output; OSD status |
| Keycloak authentication flow | Keycloak deployed and configured | Authentication endpoint 200; user can log in |
| Argo CD application sync | Argo CD deployed; applications defined | `argocd app get <app>` shows Sync Status healthy |

## Severity Classification

| Severity | Definition | Impact on Go/No-Go |
|----------|------------|---------------------|
| **S0 (Critical)** | Complete platform outage; data loss; security breach; SLO breach > 90% error budget | Automatic BLOCKED; no promotion until root cause resolved and retest PASS. |
| **S1 (High)** | Major functionality impaired; one or more critical paths degraded; error budget 50-90% consumed | Requires retest after fix; may proceed with documented waiver if error budget trend is improving. |
| **S2 (Medium)** | Minor functionality degraded; non-critical path affected; error budget 20-50% consumed | May proceed with waiver; retest required before next release cycle. |
| **S3 (Low)** | Cosmetic or cosmetic-only issue; no user impact; error budget < 20% consumed | No gate delay; documented for backlog. |
| **S4 (Info)** | Documentation gap, naming, placeholder update | No gate impact; addressed in next documentation sprint. |

## Go/No-Go Gates

### Lab Acceptance
- **When**: Early in the release cycle, after static validation and component-level validation complete.
- **Gate criteria**:
  - All static YAML schema validation PASS (criterion #1 in matrix).
  - All component-level artifact validation PASS (criterion #2).
  - All interface/dependency contract validations PASS (criterion #3).
  - Cross-component integration on ephemeral cluster: all components reach Ready state or expected degraded (criterion #4).
- **Output**: Lab acceptance sign-off document; if any criterion FAIL, the gate is not met and promotion to staging is blocked until retest.

### Staging Acceptance
- **When**: After lab acceptance PASS; platform deployed to staging cluster; end-to-end testing performed.
- **Gate criteria**:
  - End-to-end platform testing PASS (criterion #5 in matrix): platform APIs respond; workloads correct; SLO within target.
  - Resilience/failure testing (lab-safe) PASS or BLOCKED with documented reason (criterion #6).
  - Operational acceptance: at least 80% of runbook workflows completed or gaps documented (criterion #7).
  - Observability integration: all mandatory criteria (Section 10) verified PASS.
  - Error budget consumption < 50% for the 30d window (mandatory).
- **Output**: Staging acceptance sign-off; promotion to production readiness requires all criteria met or approved waivers.

### Production Readiness
- **When**: After staging acceptance PASS; final gate before production deployment.
- **Gate criteria**:
  - All mandatory criteria PASS across all environments (lab, staging).
  - No S0 or S1 severity open findings without approved waiver.
  - Error budget consumption < 50% with trend improving or stable (not degrading).
  - All production-sensitive approval-required scenarios either PASS or have documented waiver from SRE lead.
  - Observability: alert rule evaluation PASS; alertmanager routing PASS; notification delivery verified.
  - Acceptance report completed and signed off by SRE and platform engineering leads.
- **Output**: Production deployment approved. If any mandatory criterion FAIL and no waiver is approved, the gate is not met and the production deployment is postponed.

## Acceptance Report Template

```markdown
# Acceptance Report — [Release Name] — [Date]

**Platform**: [Name, version, environment]
**SRE Lead**: [Name]
**Platform Engineer**: [Name]

## 1. Summary
- Overall status: [PASS / FAIL / BLOCKED]
- Error budget remaining: [X]% at [window] remaining
- Key findings: [brief bullet summary]

## 2. Test Execution Summary
| Test Level | Result | Evidence Link | Notes |
|------------|--------|---------------|-------|
| Static Validation | PASS/FAIL/BLOCKED | [link] | |
| Component-Level Validation | PASS/FAIL/BLOCKED | [link] | |
| Interface/Dependency Validation | PASS/FAIL/BLOCKED | [link] | |
| Cross-Component Integration | PASS/FAIL/BLOCKED | [link] | |
| End-to-End Platform Testing | PASS/FAIL/BLOCKED | [link] | |
| Resilience/Failure Testing | PASS/FAIL/BLOCKED | [link] | |
| Operational Acceptance | PASS/FAIL/BLOCKED | [link] | |

## 3. Mandatory Criterion Status
| # | Criterion | Status | Severity | Waiver? (Y/N) | Waiver Reason |
|---|-----------|--------|----------|---------------|---------------|
| 1 | ... | PASS/FAIL/BLOCKED | S0/S1/S2/S3/S4 | Y/N | [if Y] |
| 2 | ... | PASS/FAIL/BLOCKED | S0/S1/S2/S3/S4 | Y/N | [if Y] |
| ... | ... | ... | ... | ... | ... |

## 4. Conditional Criterion Status
| # | Criterion | Applies If | Status | Severity |
|---|-----------|------------|--------|----------|
| 1 | ... | ... | PASS/FAIL/BLOCKED | S0-S4 |
| ... | ... | ... | ... | ... |

## 5. Go/No-Go Decision
- **Lab Acceptance**: [PASS / FAIL] — sign-off: _______________
- **Staging Acceptance**: [PASS / FAIL] — sign-off: _______________
- **Production Readiness**: [PASS / FAIL / DEFERRED] — sign-off: _______________

## 6. Outstanding Issues and Retest Plan
| # | Issue | Retest Target Date | Owner | Status |
|---|-------|-------------------|-------|--------|
| 1 | ... | ... | ... | Open/Closed |
| ... | ... | ... | ... | ... |

## 7. Appendices
- Full test logs (links)
- Error budget chart (screenshot)
- Waiver approvals (sign-offs)
```

## Documentation Check ≠ Runtime Acceptance

> **Critical rule**: A documentation check (YAML valid, schema conforms, config matches spec) is NOT runtime acceptance. A manifest may be syntactically valid and schema-conformant yet fail at runtime due to:
> - Resource quotas exceeded
> - Namespace or RBAC restrictions
> - Operator bugs or version mismatches
> - Storage class availability
> - Network policies blocking traffic

**Always validate against a live cluster** (ephemeral or staging) when runtime behavior is the goal. Static validation is a fast-fail gate, not an acceptance criterion.

> **Unexecuted test must never be reported as passed.** If a test was not run in this cycle, the cell is `NOT TESTED`. The acceptance report must clearly distinguish between `FAIL` (run and failed) and `NOT TESTED` (not run). `NOT TESTED` does not satisfy any mandatory or conditional criterion.

---
*This document is part of the SRE integration-testing workstream for Task 004-P11.7. All example values are illustrative/placeholders. No live or shared clusters are used in the design of these acceptance criteria. The Go/no-go gates are design only — actual deployment decisions remain the responsibility of the releasing organization.*
