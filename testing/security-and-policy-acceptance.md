# Section 9: Security and Policy Acceptance Tests

**Purpose**: Cross-component tests for Kubernetes security policy admission, runtime security enforcement, and vulnerability verification. All tests are designed against ephemeral/lab clusters only — no live or shared clusters are used.

> **Important**: Prevention ≠ detection ≠ response. Deliberately insecure workloads = isolated lab tests only. No production or shared cluster access is used at any point.

---

## 9.1 Pod Security Admission (PSA)

| Field | Details |
|---|---|
| **Test ID** | SEC-001 |
| **Scope** | K8s Pod Security Admission: verifying that compliant workloads are accepted and non-compliant workloads are rejected |
| **Positive Test (SEC-001-POS)** | |
| **Preconditions** | PSA is enabled at cluster or namespace level with `runtime/default` or `restricted` profile; a compliant Pod is defined |
| **Test Command** | `kubectl apply -f compliant-pod.yaml` where the pod runs as non-root, has read-only root filesystem, and uses allowed capabilities |
| **Expected Output** | Pod is `Pending` then `Running`; admission review passes; no policy violations |
| **Failure Condition** | Compliant pod rejected — indicates PSA over-misconfiguration or conflicting validationsystem defaults |
| **Remediation** | Review PSA profile selection; check for `privileged` exceptions if legitimately needed; verify `pod-security.kubernetes.io/` annotations |
| **Evidence** | `kubectl get pods` showing `Ready` status; admission review logs; `kubectl get events` showing allow decision |
| **Automated** | Yes — pod manifest scripted; assert pod transitions to `Running`; check audit log for allow event |
| **Manual** | Yes — `kubectl apply -f`; observe pod status; check events |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-001-NEG |
| **Scope** | Pod Security Admission: non-compliant workload is rejected |
| **Preconditions** | Same as positive; but the Pod runs as `root`, adds `CAP_NET_RAW`, or mounts `hostPath` |
| **Test Command** | `kubectl apply -f non-compliant-pod.yaml` where the pod violates at least one PSA rule |
| **Expected Output** | Pod remains `Pending`; admission review denies; "violates PodSecurityPolicy" or "PodSecurityPolicy denied" error |
| **Failure Condition** | Non-compliant pod accepted — indicates PSA is not enforced or is bypassed |
| **Remediation** | Verify PSA is enabled at the correct scope (cluster vs namespace); check for conflicting `securitycontext` settings; ensure no `privileged` annotation overriding PSA |
| **Evidence** | `kubectl get pods` showing `Pending` status; admission review logs; error message; `kubectl get events` |
| **Automated** | Yes — pod manifest scripted; assert pod stays `Pending`; check admission review denial |
| **Manual** | Yes — `kubectl apply -f`; observe pod status; read admission review error |

---

## 9.2 Kyverno Policy Admission

| Field | Details |
|---|---|
| **Test ID** | SEC-002 |
| **Scope** | Kyverno policy admission: verifying policy enforcement on resource creation |
| **Positive Test (SEC-002-POS)** | |
| **Preconditions** | Kyverno controller is running; a allow policy is configured (e.g., require labels on all namespaces) |
| **Test Command** | `kubectl apply -f labeled-resource.yaml` where the resource has all required labels |
| **Expected Output** | Resource is created successfully; Kyverno policy match; admission passes |
| **Failure Condition** | Labeled resource rejected — indicates policy matching issue or selector misconfiguration |
| **Remediation** | Verify Kyverno policy selector matches the resource; check `context` or `validation` rules; ensure policy is not `disabled` |
| **Evidence** | `kubectl get <resource>` showing creation; Kyverno event log; policy match output |
| **Automated** | Yes — resource manifest scripted; assert creation succeeded; check Kyverno events |
| **Manual** | Yes — `kubectl apply -f`; observe creation; check Kyverno policy events |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-002-NEG |
| **Scope** | Kyverno policy admission: resource violating policy is rejected |
| **Preconditions** | Same as positive; but the resource is missing required labels or has prohibited settings |
| **Test Command** | `kubectl apply -f unlabeled-resource.yaml` where the resource violates the Kyverno policy |
| **Expected Output** | Resource creation fails; Kyverno violation event; "policy violation" error message |
| **Failure Condition** | Violating resource accepted — indicates policy is not enforced or is bypassed |
| **Remediation** | Review Kyverno policy definition; ensure `deny` or `validate` rules are correctly typed; check policy `namespace` scope |
| **Evidence** | `kubectl` create error; Kyverno violation event; policy match failure output |
| **Automated** | Yes — resource manifest scripted; assert creation failed; check Kyverno violation events |
| **Manual** | Yes — `kubectl apply -f`; observe failure; read Kyverno event details |

---

## 9.3 Gatekeeper Constraint Admission

| Field | Details |
|---|---|
| **Test ID** | SEC-003 |
| **Scope** | Gatekeeper constraint admission: verifying constraint enforcement on resource creation |
| **Positive Test (SEC-003-POS)** | |
| **Preconditions** | Gatekeeper controller is running; a constraint is defined (e.g., restrict container privileged mode) |
| **Test Command** | `kubectl apply -f constrained-pod.yaml` where the pod respects the constraint (non-privileged, allowed resources) |
| **Expected Output** | Pod is created successfully; constraint matches; admission passes |
| **Failure Condition** | Constrained pod rejected — indicates constraint match issue or constraint template misconfiguration |
| **Remediation** | Verify constraint `match` criteria align with the resource; check `param` values; ensure constraint is `valid` and not `terminating` |
| **Evidence** | `kubectl get pods` showing `Running`; constraint audit log; gatekeeper event output |
| **Automated** | Yes — pod manifest scripted; assert pod creation; check gatekeeper constraint status |
| **Manual** | Yes — `kubectl apply -f`; observe pod status; read gatekeeper event details |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-003-NEG |
| **Scope** | Gatekeeper constraint admission: constrained resource is rejected |
| **Preconditions** | Same as positive; but the pod runs with `privileged: true` or exceeds resource limits |
| **Test Command** | `kubectl apply -f unconstrained-pod.yaml` where the pod violates the Gatekeeper constraint |
| **Expected Output** | Pod creation fails; constraint violation; "constraint violated" error message |
| **Failure Condition** | Unconstrained pod accepted — indicates constraint is not enforced or is bypassed |
| **Remediation** | Review constraint template; ensure `match` has correct `kinds` and `apiVersions`; check `prüfen` of `param` validation |
| **Evidence** | `kubectl` create error; constraint violation output; gatekeeper event log |
| **Automated** | Yes — pod manifest scripted; assert creation failed; check constraint violation |
| **Manual** | Yes — `kubectl apply -f`; observe failure; read constraint event details |

---

## 9.4 K8s RBAC — Security-Critical Operations

| Field | Details |
|---|---|
| **Test ID** | SEC-004 |
| **Scope** | K8s RBAC: security-critical operations require explicit authorization |
| **Positive Test (SEC-004-POS)** | |
| **Preconditions** | RBAC rules allow the operation (e.g., `create pods` in a namespace where the user has permission) |
| **Test Command** | `kubectl --as=authorized-user create deployment test-dep --image=nginx` |
| **Expected Output** | Deployment is created; HTTP 200 from API server; resource is visible |
| **Failure Condition** | Authorized operation denied — indicates RBAC over-restriction or scope mismatch |
| **Remediation** | Review RBAC `role` or `clusterrole` bindings; add or adjust `verbs` and `resources`; check namespace scoping |
| **Evidence** | `kubectl get deployment` showing the created deployment; API server audit log; `kubectl get events` |
| **Automated** | Yes — `kubectl` scripted with assert on resource creation |
| **Manual** | Yes — `kubectl --as=authorized-user`; observe creation; read audit log |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-004-NEG |
| **Scope** | K8s RBAC: security-critical operation is denied |
| **Preconditions** | Same as positive; but the user does not have the requested permission |
| **Test Command** | `kubectl --as=unauthorized-user create deployment test-dep --image=nginx` |
| **Expected Output** | `Error: deployments is forbidden: User "unauthorized-user" cannot create deployments at the namespace level`; 403 Forbidden |
| **Failure Condition** | Unauthorized operation accepted — indicates RBAC misconfiguration or missing binding |
| **Remediation** | Review RBAC bindings; ensure `subjects` match the intended user; check `clusterrole` vs `role` scope; verify `verbs` include `create` |
| **Evidence** | `kubectl` forbidden error; audit log entry showing the denial |
| **Automated** | Yes — `kubectl` scripted with assert on forbidden error |
| **Manual** | Yes — `kubectl --as=unauthorized-user`; observe denial; read audit log |

---

## 9.5 NetworkPolicy — Cilium Security Policy

| Field | Details |
|---|---|
| **Test ID** | SEC-005 |
| **Scope** | Cilium NetworkPolicy: inbound and outbound traffic filtering |
| **Positive Test (SEC-005-POS)** | |
| **Preconditions** | Cilium is running as the CNI; a NetworkPolicy allows traffic between two pod labels |
| **Test Command** | Deploy two pods with matching labels; run `curl` from source pod to target pod's service |
| **Expected Output** | HTTP 200 or expected payload; NetworkPolicy allows the traffic; `cilium monitor` shows "allow" event |
| **Failure Condition** | Traffic blocked despite matching labels — indicates NetworkPolicy selector mismatch or Cilium configuration issue |
| **Remediation** | Verify NetworkPolicy `selector` matches pod labels; check `egress`/`ingress` rules order; ensure Cilium is running and `k8s.opsnetwork.io/enforce` is not `false` |
| **Evidence** | `curl` output; `kubectl get networkpolicy`; `cilium monitor` capture; pod `describe` showing labels |
| **Automated** | Yes — pod deployment scripted; scripted curl; assert HTTP 200; capture cilium monitor event |
| **Manual** | Yes — exec into source pod; `curl` target service; observe cilium monitor output |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-005-NEG |
| **Scope** | Cilium NetworkPolicy: traffic is blocked by policy |
| **Preconditions** | Same as positive; but a NetworkPolicy blocks the traffic between pod labels |
| **Test Command** | Apply a blocking NetworkPolicy (deny all between namespaces); then run the curl test from SEC-005 positive |
| **Expected Output** | Connection refused or timed out; `cilium monitor` shows "policy drop" reason |
| **Failure Condition** | Traffic passes despite blocking policy — indicates policy order mismatch or selector does not match intended pods |
| **Remediation** | Verify policy `order` number; confirm `selector` matches the target pod labels; check `egress`/`ingress` rules; ensure policy is not `disabled` |
| **Evidence** | `cilium monitor` capture; NetworkPolicy YAML; `kubectl get networkpolicy`; `curl` exit code |
| **Automated** | Yes — apply policy, rerun curl test, assert failure |
| **Manual** | Yes — apply via `kubectl apply -f`; then test manually |

---

## 9.6 Trivy Scanning — Image Vulnerability Verification

| Field | Details |
|---|---|
| **Test ID** | SEC-006 |
| **Scope** | Trivy: scanning a container image for vulnerabilities |
| **Positive Test (SEC-006-POS)** | |
| **Preconditions** | Image is available locally or in a registry; Trivy is available with up-to-date vulnerability signatures |
| **Test Command** | `trivy image --severity HIGH,CRITICAL harbor-registry.example.com/project/image:tag` |
| **Expected Output** | Vulnerability report listing HIGH and CRITICAL findings; exit code reflects configured severity threshold |
| **Failure Condition** | Scan tool unavailable; network timeout contacting vulnerability DB; false positives not filtered |
| **Remediation** | Update Trivy signatures; adjust severity thresholds; filter known false positives; verify Trivy cache is fresh |
| **Evidence** | Trivy JSON/HTML report; vulnerability list with severities and fixed-version hints |
| **Automated** | Yes — trivy CLI scripted with JSON output and severity filtering |
| **Manual** | Yes — manual trivy scan with report review |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-006-NEG |
| **Scope** | Trivy: no new vulnerabilities found in known-clean image |
| **Preconditions** | Same as positive; but the image is from a known-clean build (e.g., distroless, minimal base) |
| **Test Command** | `trivy image --severity HIGH,CRITICAL known-clean-image:tag` |
| **Expected Output** | No HIGH or CRITICAL vulnerabilities reported; exit code 0 (or minor findings only) |
| **Failure Condition** | HIGH/CRITICAL findings reported on a known-clean image — indicates signature staleness or misconfiguration |
| **Remediation** | Update Trivy vulnerability DB; verify base image source; check for false positives; adjust severity filter |
| **Evidence** | Trivy report with "No vulnerabilities found" or minimal findings; no clear-text secrets in report |
| **Automated** | Yes — trivy scripted; assert no HIGH/CRITICAL findings |
| **Manual** | Yes — manual trivy scan; review report |

---

## 9.7 Cosign Verification — Image Signature Validation

| Field | Details |
|---|---|
| **Test ID** | SEC-007 |
| **Scope** | Cosign: verifying a container image has a valid signature |
| **Positive Test (SEC-007-POS)** | |
| **Preconditions** | Image is signed with Cosign; public key is available in the trust store; Cosign CLI is available |
| **Test Command** | `cosign verify --key https://rekor.example.com/v1/repositories/index/docker/artifacts/signatures harbor-registry.example.com/project/image:tag` |
| **Expected Output** | Signature verification passes; image digest matches verified signature; exit code 0 |
| **Failure Condition** | Signature verification fails; "invalid signature" or "no signature found"; exit code non-zero |
| **Remediation** | Ensure image is signed before push; add correct public key to trust store; re-sign if key rotation occurred; verify Rekor entry exists |
| **Evidence** | `cosign verify` output; signature metadata; Rekor entry reference |
| **Automated** | Yes — cosign verify scripted with exit code assertion |
| **Manual** | Yes — manual `cosign verify` with output capture |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-007-NEG |
| **Scope** | Cosign: image is unsigned or signature is invalid |
| **Preconditions** | Same as positive; but the image is unsigned or the signature is corrupted |
| **Test Command** | `cosign verify` on unsigned or tampered image |
| **Expected Output** | "invalid signature" or "no signature found"; exit code non-zero |
| **Failure Condition** | Invalid signature accepted — indicates Cosign or trust store misconfiguration |
| **Remediation** | Ensure image is signed before push; add correct public key to trust store; re-sign if key rotation occurred |
| **Evidence** | `cosign verify` output; error message; no Rekor entry reference |
| **Automated** | Yes — cosign verify scripted with assert on failure exit code |
| **Manual** | Yes — manual `cosign verify` with output capture |

---

## 9.8 Falco Runtime Detection

| Field | Details |
|---|---|
| **Test ID** | SEC-008 |
| **Scope** | Falco: runtime security event detection for unexpected container behavior |
| **Positive Test (SEC-008-POS)** | |
| **Preconditions** | Falco is running as a Kubernetes security agent; a Falco rule detects the expected behavior (e.g., running as non-root, no privileged escalation) |
| **Test Command** | Run a pod that triggers the expected Falco rule (e.g., `kubectl run falco-test --image=appropriate/curl --rm -i --restart=Never`; the pod's behavior matches a Falco rule) |
| **Expected Output** | Falco alert is generated; `kubectl get falcoalerts` shows the event; alert contains `time`, `priority`, `output`, and `output` fields with no sensitive data |
| **Failure Condition** | Falco alert not generated for expected behavior — indicates rule misconfiguration or Falco not monitoring the namespace |
| **Remediation** | Verify Falco rule is correctly defined and matched to the pod's runtime behavior; check Falco agent is running; ensure the rule `selector` matches the target namespace/pod |
| **Evidence** | `kubectl get falcoalerts` output; Falco rule definition; no sensitive values in alert `output` field |
| **Automated** | Yes — pod deployment scripted; assert FalcoAlert is created; check alert `priority` and `output` |
| **Manual** | Yes — deploy test pod; `kubectl get falcoalerts`; observe alert |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-008-NEG |
| **Scope** | Falco: no alert for expected behavior; alert only for anomalous behavior |
| **Preconditions** | Same as positive; but the pod behaves in a manner not covered by any Falco rule (or rules are disabled) |
| **Test Command** | Run a pod with benign, expected workload behavior; check for Falco alerts |
| **Expected Output** | No Falco alerts generated; `kubectl get falcoalerts` is empty or shows only pre-existing events |
| **Failure Condition** | Falco alert generated for benign behavior — indicates rule is too broad or misconfigured |
| **Remediation** | Review Falco rules; narrow `selection` or `output` fields; disable rules that fire on benign workloads; adjust rule priority |
| **Evidence** | `kubectl get falcoalerts` output (empty or events list); pod `describe`; no alert output captured |
| **Automated** | Yes — pod deployment scripted; assert no new FalcoAlerts are created |
| **Manual** | Yes — deploy test pod; `kubectl get falcoalerts`; observe empty state |

---

## 9.9 Secret Protection — No Secrets in Pod Specs or Logs

| Field | Details |
|---|---|
| **Test ID** | SEC-009 |
| **Scope** | Secret protection: sensitive values must not appear in pod specifications, logs, or audit events |
| **Positive Test (SEC-009-POS)** | |
| **Preconditions** | A Secret is mounted as a volume or injected as an environment variable; the application reads the secret without leaking it |
| **Test Command** | Create a Secret with a known key; create a Pod that mounts the Secret as a volume; exec into the pod and verify the secret is accessible at the expected path |
| **Expected Output** | Secret values are readable at the mounted path; no secret values appear in `kubectl get secret` output (only object metadata); no secret values in pod logs |
| **Failure Condition** | Secret values appear in `kubectl get secret` output; secret values leak into pod logs or environment; clear-text secrets in pod spec |
| **Remediation** | Ensure Secrets are mounted as volumes (not stored in pod spec); use `stringData` or `binaryData`; redact secrets in logs; apply `kubectl get secret --show-labels` only for metadata |
| **Evidence** | `kubectl get secret` output (metadata only; values masked); `kubectl exec` with file contents masked; pod logs redaction proof |
| **Automated** | Yes — manifest scripted; assert secret accessible at path; mask all values in captured output |
| **Manual** | Yes — create manifest; `kubectl apply`; exec into pod; `cat` mounted files; verify no leak |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-009-NEG |
| **Scope** | Secret protection: accidental secret exposure is detected |
| **Preconditions** | A Secret contains a sensitive value; but the pod spec or logs inadvertently expose it |
| **Test Command** | Attempt to read a Secret via an insecure method (e.g., `kubectl describe secret` without redaction); or generate logs that include the secret |
| **Expected Output** | Secret values are masked/redacted in output; or access is denied/role-restricted |
| **Failure Condition** Secret values appear in clear-text in `kubectl describe` output or pod logs — indicates secret protection gap |
| **Remediation** | Apply Secret management best practices: use volume mounting, not environment variables for sensitive data; add log redaction rules; limit `kubectl` access via RBAC; use external secrets manager with access auditing |
| **Evidence** | `kubectl describe secret` output with masked values; pod logs with redacted secrets; RBAC access log |
| **Automated** | Yes — test manifest scripted; assert values are masked; capture describe/log output |
| **Manual** | Yes — `kubectl describe secret`; `kubectl logs`; verify values are masked |

---

## 9.10 Prevention ≠ Detection ≠ Response Validation

| Field | Details |
|---|---|
| **Test ID** | SEC-010 |
| **Scope** | Demonstrating that prevention, detection, and response are independent control layers |
| **Positive Test (SEC-010-POS)** | |
| **Preconditions** | A policy (PSA, Kyverno, Gatekeeper) prevents a non-compliant resource from being created; Falco detects the same behavior at runtime if prevention fails; response processes the alert |
| **Test Command** | 1. Attempt to create a non-compliant Pod (PSA should deny); 2. If PSA is bypassed, Falco should generate an alert; 3. Response workflow acknowledges the alert |
| **Expected Output** | PSA denies creation (pod stays `Pending`); if `kubectl apply` is forced past PSA, Falco generates an alert; audit log records the event; response team can triage the alert |
| **Failure Condition** | Any layer fails to perform its intended function — prevention does not block, detection does not fire, or response does not acknowledge |
| **Remediation** | Review each layer independently; ensure PSA is enabled at correct scope; verify Falco rules cover the behavior; document response runbook for the alert |
| **Evidence** | `kubectl get pods` showing `Pending`; FalcoAlert output; audit log entries; response runbook sign-off |
| **Automated** | Yes — multi-step scripted test; assert PSA denial; if bypassed, assert Falco alert; assert response acknowledgment |
| **Manual** | Yes — sequential: `kubectl apply`; check pod status; `kubectl get falcoalerts`; response team sign-off |

---

| Field | Details |
|---|---|
| **Test ID** | SEC-010-NEG |
| **Scope** | Isolation: deliberately insecure workload only in lab environment |
| **Preconditions** | A workload that violates multiple security policies (PSA, NetworkPolicy, Kyverno) is deployed in an ephemeral lab cluster only |
| **Test Command** | Deploy a `privileged: true`, `hostPath` mounting, `CAP_NET_RAW` pod in a lab namespace |
| **Expected Output** | PSA/Policy denies or flags the workload; Falco may generate alerts; the workload is isolated and does not affect shared or production clusters |
| **Failure Condition** | Workload affects shared/production clusters; or isolation barriers are bypassed |
| **Remediation** | Ensure workload is only ever deployed to ephemeral lab clusters; enforce namespace quotas and admission restrictions; review cluster separation policies |
| **Evidence** | Lab cluster `kubectl` output (isolated namespace); policy denial/failure events; no access to shared or production clusters |
| **Automated** | Yes — workload manifest scripted; assert deployment to lab namespace only; check policy events |
| **Manual** | Yes — deploy to lab namespace; observe policy and Falco behavior; confirm no cross-namespace/spread |

---

## 9.11 Sensitive Value Masking Policy

All test evidence MUST adhere to the following:

- Clear-text passwords, tokens, keys, or secrets must NOT appear in any captured output
- Regex-mask known secret patterns: `password`, `token`, `secret`, `key` (case-insensitive) replaced with `********`
- Falco alert `output` field must not contain command strings, container images, or path strings that reveal secrets
- Trivy/Anchore report must mask or omit CVE details that embed exploitable reference data; use CVE IDs only, not full descriptions with payload info
- Cosign verification output must not include private key material or raw signature bytes
- `kubectl` output must not include token values from service account paths or secret data
- Evidence files must be redacted before commit or publication

> **Key Principle**: Prevention ≠ detection ≠ response. Each control layer must be validated independently. A policy that prevents non-compliant workloads from running does not guarantee that runtime detection (Falco) will fire if prevention is bypassed, and neither guarantees that the response workflow will correctly triage the alert. All three layers must be tested and verified in isolation and in combination.

---

# Section 9: Summary of Coverage

| Section | Topic | Test IDs |
|---|---|---|
| 9 | Security and Policy Acceptance | SEC-001 through SEC-011 |

*No credentials, secrets, or recovery keys are embedded in this document. All example values are illustrative placeholders. Deliberately insecure workloads are isolated lab tests only — never deployed to shared or production clusters.*
