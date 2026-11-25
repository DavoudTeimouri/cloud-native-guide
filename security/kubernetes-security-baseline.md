# Section 3 — Kubernetes Workload Security Baseline

*Illustrative only — not production-committed configurations. Marked as such where indicated. No baselines are applied to a live cluster from this document.*

---

## 3.1 Baseline Overview

This section defines the **mandatory** workload security baseline applied across all application namespaces. Workload-dependent recommendations extend the baseline where context permits; baseline controls must not be relaxed for any workload type.

**Classification**: Runtime enforcement — admission-time (via PodSecurityStandard `restricted`) + runtime (via runtime configuration).

**Enforcement layers**:
- Admission-time: Pod Security Standards `restricted` profile (label-based defaulting webhook) or complementary admission controllers (Kyverno, Gatekeeper).
- Runtime: kubelet configuration, Seccomp profiles, capabilities drop, seccomp profile type.

> **Do not imply**: The `pod-security.kubernetes.io/enforce` namespace label alone enforces policy. The admission webhook must be active and accepting requests. Labeling a namespace `restricted` without an active admission controller allows the pod to run with only audit warnings.

### Mandatory Baseline Controls

| Control | Value / Requirement | Enforcement Layer | Notes |
|---|---|---|---|
| `runAsNonRoot` | `true` | Admission-time / Runtime | Must be set in security context; runtime enforces refusal of pods without it. |
| `runAsUser` | `65532` (nobody) or distro-assigned UID | Admission-time / Runtime | Set explicit UID; do not leave default. |
| `runAsGroup` | `65532` (nobody) or distro-assigned GID | Admission-time / Runtime | Supplementary group context. |
| `allowPrivilegeEscalation` | `false` | Admission-time / Runtime | Implies no `setuid`/`setgid` binaries can elevate privileges. |
| `readOnlyRootFilesystem` | `true` | Admission-time / Runtime | Prevents tampering at runtime; required for many workloads with proper init. |
| `capabilities.drop` | `["ALL"]` | Admission-time / Runtime | All capabilities dropped; `add` may be used for specific runtime needs (e.g., `NET_RAW` for CNI) with justification. |
| `seccompProfile.type` | `RuntimeDefault` | Admission-time / Runtime | Default seccomp profile from the container runtime (Docker/containerd). |
| `hostNetwork` | `false` | Admission-time | Prohibited in baseline; `true` requires explicit exception. |
| `hostPath` volumes | `prohibited` | Admission-time | No hostPath volumes in baseline workloads. |
| `hostPID` | `false` | Admission-time | Prohibited in baseline workloads. |
| `hostIPC` | `false` | Admission-time | Prohibited in baseline workloads. |
| `allowHostPorts` | `false` | Admission-time | Host port mapping prohibited unless explicitly justified. |
| `imagePullPolicy` | `IfNotPresent` or `PreferredNotReady` | Admission-time | `Always` only for images from approved registries with digest pinning. |
| `serviceAccountTokenAutomount` | `false` | Admission-time | Service account tokens not automounted; injected via sidecar if needed. |
| `privileged` container | `prohibited` | Admission-time | `true` field in security context prohibited. |

### Workload-Dependent Recommendations

| Control | Recommendation | When Applicable |
|---|---|---|
| `capabilities.add` | Allow specific capabilities only when justified (e.g., `NET_RAW` for CNI, `SYS_TIME` for time sync) | Specialized networking or time-critical workloads |
| `runAsUser` / `runAsGroup` | Use non-nobody UIDs when workload requires specific permissions (e.g., writing to protected directories) | Workloads needing controlled filesystem access |
| `seccompProfile.type` | `Localhost` profile for workloads with custom seccomp needs | Advanced runtime security posture |
| `allowHostPorts` | Allow only when internal service mesh handles routing; avoid hostPort exposure | Load-balanced or mesh gateway workloads |
| `imagePullPolicy: Always` | Permit for workloads requiring immediate image updates (CI/CD-driven) | Ephemeral CI/CD runners, canary deployments |
| `serviceAccountTokenAutomount: true` | Allow when workload explicitly needs API access and no sidecar alternative | Admission controllers, API aggregation workloads |

---

## 3.2 Security Context Baseline Example

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: baseline-workload
  labels:
    app: baseline
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    fsGroup: 65532
    supplementalGroups: [65532]
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop:
        - ALL
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: registry.internal/myapp@sha256:abc123def456
      securityContext:
        runAsNonRoot: true
        readOnlyRootFilesystem: true
      ports:
        - containerPort: 8080
  initContainers:
    - name: init-setup
      image: registry.internal/init-tools@sha256:789abc
      securityContext:
        runAsNonRoot: true
        readOnlyRootFilesystem: true
      command: ["sh", "-c", "mkdir -p /data && chown 65532:65532 /data"]
  containers:
    - name: sidecar-logger
      image: registry.internal/logger@sha256:ef123456
      securityContext:
        runAsNonRoot: true
        readOnlyRootFilesystem: true
      volumeMounts:
        - name: log-vol
          mountPath: /var/log/app
  volumes:
    - name: log-vol
      emptyDir: {}
  serviceAccountName: default
  automountServiceAccountToken: false
```

**Expected outcome**: Pod admitted only if all baseline controls are present. Any deviation (e.g., `allowPrivilegeEscalation: true`, missing `runAsNonRoot`, `hostPath` volume) is rejected at admission or flagged at runtime.

**Validation command**:
```bash
# Verify pod is admitted with restricted profile
kubectl apply -f baseline-pod.yaml

# Check security context is enforced
kubectl get pod baseline-workload -o yaml | grep -E "runAsNonRoot|allowPrivilegeEscalation|readOnlyRootFilesystem|seccompProfile|capabilities"

# Verify baseline is active in namespace
kubectl get namespace <ns> -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}'
```

**Troubleshooting / remediation**:
- If pod is rejected: inspect the admission webhook error message; add missing security context fields.
- If `runAsNonRoot` is set but pod still runs as root: verify UID mapping; ensure `runAsUser` is set explicitly.
- If `readOnlyRootFilesystem: true` causes pod failure: applications writing to `$PWD` or `/tmp` need a writable volume (emptyDir or projected).
- If capabilities are too restrictive: workload may require `NET_RAW` or `SYS_NICE` — add via `capabilities.add` with justification and document exception.

---

## 3.3 Service Account Token Automounting

`automountServiceAccountToken: false` is the baseline. Tokens are not automounted into pods. If a workload needs API access:

1. **Sidecar pattern**: Deploy a sidecar that fetches secrets/tokens via Vault Agent or cloud IAM bridge.
2. **Explicit projection**: Use `metadata.annotations` with `kubernetes.io/service-account.name` and ` downwardAPI ` to project specific tokens.
3. **Justified automount**: If no alternative exists, set `automountServiceAccountToken: true` with a documented exception and enhanced monitoring.

**Example — sidecar-injected token access**:
```yaml
spec:
  serviceAccountName: default
  automountServiceAccountToken: false
  containers:
    - name: app
      image: ...
    - name: vault-agent
      image: hashicorp/vault:latest
      args: ["server", "-config=/vault/config/vault-agent.json"]
      volumeMounts:
        - name: vault-token
          mountPath: /vault/secrets
  volumes:
    - name: vault-token
      emptyDir: {}
```

**Validation**:
```bash
# Confirm token is NOT present in pod environment
kubectl exec <pod> -c app -- sh -c 'printenv KUBERNETES_SERVICE_TOKEN'

# Confirm sidecar can fetch token
kubectl exec <pod> -c vault-agent -- sh -c 'curl -s http://127.0.0.1:8200/v1/auth/kubernetes/login'
```

---

## 3.4 Init Containers, Sidecars, and Ephemeral Containers

| Container Type | Security Requirements | Baseline Treatment |
|---|---|---|
| **Init containers** | Must adhere to same security context as primary containers (`runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`). Cannot add capabilities beyond what the primary container allows. | Same baseline as primary containers. Security context inherited from pod-level `securityContext` where possible. |
| **Sidecars** | Same security context requirements; must not widen the pod's attack surface. Sidecars with `privileged: true` or `allowPrivilegeEscalation: true` are prohibited. | Same baseline; sidecar security context must not differ from primary unless justified. |
| **Ephemeral containers** | Debug-only; not scheduled via Kubernetes (entered via `kubectl debug`). Must not be used to run privileged operations. | Not part of baseline YAML — accessed only for triage. Ephemeral container exec does not modify pod spec. |

**Init container example** (from 3.2):
- Inherits pod-level `securityContext.runAsNonRoot: true`.
- Cannot `chmod 777` or write to `/`; filesystem is read-only except where explicitly mounted.
- Exit code must be `0` for pod to proceed; non-zero halts pod creation.

**Sidecar example** (from 3.2):
- Same `readOnlyRootFilesystem: true` and `runAsNonRoot: true`.
- Shares pod network/pid namespace but does not increase host exposure.
- Log volume must not be `hostPath`; use `emptyDir` or secret-managed volume.

**Validation — init containers**:
```bash
# Verify init container security context
kubectl get pod <pod> -o yaml | grep -A5 "initContainers:" | grep -E "runAsNonRoot|allowPrivilegeEscalation"

# Verify pod creation fails without required baseline
kubectl apply -f init-container.yaml && echo "Admitted" || echo "Rejected"
```

**Validation — ephemeral containers**:
```bash
# Ephemeral container access does not modify spec
kubectl debug -it <pod> --image=busybox /bin/sh
# Inside debug shell: verify runtime context
id
cat /etc/passwd
```

---

## 3.5 Validation Checklist

- [ ] `runAsNonRoot: true` set in pod + container security context
- [ ] `runAsUser: 65532` (or assigned UID) explicitly set
- [ ] `allowPrivilegeEscalation: false` set in pod + container security context
- [ ] `readOnlyRootFilesystem: true` set in pod + container security context
- [ ] `capabilities.drop: ["ALL"]` set; `add` only where justified and documented
- [ ] `seccompProfile.type: RuntimeDefault` set
- [ ] `hostNetwork: false` — no host network mode
- [ ] No `hostPath` volumes defined
- [ ] `hostPID: false` — no host PID namespace
- [ ] `hostIPC: false` — no host IPC namespace
- [ ] `allowHostPorts: false` — no host port mapping
- [ ] `automountServiceAccountToken: false` — service account tokens not automounted
- [ ] `privileged: false` — no privileged security context
- [ ] Image uses digest pinning (`@sha256:...`) and comes from approved registry
- [ ] Namespace labeled `pod-security.kubernetes.io/enforce=restricted` (or equivalent admission controller active)
- [ ] Validation command output confirms all fields present and correct

- [ ] **Mandatory baseline**: all controls above must be present in all workloads.
- [ ] **Workload-dependent**: `capabilities.add`, `runAsUser` UID variation, `allowHostPorts`, `imagePullPolicy: Always` — documented exceptions only.

---

## 3.6 Exceptions and Rollout Strategy

**Exception process**:
1. Identify workload requiring exception (e.g., CNI plugin, legacy daemon).
2. Create `Namespace` with `pod-security.kubernetes.io/enforce=privileged` label **only for that namespace**.
3. Document exception: CVE/bug reference, business justification, risk acceptance sign-off.
4. Add Kyverno/Gatekeeper exception rule if applicable (see Section 4).
5. Review exception quarterly; remove when no longer required.

**Rollout strategy**:
1. Label `restricted` profile on all non-control-plane namespaces initially in **audit-only** mode (`validationFailureAction: Audit`).
2. Verify no workloads are broken for 2 weeks.
3. Transition to **enforce** mode.
4. Monitor admission webhook logs for rejected pods; iterate on baseline exceptions.
5. Document all exceptions in the cluster's security exceptions registry.

**Safe rollback**:
- If enforce mode breaks critical workload: revert namespace label to `privileged` or `baseline`.
- Use Kyverno policy `force audit` to transition back while maintaining visibility.
- Restore pod spec fields one-at-a-time; verify after each change.

---