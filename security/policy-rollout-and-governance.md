# Section 5 — Policy Rollout and Governance

*Illustrative only — not production-committed configurations. Marked as such where indicated. No policies are applied to a live cluster from this document.*

---\n\n## 5.1 Rollout Strategy Overview

This section documents the process for rolling out security policies across the cluster, transitioning from `audit-only` (or `Audit`) mode to `enforce` (or `deny`), and the governance mechanisms for managing exceptions and ongoing maintenance.

**Core principle**: No policy should transition directly from development to enforcement. All rollouts follow a verify-first, enforce-later cadence.

---\n\n## 5.2 Kyverno Rollout Workflow

### Step 1: Deploy in Audit Mode

```bash
# Edit the ClusterPolicy to set validationFailureAction to Audit (if not already the default)
kyverno policy edit <policy-name> --set validationFailureAction=Audit

# Verify the policy is in audit mode
kyverno policy describe <policy-name>
# Expected: validationFailureAction: Audit
```

### Step 2: Verify No Workload Breakage

| Duration | Action | Success Criteria |
|---|---|---|
| 2 weeks minimum | Monitor all cluster workloads | No pods rejected or stuck in `Pending` |
| Ongoing | Check admission webhook logs | Zero admission errors for compliant workloads |
| Ongoing | Run compliance test suite | All expected workloads admit successfully |

### Step 3: Transition to Enforce Mode

```bash
# Switch the policy to enforce mode
kyverno policy edit <policy-name> --set validationFailureAction=Enforce

# Immediately verify
kubectl apply -f known-compliant-pod.yaml
# Expected: admission accepted

# Test a borderline case
kubectl apply -f borderline-pod.yaml
# Expected: either admitted or rejected with clear message
```

### Step 4: Monitor and Iterate

```bash
# Watch admission logs for rejections
kubectl logs -n kyverno <pod> -f | grep -i "validation failure"

# Iterate on policy patterns if workloads are blocked
# Broadening patterns, adding temporary exceptions, or documenting justifications
```

---\n\n## 5.3 Gatekeeper Rollout Workflow

### Step 1: Deploy with Ignore Enforcement

```yaml
# Gatekeeper Constraint with enforcementAction: Ignore
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: <constraint-kind>
metadata:
  name: <constraint-name>
spec:
  enforcementAction: Ignore  # allows creation with warning
  # ... rest of constraint spec
```

### Step 2: Verify No Workload Breakage

```bash
# Apply a test workload that would be blocked in enforce mode
kubectl apply -f test-workload.yaml
# Expected: admission accepted (because enforcementAction: Ignore)

# Check for warning events
kubectl get events --field-selector reason=constraint-violation
```

### Step 3: Transition to Enforce Mode

```yaml
# Update the constraint to enforcementAction: deny
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: <constraint-kind>
metadata:
  name: <constraint-name>
spec:
  enforcementAction: deny  # blocks non-compliant resources
  # ... rest of constraint spec unchanged
```

### Step 4: Monitor and Iterate

```bash
# Watch for denied admissions
kubectl get admissionreviews -A | grep -i "denied"

# If workloads are blocked, either:
# - Broaden the policy pattern
# - Add a temporary exemption
# - Document the exception and revisit
```

---\n\n## 5.4 Exception Process

### Documenting an Exception

Each exception must be recorded in the cluster's **security exceptions registry** with:

- **Exception ID**: Unique identifier (e.g., `EXC-2024-001`)
- **Namespace**: Which namespace the exception applies to
- **Policy Affected**: Name of the policy (Kyverno ClusterPolicy or Gatekeeper Constraint)
- **Justification**: CVE reference, business requirement, or technical constraint
- **Risk Acceptance**: Name and date of the person/team approving the exception
- **Expiry Date**: When the exception should be reviewed/removed (quarterly review)
- **Rollback Procedure**: Steps to remove the exception if circumstances change

### Exempt Namespace Patterns

```bash
# For Kyverno: add namespace label exemption via match or annotation
# For Gatekeeper: add exemptNamespaces or enforceNamespaces parameter

# Example — exempt a namespace from a resource-requests policy
kubectl label ns <namespace> kyverno.io/exceptions=resource-requests
# Or via Gatekeeper constraint parameter:
parameters:
  exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public", "<namespace>"]
```

### Quarterly Exception Review

1. List all active exceptions from the registry
2. For each exception: determine if it's still required
3. If no longer required: remove the exception and transition the policy
4. If still required: update the expiry date and risk acceptance
5. Document the review outcome in the registry

---\n\n## 5.5 Rollback Procedure

### Safe Rollback Steps

1. **Revert to audit/ignore mode**:
   - Kyverno: `kyverno policy edit <policy-name> --set validationFailureAction=Audit`
   - Gatekeeper: update `enforcementAction: Ignore`

2. **Investigate the root cause** of why workloads were blocked

3. **Iterate on the policy pattern** to broaden the match or add justified exceptions

4. **Re-transition to enforce mode** once the issue is resolved

### Emergency Rollback

If enforce mode is breaking critical production workloads and the issue cannot be quickly resolved:

1. Immediately revert to audit/ignore mode
2. Document the incident in the security exceptions registry
3. Schedule a post-mortem to prevent recurrence
4. Plan the policy redesign with broader patterns or additional exceptions

---\n\n## 5.6 Governance Checklist

- [ ] All 10 admission policies deployed in `security-policies` namespace (or equivalent)
- [ ] Each policy deployed in `audit-only` mode first; no workloads blocked for 2 weeks minimum
- [ ] Each policy transitioned to `enforce`/`deny` mode; verified with compliant and non-compliant test workloads
- [ ] Exemption namespace list includes `kube-system`, `gatekeeper-system`, `kube-public`
- [ ] Policy ownership documented per policy (owner, review cadence, exception registry entry)
- [ ] No duplicate enforcement between Kyverno and Gatekeeper — one authoritative source per policy domain
- [ ] Version-dependent examples marked (Kyverno feature availability, Gatekeeper API version)
- [ ] Safe rollout/rollback procedure documented per policy
- [ ] Supply-chain concepts (registry allowlisting, digest pinning, Cosign verification) integrated where applicable
- [ ] Validation command outputs recorded for each policy's compliant/non-compliant test

---\n--- 

*End of Section 5 — Policy Rollout and Governance*