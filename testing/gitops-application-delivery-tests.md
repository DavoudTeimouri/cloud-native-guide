# Section 11: GitOps and Application Delivery Integration

*Illustrative only — not production-committed configurations. No live cluster is used; no GitOps automation is executed from this document. All commands are representative; verify against authoritative upstream documentation.*

## 11.1 End-to-end deployment workflow

1. Change in Git.
2. Repository access.
3. Argo CD detection.
4. Manifest rendering.
5. Policy admission.
6. Image retrieval.
7. Pod scheduling.
8. PVC provisioning.
9. Application readiness.
10. Ingress and TLS.
11. Monitoring and log visibility.

## 11.2 Test scenarios

| Test ID | Scenario | Type | Classification |
|---|---|---|---|
| GIT-001 | Successful deployment | Positive | lab-safe |
| GIT-002 | Invalid manifest | Negative | lab-safe |
| GIT-003 | Policy rejection | Negative | lab-safe |
| GIT-004 | Missing image | Negative | lab-safe |
| GIT-005 | Failed image verification | Negative | lab-safe |
| GIT-006 | Missing secret | Negative | lab-safe |
| GIT-007 | PVC provisioning failure | Negative | lab-safe |
| GIT-008 | Application readiness failure | Negative | lab-safe |
| GIT-009 | GitOps drift detection | Positive | lab-safe |
| GIT-010 | Controlled rollback | Positive | lab-safe |

## 11.3 Successful deployment

**Objective**: Confirm a change in Git flows through Argo CD to a running application.

**Preconditions**: Argo CD installed; Git repository reachable; Application resource defined.

**Test command**:
```bash
# Illustrative
argocd app create e2e-app --repo https://git.internal/platform-manifests --path manifests/app --dest-server https://kubernetes.default.svc --dest-namespace default
argocd app sync e2e-app
kubectl get deployment e2e-app
```

**Expected output**: Application `Synced`/`Healthy`; deployment `Available`.

**Failure condition**: Application `OutOfSync`/`Degraded`.

**Remediation**: Check Argo CD diff; `argocd app diff e2e-app`; check manifest syntax.

**Evidence**: `argocd app get e2e-app` output; deployment rollout status.

**Automation**: Shell script / Kubernetes Job.

---

## 11.4 Invalid manifest

**Objective**: Confirm an invalid manifest is rejected.

**Preconditions**: Application resource; invalid YAML committed to Git.

**Test command**:
```bash
# Illustrative
kubectl apply --validate --dry-run=server -f invalid-manifest.yaml
```

**Expected output**: Validation error; manifest not applied.

**Failure condition**: Invalid manifest accepted without error.

**Remediation**: Fix manifest; re-commit.

**Evidence**: Validation error output.

**Automation**: kubectl dry-run.

---

## 11.5 Policy rejection

**Objective**: Confirm a non-compliant workload is blocked by admission policy.

**Preconditions**: Gatekeeper/Kyverno policy requiring `runAsNonRoot: true`; manifest without it.

**Test command**:
```bash
kubectl apply -f noncompliant-pod.yaml
```

**Expected output**: Admission rejection with policy message.

**Failure condition**: Non-compliant pod admitted.

**Remediation**: Fix manifest security context; re-commit.

**Evidence**: Admission error message.

**Automation**: kubectl apply (expected failure).

---

## 11.6 Missing image

**Objective**: Confirm deployment fails gracefully when image is unavailable.

**Preconditions**: Application referencing non-existent image digest.

**Test command**:
```bash
kubectl apply -f app-missing-image.yaml
kubectl get pod <pod>
```

**Expected output**: Pod `ImagePullBackOff`/`ErrImagePull`.

**Failure condition**: Pod runs with wrong image.

**Remediation**: Correct image reference in Git; re-sync.

**Evidence**: `kubectl describe pod` events.

**Automation**: kubectl check.

---

## 11.7 Failed image verification

**Objective**: Confirm an unsigned image is blocked by admission enforcement.

**Preconditions**: Cosign verification policy enforced via Gatekeeper/Kyverno.

**Test command**:
```bash
kubectl apply -f app-unsigned-image.yaml
```

**Expected output**: Admission rejection referencing signature verification failure.

**Failure condition**: Unsigned image admitted.

**Remediation**: Sign image with Cosign; update manifest digest; re-commit.

**Evidence**: Admission error message.

**Automation**: kubectl apply (expected failure).

---

## 11.8 Missing secret

**Objective**: Confirm a pod requiring a missing secret fails to start.

**Preconditions**: Pod referencing non-existent Secret.

**Test command**:
```bash
kubectl apply -f pod-missing-secret.yaml
kubectl get pod <pod>
```

**Expected output**: Pod `CreateContainerConfigError`.

**Failure condition**: Pod starts without secret.

**Remediation**: Create secret from Vault/backup; re-apply.

**Evidence**: `kubectl describe pod` events.

**Automation**: kubectl check.

---

## 11.9 PVC provisioning failure

**Objective**: Confirm a pod fails gracefully when PVC cannot be provisioned.

**Preconditions**: PVC referencing non-existent StorageClass or exhausted capacity.

**Test command**:
```bash
kubectl apply -f pod-missing-pvc.yaml
kubectl get pvc <pvc>
kubectl get pod <pod>
```

**Expected output**: PVC `Pending`; pod `Pending` with `VolumeBindingFailed`.

**Failure condition**: Pod starts without volume.

**Remediation**: Create StorageClass/free capacity; re-apply.

**Evidence**: `kubectl describe pvc`/`kubectl describe pod`.

**Automation**: kubectl check.

---

## 11.10 Application readiness failure

**Objective**: Confirm an application failing readiness is detected.

**Preconditions**: Deployment with failing readiness probe.

**Test command**:
```bash
kubectl rollout status deployment/<app>
kubectl get pod <pod>
```

**Expected output**: Rollout timeout/failure; pod not `Ready`.

**Failure condition**: Deployment marked `Available` despite failing probe.

**Remediation**: Fix application readiness probe or application code; re-commit.

**Evidence**: `kubectl rollout status` output; probe logs.

**Automation**: kubectl rollout status.

---

## 11.11 GitOps drift detection

**Objective**: Confirm manual changes outside Git are detected as drift.

**Preconditions**: Application synced; manual change made directly to cluster (lab-safe).

**Test command**:
```bash
kubectl scale deployment e2e-app --replicas=5   # manual change, lab-safe
argocd app diff e2e-app
argocd app get e2e-app
```

**Expected output**: `argocd app diff` shows difference; Application `OutOfSync`.

**Failure condition**: Drift not detected.

**Remediation**: Reconcile: either revert manual change or commit it to Git then sync.

**Evidence**: `argocd app diff` output.

**Automation**: Shell script (lab-safe only).

---

## 11.12 Controlled rollback

**Objective**: Confirm a bad change can be rolled back via GitOps.

**Preconditions**: Previous good commit in Git.

**Test command**:
```bash
argocd app rollback e2e-app <previous-revision>
kubectl rollout status deployment/e2e-app
```

**Expected output**: Deployment returns to previous revision; pods `Running`/`Ready`.

**Failure condition**: Rollback fails; pods remain unhealthy.

**Remediation**: Investigate rollback failure; forward-fix if needed.

**Evidence**: `argocd app rollback` output; rollout status.

**Automation**: Shell script / Kubernetes Job.

---

## 11.13 Application vs infrastructure failure distinction

**Objective**: Confirm operators can distinguish application failure from infrastructure/integration failure.

| Symptom | Likely layer | Diagnostic |
|---|---|---|
| Pod `CrashLoopBackOff` | Application | Container logs; application code |
| Pod `Pending` `VolumeBindingFailed` | Infrastructure/Storage | StorageClass; CSI; PVC events |
| Pod `Pending` `0/1 nodes available` | Infrastructure/Capacity | Node resources; taints |
| Application `5xx` after deploy | Application | Application logs; recent code change |
| Ingress `502` | Infrastructure/Network | Ingress controller; service endpoints; CNI |
| Argo CD `OutOfSync` | Integration | Git repository; Argo CD controller; credentials |

**Remediation**: Follow the diagnostic column; escalate to the owning team for the failing layer.

---

## 11.14 Limitations

- GitOps does not automatically restore persistent application data; data restore is a separate backup/restore procedure (see `operations/backup-validation-and-drills.md`).
- All tests are illustrative; verify commands against actual Argo CD/Kubernetes versions.

---

*SND 004-P11.7 — GitOps and Application Delivery Integration Tests (illustrative)*
