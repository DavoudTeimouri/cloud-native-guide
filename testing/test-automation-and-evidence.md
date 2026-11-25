# Section 14: Test Automation and Evidence Collection

*Illustrative only — not production-committed configurations. No automation framework is deployed from this document. All scripts are representative; verify syntax before use.*

## 14.1 Standard test schema

Every test is defined with the following standard schema:

| Field | Description |
|---|---|
| Test ID | Unique identifier (e.g., NET-001, STG-005, SEC-003) |
| Test category | Network / Storage / Registry / Identity / Security / Observability / GitOps / HA / Backup / Upgrade |
| Requirement | The requirement this test validates |
| Component(s) | Components under test |
| Preconditions | Conditions that must hold before execution |
| Execution steps | Commands or procedure to run |
| Expected result | Pass condition |
| Failure severity | S0–S4 (S0 = platform down, S4 = cosmetic) |
| Automation level | Manual / shell script / Python / Kubernetes Job / PromQL / policy test |
| Evidence | Artifact collected on pass/fail |
| Cleanup | Post-test cleanup actions |
| Owner | Responsible team/operator |
| Environment classification | Static/documentation-only, lab-safe, staging-only, production-sensitive approval-required |

Test IDs are unique across all test categories.

## 14.2 Automation opportunities

| Category | Suitable automation | Notes |
|---|---|---|
| Static validation | Shell script / Python | YAML lint, schema validation |
| Component health | kubectl check / shell script | Read-only; no cluster mutation |
| CNI connectivity | Shell script / Kubernetes Job | Positive + negative pairs |
| Storage lifecycle | Kubernetes Job | Requires PVC/CSI; lab-safe |
| Registry supply chain | Shell script | `skopeo copy`, `cosign verify` |
| RBAC authorization | `kubectl auth can-i` | Read-only |
| Admission policy | kubectl apply (expected failure) | Negative test |
| Alert routing | PromQL query | Verify alert fires |
| GitOps drift | `argocd app diff` | Read-only |
| Backup integrity | `etcdctl snapshot status` / Velero | Read-only |
| Upgrade readiness | Shell script / Python | Version checks |

## 14.3 Sample automation script (representative)

**Objective**: Validate core platform health without mutating the cluster.

**Preconditions**: `kubectl` configured; cluster access.

**Script** (illustrative, placeholders labeled):
```bash
#!/bin/bash
# illustrative platform health check — read-only
set -euo pipefail

NAMESPACE="${1:-default}"
FAILURES=0

check() {
    local name="$1"; local expected="$2"; local actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo "PASS: $name -> $actual"
    else
        echo "FAIL: $name -> expected '$expected', got '$actual'"
        FAILURES=$((FAILURES + 1))
    fi
}

# Node readiness
NODES_NOT_READY=$(kubectl get nodes --no-headers | grep -v " Ready " | wc -l)
check "all nodes ready" "0" "$NODES_NOT_READY"

# Pod status
NON_RUNNING=$(kubectl get pods -A --no-headers | grep -v " Running\|Completed " | wc -l)
check "all pods running/completed" "0" "$NON_RUNNING"

# CoreDNS
COREDNS_READY=$(kubectl get deployment -n kube-system coredns -o jsonpath='{.status.readyReplicas}')
check "CoreDNS ready replicas" "1" "$COREDNS_READY"

# Admission webhooks (Kyverno/Gatekeeper) — read-only check
WEBHOOKS=$(kubectl get validatingwebhookconfiguration --no-headers 2>/dev/null | wc -l)
check "admission webhooks configured" "1" "$WEBHOOKS"

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "Platform health check: ALL PASS"
    exit 0
else
    echo "Platform health check: $FAILURES FAILURE(S)"
    exit 1
fi
```

**Safety**: Read-only `kubectl get` commands; no cluster mutation; dry-run safe.

**Expected output**: `Platform health check: ALL PASS` or list of failures with exit code 1.

**Evidence**: Script stdout/exit code.

**Automation**: Shell script; suitable for CI pre-check.

---

## 14.4 Evidence collection

| Test outcome | Evidence to retain |
|---|---|
| Pass | Command output, screenshot (if applicable), timestamp, operator |
| Fail | Error output, logs, diagnostic commands, timestamp, operator, remediation taken |
| Blocked | Reason for block, approver, waiver reference |
| Not applicable | Justification, approver |
| Not tested | Reason, planned execution window |

Evidence must never contain sensitive values (secrets, tokens, keys, passwords). Redact before storing.

## 14.5 Cleanup

Every test that creates cluster resources must define cleanup:

- Delete test namespaces/pods/PVCs after completion.
- Revert manual configuration changes (lab-safe only).
- Restore paused Argo CD sync after drift test.
- Delete test images from internal registry after image verification test.

## 14.6 Avoid creating a large custom testing framework

This document deliberately does not build a new custom test framework. Reuse existing tooling:

- `kubectl` / `oc` for Kubernetes validation
- `etcdctl` for etcd validation
- `ceph` CLI for Ceph validation
- `skopeo` / `cosign` / `trivy` for supply-chain validation
- `argocd` CLI for GitOps validation
- `velero` for backup validation
- PromQL / Grafana for observability validation
- Shell scripts and Kubernetes Jobs for orchestration

Introduce a new dependency only when no existing tool covers the requirement, and document the justification.

## 14.7 Validation of scripts/examples

Any script or sample manifest introduced must:

- Pass shellcheck (shell) or equivalent syntax check.
- Use `set -euo pipefail` (shell) or equivalent error handling.
- Be runnable in a clean environment with labeled placeholders replaced.
- Include input validation and clear error handling.
- Be dry-run or read-only where possible.

Syntax is validated in the available environment; runtime execution against live infrastructure is not performed (see scope boundaries).

---

*SND 004-P11.7 — Test Automation and Evidence Collection (illustrative)*
