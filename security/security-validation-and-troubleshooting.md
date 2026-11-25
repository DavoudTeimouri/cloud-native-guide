# Section 10 — Security Validation & Troubleshooting

*Illustrative only — not production-committed configurations. Marked as such where indicated. No validations are applied to a live cluster from this document.*

---\n\n## 10.1 Validation Overview

This section provides procedures to validate that all security controls defined in earlier sections are properly enforced and observable. Each control has a **compliance check** and a **recovery validation** step.

**Validation philosophy**: Verify in `audit-only` mode first, transition to `enforce`/`deny` after confirming no workload breakage. Document all deviations in the cluster's security exceptions registry.

---\n\n## 10.2 Admission Policy Validation

### Check Policy Deployment and Mode

```bash
# List all Kyverno policies and their validation mode
kyverno policy list --all --report-validate

# List all Gatekeeper constraints and their enforcement mode
kubectl get constraints --all-namespaces
kubectl get constrainttemplates --all-namespaces
```

### Verify a Policy is Enforced

```bash
# Test a compliant resource is admitted
kubectl apply -f compliant-pod.yaml
# Expected: admission accepted

# Test a violating resource is rejected
kubectl apply -f non-compliant-pod.yaml 2>&1
# Expected: error message containing policy message
```

### Audit Mode Check

```bash
# Deploy policy with Audit mode first
kyverno policy edit <policy-name> --set validationFailureAction=Audit

# Wait 2 weeks minimum; verify no rejected workloads in logs
kubectl logs -n kyverno <pod> | grep -i "validation failure"
```

### Rollback to Audit

```bash
# If enforce mode breaks critical workload:
kyverno policy edit <policy-name> --set validationFailureAction=Audit
# Or for Gatekeeper:
kubectl edit constraint <constraint-name> -p enforcementAction=Ignore
```

---\n\n## 10.3 RBAC Validation

### Verify User/Service Account Permissions

```bash
# Test intended privileges
kubectl auth can-i 'get' 'pods' --namespace=<ns> --as=<user>

# Test wildcard access (should be restricted)
kubectl auth can-i '*' '*' --all-namespaces --as=<user>

# Verify system group access
kubectl auth can-i 'get' 'pods' --namespace=kube-system --as=system:anonymous
```

### RBAC Audit Checklist

- [ ] No user has `*` verb on `*` resource across all namespaces
- [ ] `system:authenticated` access is narrowed to required operations only
- [ ] `system:anonymous` access is disabled or restricted to health checks
- [ ] `pods/exec` and `pods/portforward` are restricted to diagnostic or service-account users only
- [ ] Service account tokens are not automounted (`automountServiceAccountToken: false`)
- [ ] Each role/binding has a documented owner and review cadence

---\n\n## 10.4 NetworkPolicy Validation

### Confirm Default-Deny Baseline

```bash
# Apply a NetworkPolicy that blocks all traffic in a test namespace
kubectl apply -f default-deny-test.yaml

# Verify all pods are unreachable
kubectl exec -n <test-ns> <pod> -- curl -s -o /dev/null -w "%{http_code}" http://<service>
# Expected: 000 or connection refused

# Clean up test policy
kubectl delete -f default-deny-test.yaml
```

### Verify Additive Behavior

```bash
# Create two policies: one allowing DNS, one allowing HTTP
kubectl apply -f allow-dns.yaml
kubectl apply -f allow-http.yaml

# A pod must match at least one allow rule and must not be denied
kubectl exec <pod> -- curl -s -o /dev/null -w "%{http_code}" http://<service>:80
# Expected: 200 for allowed, 000/403 for blocked

# Remove one policy and verify behavior changes
kubectl delete -f allow-http.yaml
# Expected: HTTP access blocked, DNS still works
```

### NetworkPolicy Checklist

- [ ] DNS egress allowed: `kube-dns/CoreDNS` UDP+TCP 53 to `kube-system` namespace
- [ ] Kubernetes API server access restricted from workload namespaces
- [ ] Monitoring traffic allowances defined (Prometheus scrape, Alertmanager)
- [ ] Storage traffic (Ceph/Rook) policies allow MON/OSD/MDS communication
- [ ] Ingress gateway allows only expected namespace traffic
- [ ] Egress gateway allows only expected destination namespaces
- [ ] Cilium vs native NP differences documented for the cluster's CNI
- [ ] Application-to-application egress + ingress pairs verified (both directions must allow)
- [ ] No plaintext credentials in policy YAML (all placeholders labeled)

---\n\n## 10.5 Pod Security Context Validation

### Verify Security Context is Enforced

```bash
# Apply a test pod with full security context
kubectl apply -f security-context-test.yaml

# Check the security context is present and correct
kubectl get pod <pod-name> -o yaml | grep -E \
  "runAsNonRoot|runAsUser|allowPrivilegeEscalation|readOnlyRootFilesystem|capabilities|seccompProfile"

# Expected: all fields present with correct values

# Verify baseline mode in namespace
kubectl get namespace <ns> -o jsonpath='{.metadata.labels.pod-security.kubernetes.io/enforce}'
# Expected: "restricted" (or "baseline" if still in audit mode)
```

### Security Context Troubleshooting

| Symptom | Expected Cause | Corrective Action |
|---|---|---|
| Pod rejected at admission | Missing `runAsNonRoot: true` | Add missing security context field |
| Pod runs as root despite `runAsNonRoot: true` | UID mapping issue in container runtime | Verify host UID mapping; ensure `runAsUser` is set explicitly |
| `readOnlyRootFilesystem: true` causes pod failure | Application writes to `$PWD` or `/tmp` | Add `emptyDir` writable volume or projected volume |
| Capabilities too restrictive | Workload requires `NET_RAW` or `SYS_NICE` | Add via `capabilities.add` with justification and document exception |
| `allowPrivilegeEscalation: false` not respected | Defaulting webhook not active | Ensure admission controller is running and accepting requests |

---\n\n## 10.6 Image Signature Verification Validation

### Verify Cosign Signature Before Deployment

```bash
# Verify a signed image
cosign verify --key cosign.pub myimage@sha256:abc123def456...

# Expected: signature validated, key fingerprint printed

# Verify fails for unsigned image
cosign verify --key cosign.pub myimage@sha256:abc123def456... 2>&1
# Expected: ERROR: no signature found; exit code non-zero
```

### CI Pipeline Gate

```yaml
# GitHub Actions example — gate promotion on Cosign verification
- name: Verify image signature with Cosign
  run: |
    cosign verify --key cosign.pub myimage@sha256:abc123def456...
  # Pipeline exits non-zero if verification fails
```

### Admission-Time Enforcement (Kyverno verifyImages)

```yaml
# Example Kyverno policy that restricts images to verified registries
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-images
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-verified-image
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment"]
      verifyImages:
        allow:
          - registry: "registry.internal"
            # Cosign verification happens in CI; this policy ensures
            # only images from verified sources are admitted
```

---\n\n## 10.7 Secret Access Validation

### Confirm Secrets are Present at Runtime (not in Image)

```bash
# Verify secret is NOT in the image environment
kubectl exec <pod> -c app -- sh -c 'printenv DB_PASSWORD'
# Expected: empty output (secret not present in image)

# Verify secret IS injected via Vault sidecar
kubectl exec <pod> -c vault-agent -- sh -c 'printenv DB_PASSWORD'
# Expected: contains the dynamic database credential

# Verify secret revocation works
# Rotate Vault lease and confirm pod restart picks up new value
kubectl rollout restart deployment <deployment-name>
# Expected: new credential fetched after restart
```

### Secret Management Checklist

- [ ] No secrets found in Git (gitleaks or equivalent scan)
- [ ] Dynamic secrets via Vault/OpenBao with TTL and lease renewal
- [ ] Static secrets outside Vault are documented and rotation-planned
- [ ] Secret access is via sidecar or init container, not environment variables in the pod spec
- [ ] Secrets are not automounted (`automountServiceAccountToken: false`)
- [ ] TLS certificates managed via PKI, not stored as static secrets

---\n\n## 10.8 Runtime Security Events Validation

### Falco Runtime Detection Rules

```bash
# Forward Falco events to stdout for inspection
kubectl port-forward svc/falco 8666:8666

# Stream events and trigger a rule
curl http://localhost:8666/events

# Trigger: shell spawned inside a running container
kubectl exec -it <pod> -c <container> -- sh -c 'touch /etc/test-falco'
# Expected: event appears in the Falco event stream with priority warning

# Verify default rules are tuned
# Check for rules firing on package managers, container startup, legitimate init processes
# and retire them if found
```

### Runtime Detection Checklist

- [ ] Falco test alert raised for a tuned rule (shell in container, write to /etc)
- [ ] Falco events are forwarded to the configured sink (stdout, syslog, Prometheus, Kafka)
- [ ] Default rules retired for package managers and container startup
- [ ] Rules retained for: writes to `/etc`, `/usr/bin`, `/var/lib/ceph`; `setuid`/`setgid` binaries; Kubernetes API token reads from containers; outbound connections to known-bad IP addresses
- [ ] Falco does not block actions — it detects and reports only

---\n\n## 10.9 Trivy Image Scanning Validation

### Scan Image for Critical/High CVEs

```bash
# Scan by digest (recommended)
trivy image --severity CRITICAL,HIGH myimage@sha256:abc123def456...

# Expected: list of vulnerabilities by severity; exit code 0 if only low/negligible findings

# Gate promotion on critical findings
trivy image --severity CRITICAL,HIGH --exit-code 1 myimage@sha256:abc123def456...
# Expected: pipeline exits non-zero if CRITICAL findings exist
```

### Trivy Checklist

- [ ] CRITICAL image blocked in CI (Trivy exit-code 1 on critical findings)
- [ ] Cosign verification passes for signed images and fails for unsigned
- [ ] No secrets found in Git (gitleaks or equivalent)
- [ ] TLS scan clean (no deprecated protocols, weak ciphers)
- [ ] Break-glass login works with the IdP down (documented exception process)

---\n\n## 10.10 Mandatory Validation Subset

The following minimum controls must be verified in any deployment before promoting to production:

- [ ] Privileged pod denied via Pod Security Standards (or equivalent admission controller)
- [ ] Gatekeeper constraint enforced (or Kyverno equivalent) in application namespaces
- [ ] Falco test alert raised for a tuned rule (shell in container, write to /etc)
- [ ] CRITICAL image blocked in CI (Trivy exit-code 1 on critical findings)
- [ ] Cosign verification passes for signed images and fails for unsigned
- [ ] No secrets found in Git (gitleaks or equivalent)
- [ ] TLS scan clean (no deprecated protocols, weak ciphers)
- [ ] Break-glass login works with the IdP down (documented exception process)

**Verification**: Run the mandatory subset checks in a staging environment before promoting to production. Document any accepted deviations with rationale and monitoring.

---\n\n## 10.11 Troubleshooting Summary

### General Troubleshooting Framework

| Phase | Action | Goal |
|---|---|---|
| **Symptoms** | Observe user-facing impact; collect dashboard/alert data | Narrow the scope of the issue |
| **Commands** | Run diagnostic commands (listed per control) | Identify the failing layer |
| **Isolate** | Determine the layer: admission → network → runtime → supply-chain | Focus investigation |
| **Root Cause** | Investigate configuration, logs, metrics, and events | Find the underlying reason |
| **Corrective Actions** | Apply safe fix (restart, config change, exception documented) | Restore compliance |
| **Recovery Validation** | Re-run validation commands; monitor for 15–30 min | Confirm the fix and prevent recurrence |

### Isolation Matrix — Identify Where to Look

| Control | Admission-Time | Network | Runtime | Supply-Chain |
|---|---|---|---|---|
| Pod Security Context | ✅ (PSS, Kyverno, Gatekeeper) | ❌ | ❌ | ❌ |
| NetworkPolicy | ❌ | ✅ (CNI plugin) | ❌ | ❌ |
| Admission Policies (Kyverno/Gatekeeper) | ✅ | ❌ | ❌ | ❌ |
| Image Signature (Cosign) | ❌ | ❌ | ❌ | ✅ |
| Secret Access (Vault) | ❌ | ❌ | ✅ (runtime fetch) | ❌ |
| Falco Runtime Detection | ❌ | ❌ | ✅ (kernel syscalls) | ❌ |
| Trivy Scanning | ❌ | ❌ | ❌ | ✅ (build/CI time) |

### Recovery Validation Pattern

```bash
# 1. Re-apply the validation command from the relevant section
# 2. Confirm the expected output (e.g., admitted, allowed, clean scan)
# 3. Monitor for 15–30 minutes to confirm no recurrence
# 4. Document the fix and update the exceptions registry if a deviation was accepted
```

---\n\n--- 

*End of Section 10 — Security Validation & Troubleshooting*