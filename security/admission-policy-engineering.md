# Section 4 — Admission Policy Engineering

*Illustrative only — not production-committed configurations. Marked as such where indicated. No policies are applied to a live cluster from this document.*

---

## 4.1 Engineering Overview

Admission controllers evaluate resources at creation/update time, either **admitting** (allowing) or **rejecting** (blocking) the operation. This section documents policy implementations using two primary engines:

- **Kyverno**: Kubernetes-native YAML policies; pattern matching, validation, mutation, and generation. No Rego required.
- **OPA Gatekeeper**: Rego constraint templates and constraints; structural and behavioral constraints.

**Policy scope**: Application namespaces only. Control-plane namespaces (`kube-system`, `gatekeeper-system`, `kube-public`) are exempted from most policies with documented exception processes.

**Objective**: Define one authoritative source per policy domain to avoid duplicate enforcement. Kyverno handles image provenance and resource mutation; Gatekeeper enforces structural/orchestration constraints.

---

## 4.2 Policy 1 — Require Resource Requests and Limits

### Security Objective
Every container must specify `resources.requests` and `resources.limits`. Prevents the "resources: null" default that allows unrestricted host resource consumption.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resources
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-resource-requests-and-limits
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "Resources requests and limits must be specified for all containers"
        pattern:
          spec:
            template:
              spec:
                containers:
                  - name: "{{ .name }}"
                  resources:
                    requests:
                      cpu: "100m"
                      memory: "128Mi"
                    limits:
                      cpu: "500m"
                      memory: "512Mi"
```

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`resource_reqs.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8sresourceconstraint
spec:
  crd:
    spec:
      names:
        kind: ResourceRequest
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            namespace:
              type: string
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        containers:
                          type: array
                          items:
                            type: object
                            properties:
                              resources:
                                type: object
                                properties:
                                  requests:
                                    type: object
                                  limits:
                                    type: object
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sresourceconstraint

        violation[msg] {
          not input.review.object.spec.template.spec.containers[_].resources.requests
          msg := sprintf("Container %v missing resources.requests", [input.review.object.spec.template.spec.containers[_].name])
        }

        violation[msg] {
          not input.review.object.spec.template.spec.containers[_].resources.limits
          msg := sprintf("Container %v missing resources.limits", [input.review.object.spec.template.spec.containers[_].name])
        }
```

**Constraint** (`resource-reqs.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: ResourceRequest
metadata:
  name: resource-reqs
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    actions:
      deny: {}
  negate: false
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| `validationFailureAction: Enforce` (Kyverno) | Blocks admission of non-compliant resources; returns error message. |
| `validationFailureAction: Audit` (Kyverno) | Allows resource creation but logs a violation event; no enforcement. |
| Gatekeeper `enforcementAction: deny` | Blocks admission; `Ignore` allows with warning. |
| Default Gatekeeper `fail` on validating webhook failure | Blocks writes when Gatekeeper is down or misconfigured. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-deploy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant
  template:
    metadata:
      labels:
        app: compliant
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
```

**Expected outcome**: Admitted under both Kyverno and Gatekeeper.

### Test Non-Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: non-compliant-deploy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: non-compliant
  template:
    metadata:
      labels:
        app: non-compliant
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
          # resources missing intentionally
```

**Expected outcome**: Rejected by Kyverno (`ERROR: Resources requests and limits must be specified for all containers`) and Gatekeeper (`violation: Container missing resources.requests`).

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public` via `exemptNamespaces` in Kyverno or Gatekeeper constraint match conditions.
- For application namespaces needing temporary relaxation: use `namespace-label` match + `kyverno.io/exceptions` annotation, or Gatekeeper `exemptNamespaces` parameter.
- Document all exceptions in the cluster's exception registry.

### Safe Rollout / Rollback

**Rollout**:
1. Deploy policy in `audit-only` mode (`validationFailureAction: Audit` for Kyverno; Gatekeeper `enforcementAction: Ignore`).
2. Verify no workloads are blocked for 2 weeks.
3. Transition to `Enforce`/`deny`.
4. Monitor admission webhook logs for rejected pods; iterate on baseline.

**Rollback**:
- If enforce mode breaks critical workload: revert to `Audit`/`Ignore` mode.
- Update policy pattern to broaden match or add temporary exception annotation.
- Document rollback rationale in the security exceptions registry.

---

## 4.3 Policy 2 — Disallow Privileged Containers

### Security Objective
No container may be run with `privileged: true` in security context. Prevents workloads from gaining host-level access.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged
spec:
  validationFailureAction: Enforce
  rules:
    - name: no-privileged-containers
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "Privileged containers are not allowed"
        pattern:
          spec:
            securityContext:
              privileged: false
```

> **Pattern limitation**: The Kyverno `pattern` above validates the *presence* of `privileged: false`, but does not strictly reject `privileged: true` in all edge cases. A more robust approach uses Kyverno's `exclude` or validation side-effects.

**Improved Kyverno pattern** (validates absence):

```yaml
validate:
  message: "Privileged containers are not allowed"
  exclude:
    any:
      - path: "spec.securityContext.privileged"
        value: "true"
```

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`no_privileged.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8sprivilegedcontainer
spec:
  crd:
    spec:
      names:
        kind: K8sPrivilegedContainer
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        securityContext:
                          type: object
                          properties:
                            privileged:
                              type: boolean
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sprivilegedcontainer

        violation[msg] {
          not input.review.object.spec.template.spec.securityContext.privileged == false
          msg := "Privileged containers are not allowed"
        }
```

**Constraint** (`privileged-container.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sPrivilegedContainer
metadata:
  name: block-privileged
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `validationFailureAction: Enforce` | Blocks admission if `privileged: true` is present. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation event. |
| Gatekeeper `enforcementAction: deny` | Blocks admission; `Ignore` allows with warning. |
| Gatekeeper `enforcementAction: enforce` (default `fail`) | Blocks writes when Gatekeeper is down; recommended for application namespaces. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-privileged
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant-privileged
  template:
    metadata:
      labels:
        app: compliant-privileged
    spec:
      securityContext:
        privileged: false
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Admitted under both engines.

### Test Non-Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: privileged-deploy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: privileged
  template:
    metadata:
      labels:
        app: privileged
    spec:
      securityContext:
        privileged: true
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Rejected by Kyverno (`Privileged containers are not allowed`) and Gatekeeper (`Privileged containers are not allowed`).

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public` via `exemptNamespaces` parameter.
- For specific workloads needing privileged access (e.g., CNI, storage operators): create a dedicated namespace labeled `privileged-exception: "true"` and exempt that namespace in the policy.
- Document all exceptions.

### Safe Rollout / Rollback

Same as Policy 1 — audit-first, then enforce. Rollback by switching to `Audit`/`Ignore` mode or broadening the policy pattern.

---

## 4.4 Policy 3 — Require Non-Root Execution

### Security Objective
All pods must set `runAsNonRoot: true` and `runAsUser` to a non-root UID. Prevents containers from running as root, which is a common attack vector.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-nonroot
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-run-as-nonroot
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "Pods must run as non-root"
        pattern:
          spec:
            securityContext:
              runAsNonRoot: true
              runAsUser: 65532
```

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`run_as_nonroot.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8srunasnonroot
spec:
  crd:
    spec:
      names:
        kind: K8sRunAsNonRoot
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        securityContext:
                          type: object
                          properties:
                            runAsNonRoot:
                              type: boolean
                            runAsUser:
                              type: integer
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srunasnonroot

        violation[msg] {
          not input.review.object.spec.template.spec.securityContext.runAsNonRoot
          msg := "Pods must run as non-root (runAsNonRoot must be true)"
        }

        violation[msg] {
          input.review.object.spec.template.spec.securityContext.runAsUser == 0
          msg := "Pods must run as non-root (runAsUser must not be 0)"
        }
```

**Constraint** (`nonroot.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRunAsNonRoot
metadata:
  name: require-nonroot
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    enforceNamespaces: ["*"]
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `validationFailureAction: Enforce` | Blocks admission if `runAsNonRoot: true` or `runAsUser: 65532` is missing. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-nonroot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant-nonroot
  template:
    metadata:
      labels:
        app: compliant-nonroot
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload (missing runAsNonRoot)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nonroot-missing
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nonroot-missing
  template:
    metadata:
      labels:
        app: nonroot-missing
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Rejected by Kyverno (`Pods must run as non-root`) and Gatekeeper (`runAsNonRoot must be true`).

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public` via `exemptNamespaces`.
- Some system workloads (e.g., DNS, storage cSI drivers) may require `runAsNonRoot: false` — exempt those specifically via namespace labeling or `exclude` patterns.

### Safe Rollout / Rollback

Same pattern: audit-first, then enforce. Rollback by switching modes or adding exemptions.

---

## 4.5 Policy 4 — Disallow Privilege Escalation

### Security Objective
`allowPrivilegeEscalation: false` must be set in pod + container security context. Prevents `setuid`/`setgid` binaries from elevating privileges.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privilege-escalation
spec:
  validationFailureAction: Enforce
  rules:
    - name: no-privilege-escalation
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "Privilege escalation must be disabled"
        pattern:
          spec:
            securityContext:
              allowPrivilegeEscalation: false
```

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`no_priv_escalation.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8sprivilegesc
spec:
  crd:
    spec:
      names:
        kind: K8sPrivilegeSc
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        securityContext:
                          type: object
                          properties:
                            allowPrivilegeEscalation:
                              type: boolean
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sprivilegesc

        violation[msg] {
          input.review.object.spec.template.spec.securityContext.allowPrivilegeEscalation != false
          msg := "Privilege escalation must be disabled (allowPrivilegeEscalation must be false)"
        }
```

**Constraint** (`privilege-sc.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sPrivilegeSc
metadata:
  name: disallow-priv-escalation
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `validationFailureAction: Enforce` | Blocks admission if `allowPrivilegeEscalation: false` is missing or set to `true`. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-no-escalation
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant-no-escalation
  template:
    metadata:
      labels:
        app: compliant-no-escalation
    spec:
      securityContext:
        allowPrivilegeEscalation: false
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: escalation-allowed
spec:
  replicas: 1
  selector:
    matchLabels:
      app: escalation-allowed
  template:
    metadata:
      labels:
        app: escalation-allowed
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
      # allowPrivilegeEscalation missing or true
```

**Expected outcome**: Rejected.

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public`.
- Some CSI drivers may require `allowPrivilegeEscalation: true` — create dedicated exempt namespaces with justification.

### Safe Rollout / Rollback

Same pattern.

---

## 4.6 Policy 5 — Require Approved Image Registries

### Security Objective
Container images must come from approved registries only. Prevents deployment of images from uncontrolled sources.

### Kyverno Policy (ClusterPolicy) — verifyImages

Kyverno's `verifyImages` feature checks image sources against a allowlist.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-approved-registry
spec:
  validationFailureAction: Enforce
  rules:
    - name: verify-image-registry
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      verifyImages:
        # Allow images from approved registries only
        allow:
          - registry: "registry.internal"
            # Optional: pin by digest
            # tag: "*@sha256:*"
          - registry: "ghcr.internal"
        deny:
          - "registry.untrusted.example.com/*"
```

> **Note**: `verifyImages` is a Kyverno v1.5+ feature. Verify your cluster's Kyverno version before relying on this.

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`approved_registries.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8sapprovedreg
spec:
  crd:
    spec:
      names:
        kind: K8sApprovedReg
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        containers:
                          type: array
                          items:
                            type: object
                            properties:
                              image:
                                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sapprovedreg

        private approved_registries = [
          "registry.internal",
          "ghcr.internal",
        ]

        violation[msg] {
          not any approved_registries[_] as r |
          input.review.object.spec.template.spec.containers[_].image =~ sprintf("^%s/", [r])
          msg := sprintf("Image must come from an approved registry. Found: %v", [input.review.object.spec.template.spec.containers[_].image])
        }
```

**Constraint** (`approved-reg.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sApprovedReg
metadata:
  name: require-approved-registry
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    enforceNamespaces: ["*"]
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `verifyImages: allow/deny` | Blocks admission if image source is not in allowlist. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-registry
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant-registry
  template:
    metadata:
      labels:
        app: compliant-registry
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: non-compliant-registry
spec:
  replicas: 1
  selector:
    matchLabels:
      app: non-compliant-registry
  template:
    metadata:
      labels:
        app: non-compliant-registry
    spec:
      containers:
        - name: app
          image: registry.untrusted.example.com/myapp:latest
```

**Expected outcome**: Rejected by Kyverno (`Image not from approved registry`) and Gatekeeper (`Image must come from an approved registry`).

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public`.
- For temporary needs (e.g., debugging), use `kyverno.io/temporary-exception` annotation on the resource.

### Safe Rollout / Rollout

Same pattern. Rollout: start with broad `allow` list, narrow as trust is established.

---

## 4.7 Policy 6 — Require Image Digests / Image-Tag Policy

### Security Objective
Images must be pinned by digest (`@sha256:...`). Using `:latest` or unspecified tags is prohibited.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-digest
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-digest
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "Images must be pinned by digest (use @sha256: tag)"
        pattern:
          spec:
            containers:
              - image: "*@sha256:*"
```

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`image_digest.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8simagedigest
spec:
  crd:
    spec:
      names:
        kind: K8sImageDigest
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        containers:
                          type: array
                          items:
                            type: object
                            properties:
                              image:
                                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8simagedigest

        violation[msg] {
          not input.review.object.spec.template.spec.containers[_].image =~ "@sha256:"
          msg := sprintf("Image must be pinned by digest. Found: %v", [input.review.object.spec.template.spec.containers[_].image])
        }
```

**Constraint** (`image-digest.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sImageDigest
metadata:
  name: require-image-digest
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    enforceNamespaces: ["*"]
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `validate: pattern: image: "*@sha256:*"` | Blocks admission if digest not present. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-digest
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant-digest
  template:
    metadata:
      labels:
        app: compliant-digest
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123def456example
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload (:latest tag)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: latest-tag
spec:
  replicas: 1
  selector:
    matchLabels:
      app: latest-tag
  template:
    metadata:
      labels:
        app: latest-tag
    spec:
      containers:
        - name: app
          image: registry.internal/myapp:latest
```

**Expected outcome**: Rejected by Kyverno (`Images must be pinned by digest`) and Gatekeeper (`Image must be pinned by digest`).

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public`.
- Some CI/CD workflows may use `:latest` for canary deployments — those namespaces must be explicitly exempted and monitored.

### Safe Rollout / Rollback

Same pattern. Critical: transition from `:tag` to `@digest` gradually; pin images in CI pipeline first.

---

## 4.8 Policy 7 — Restrict Host Networking and host PID/IPC

### Security Objective
`hostNetwork: false`, `hostPID: false`, `hostIPC: false` must be enforced. These namespace-level exposures allow workloads to see host-level resources.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-host-namespaces
spec:
  validationFailureAction: Enforce
  rules:
    - name: no-host-network-pid-ipc
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "hostNetwork, hostPID, and hostIPC must not be enabled"
        pattern:
          spec:
            hostNetwork: false
            hostPID: false
            hostIPC: false
```

> **Pattern limitation**: The Kyverno `pattern` above validates that these fields are `false`, but does not handle the case where the fields are entirely absent (some schemas default to `false`). A stricter approach uses `exclude` to reject `true` values.

### Improved Kyverno (exclude `true`)

```yaml
validate:
  message: "hostNetwork, hostPID, and hostIPC must not be enabled"
  exclude:
    any:
      - path: "spec.hostNetwork"
        value: true
      - path: "spec.hostPID"
        value: true
      - path: "spec.hostIPC"
        value: true
```

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`no_host_namespaces.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8shostnamespaces
spec:
  crd:
    spec:
      names:
        kind: K8sHostNamespaces
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                hostNetwork:
                  type: boolean
                hostPID:
                  type: boolean
                hostIPC:
                  type: boolean
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8shostnamespaces

        violation[msg] {
          input.review.object.spec.hostNetwork == true
          msg := "hostNetwork must not be enabled"
        }

        violation[msg] {
          input.review.object.spec.hostPID == true
          msg := "hostPID must not be enabled"
        }

        violation[msg] {
          input.review.object.spec.hostIPC == true
          msg := "hostIPC must not be enabled"
        }
```

**Constraint** (`host-namespaces.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sHostNamespaces
metadata:
  name: restrict-host-namespaces
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `exclude: value: true` | Blocks admission if any of the three fields is `true`. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: compliant-host
spec:
  hostNetwork: false
  hostPID: false
  hostIPC: false
  containers:
    - name: app
      image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload (hostNetwork: true)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: noncompliant-host
spec:
  hostNetwork: true
  containers:
    - name: app
      image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Rejected.

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public` — some system daemons require `hostNetwork: true`.
- For specific workloads needing host network (e.g., CNI, load balancers): dedicated exempt namespace with justification.

### Safe Rollout / Rollback

Same pattern.

---

## 4.9 Policy 8 — Restrict hostPath Volumes

### Security Objective
`hostPath` volumes are prohibited in baseline workloads. Prevents workloads from accessing host filesystem.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-hostpath
spec:
  validationFailureAction: Enforce
  rules:
    - name: no-hostpath-volumes
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "hostPath volumes are not allowed"
        exclude:
          any:
            - path: "spec.volumes[*]"
              value: hostPath
```

> **Pattern note**: The `exclude` path `spec.volumes[*].value: hostPath` matches any volume where `hostPath` is set. Kyverno's pattern matching on arrays of objects uses JSONPath-like paths.

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`no_hostpath.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8shostpathvol
spec:
  crd:
    spec:
      names:
        kind: K8sHostPathVol
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        volumes:
                          type: array
                          items:
                            type: object
                            properties:
                              hostPath:
                                type: boolean
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8shostpathvol

        violation[msg] {
          input.review.object.spec.template.spec.volumes[_].hostPath == true
          msg := "hostPath volumes are not allowed"
        }
```

**Constraint** (`hostpath-vol.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sHostPathVol
metadata:
  name: disallow-hostpath
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `exclude: value: hostPath` | Blocks admission if any volume uses `hostPath`. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload (no hostPath)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: compliant-hostpath
spec:
  containers:
    - name: app
      image: registry.internal/myapp@sha256:abc123
  volumes:
    - name: empty-vol
      emptyDir: {}
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload (hostPath volume)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: noncompliant-hostpath
spec:
  containers:
    - name: app
      image: registry.internal/myapp@sha256:abc123
  volumes:
    - name: host-vol
      hostPath:
        path: "/tmp"
```

**Expected outcome**: Rejected.

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public` — some CNI and storage plugins require `hostPath`.
- For specific workloads (e.g., system daemons): dedicated exempt namespace.

### Safe Rollout / Rollback

Same pattern.

---

## 4.10 Policy 9 — Require Security Context Settings

### Security Objective
Security context fields (`runAsNonRoot`, `runAsUser`, `allowPrivilegeEscalation`, `readOnlyRootFilesystem`, `capabilities.drop`, `seccompProfile`) must be present in all pods.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-security-context
spec:
  validationFailureAction: Enforce
  rules:
    - name: security-context-required
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "Security context must be specified with required fields"
        pattern:
          spec:
            securityContext:
              runAsNonRoot: true
              runAsUser: 65532
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                  - ALL
              seccompProfile:
                type: RuntimeDefault
```

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`security_context.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8ssecuritycontext
spec:
  crd:
    spec:
      names:
        kind: K8sSecurityContext
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    spec:
                      type: object
                      properties:
                        securityContext:
                          type: object
                          properties:
                            runAsNonRoot:
                              type: boolean
                            runAsUser:
                              type: integer
                            allowPrivilegeEscalation:
                              type: boolean
                            readOnlyRootFilesystem:
                              type: boolean
                            capabilities:
                              type: object
                              properties:
                                drop:
                                  type: array
                            seccompProfile:
                              type: object
                              properties:
                                type:
                                  type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8ssecuritycontext

        violation[msg] {
          not input.review.object.spec.template.spec.securityContext.runAsNonRoot
          msg := "Security context must have runAsNonRoot: true"
        }

        violation[msg] {
          not input.review.object.spec.template.spec.securityContext.allowPrivilegeEscalation == false
          msg := "Security context must have allowPrivilegeEscalation: false"
        }

        violation[msg] {
          not input.review.object.spec.template.spec.securityContext.readOnlyRootFilesystem
          msg := "Security context must have readOnlyRootFilesystem: true"
        }

        violation[msg] {
          not input.review.object.spec.template.spec.securityContext.capabilities.drop[_]
          msg := "Security context must have capabilities.drop set"
        }

        violation[msg] {
          not input.review.object.spec.template.spec.securityContext.seccompProfile.type
          msg := "Security context must have seccompProfile.type set"
        }
```

**Constraint** (`security-context.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sSecurityContext
metadata:
  name: require-security-context
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    enforceNamespaces: ["*"]
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `pattern: securityContext: ...` | Blocks admission if any required field is missing or has wrong value. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-secctx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant-secctx
  template:
    metadata:
      labels:
        app: compliant-secctx
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload (missing security context)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: no-secctx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: no-secctx
  template:
    metadata:
      labels:
        app: no-secctx
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Rejected by Kyverno and Gatekeeper.

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public`.
- Some legacy workloads may not have security context — those namespaces must be explicitly exempted and documented.

### Safe Rollout / Rollback

Same pattern.

---

## 4.11 Policy 10 — Require Approved Labels and Ownership Metadata

### Security Objective
All workloads must carry approved labels for ownership, environment, and cost-center tracking. Prevents untagged or mislabeled workloads from running.

### Kyverno Policy (ClusterPolicy)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-approved-labels
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-labels
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      validate:
        message: "Approved labels must be present on all workloads"
        pattern:
          metadata:
            labels:
              environment: "production|staging|development"
              owner: "[a-z0-9-]+"
              cost-center: "[0-9]{3}"
```

> **Pattern note**: The Kyverno `pattern` above uses regex-like validation within the pattern match. Full regex support varies by Kyverno version; adjust based on cluster Kyverno version.

### Gatekeeper Policy (ConstraintTemplate + Constraint)

**ConstraintTemplate** (`approved_labels.yaml`):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8sapprovedlabels
spec:
  crd:
    spec:
      names:
        kind: K8sApprovedLabels
      schema:
        openAPIv3Schema:
          type: object
          properties:
            kind:
              type: string
              enum: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
            spec:
              type: object
              properties:
                template:
                  type: object
                  properties:
                    metadata:
                      type: object
                      properties:
                        labels:
                          type: object
                          additionalProperties:
                            type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sapprovedlabels

        violation[msg] {
          not input.review.object.metadata.labels.environment
          msg := "Label 'environment' must be present"
        }

        violation[msg] {
          not input.review.object.metadata.labels.owner
          msg := "Label 'owner' must be present"
        }

        violation[msg] {
          not input.review.object.metadata.labels.cost-center
          msg := "Label 'cost-center' must be present"
        }
```

**Constraint** (`approved-labels.yaml`):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sApprovedLabels
metadata:
  name: require-approved-labels
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
  parameters:
    enforceNamespaces: ["*"]
    exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
```

### Audit vs Enforce Behavior

| Behavior | Action |
|---|---|
| Kyverno `pattern: labels: ...` | Blocks admission if required labels are missing or don't match pattern. |
| Kyverno `validationFailureAction: Audit` | Allows creation; logs violation. |
| Gatekeeper `enforcementAction: deny` | Blocks admission. |
| Gatekeeper `enforcementAction: Ignore` | Allows with warning. |

### Test Compliant Workload

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliant-labels
  labels:
    environment: production
    owner: team-alpha
    cost-center: "123"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliant-labels
  template:
    metadata:
      labels:
        app: compliant-labels
        environment: production
        owner: team-alpha
        cost-center: "123"
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Admitted.

### Test Non-Compliant Workload (missing labels)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: no-labels
spec:
  replicas: 1
  selector:
    matchLabels:
      app: no-labels
  template:
    metadata:
      labels:
        app: no-labels
    spec:
      containers:
        - name: app
          image: registry.internal/myapp@sha256:abc123
```

**Expected outcome**: Rejected by Kyverno (`Approved labels must be present`) and Gatekeeper (`Label 'environment' must be present`).

### Exceptions + Namespace Scoping

- Exempt `kube-system`, `gatekeeper-system`, `kube-public`.
- Some infrastructure workloads (e.g., monitoring, logging) may have different label requirements — those namespaces must be explicitly exempted with documented rationale.

### Safe Rollout / Rollback

Same pattern. Start with `audit-only`, verify label completeness across workloads, then transition to `enforce`.

---

## 4.12 Gatekeeper vs Kyverno — Objective Comparison

| Dimension | Kyverno | Gatekeeper |
|---|---|---|
| **Policy language** | Kubernetes-native YAML (pattern, validate, exclude, mutate, generate) | Rego (Turing-complete logic language) |
| **Learning curve** | Low — YAML-native; no new language | Higher — Rego syntax and evaluation model |
| **Best fit domains** | Image verification, resource mutation, source-based rules | Structural/orchestration constraints, complex logic |
| **Constraint templates vs policies** | Single YAML resource (ClusterPolicy/Policy) | Two-step: ConstraintTemplate + Constraint |
| **Mutation capabilities** | Native — can rewrite resource spec on the fly | Limited — primarily validation; mutation via separate AdmissionReview |
| **ValidationFailureAction** | `Enforce` (block) or `Audit` (warn) | `deny` (block) or `Ignore` (warn) + `enforcementAction: fail` / `Ignore` |
| **Matching scope** | `any`, `all`, `none` resource kinds; `matchResources` with labels/selections | `match` on `kinds` with `apiGroups` and `kinds`; `parameter` exemptions |
| **ExemptNamespaces** | `exemptNamespaces` rule parameter | `enforcementAction: Ignore` + `exemptNamespaces` in constraint parameters |
| **Version dependency** | Kyverno features (verifyImages, mutation) vary by version; mark version-dependently | Gatekeeper API version (`constraints.gatekeeper.sh/v1beta1`) relatively stable; Rego version varies |
| **When to use one, not the other** | Use Kyverno for: image provenance, resource mutation, allow/deny lists based on registry/label values; faster iteration in YAML. | Use Gatekeeper for: complex structural constraints, reusable constraint templates across clusters, logical conditions that benefit from Rego's expressive power. |
| **Avoid duplicate enforcement** | Assign image-related policies (registry pinning, digest pinning, signature verification) to Kyverno. Assign structural/orchestration constraints (resource requests, security context, host namespace restrictions) to Gatekeeper. | Do not duplicate the same rule in both engines. If a policy applies to both domains, choose one authoritative source and document the choice. |

### Policy Ownership Management

1. **Catalog policies** in a dedicated namespace (e.g., `security-policies`) with one subdirectory per engine.
2. **Assign ownership**: Each policy has an owner (security team or platform team) and a review cadence (quarterly).
3. **Avoid overlaps**: Before adding a new policy, search existing policies to ensure no duplicate enforcement.
4. **Version tagging**: Tag each policy with the minimum engine version required. Deprecate policies on older versions.
5. **Rollout tracking**: Use a `PolicyRollout` annotation or label to track `audit` → `enforce` status per namespace.

---

## 4.13 Supply-Chain Concepts in Admission Policy Engineering

### Trusted Image Sources

- **Kyverno `verifyImages`**: Policies that allow/deny image registries at admission time. Works in conjunction with Cosign signature verification — Kyverno checks the registry source, Cosign verifies the signature.
- **Gatekeeper**: Pattern-match on `image: "*@sha256:*"` to enforce digest pinning; combine with external admission controller logic for registry allowlisting.

### Image Scanning with Trivy

- Trivy operates at **build time / CI time**, not admission time. A clean Trivy scan does not guarantee a safe image at runtime (new CVEs may emerge between scan and deployment).
- Policy: Integrate Trivy into CI/CD as a gate (`exit-code 1` on CRITICAL findings). Do not rely on Trivy as an admission-time enforcement mechanism.
- Example Kyverno policy that references Trivy scan results (informational, not enforcement):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: informational-trivy-findings
spec:
  validationFailureAction: Audit
  rules:
    - name: trivy-scan-reference
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment"]
      validate:
        message: "Ensure image was scanned with Trivy before promotion"
        pattern: {}  # No enforcement; annotation added for awareness
```

### Image Signing with Cosign

- Cosign signs images by digest using key transparency and PKI. Verification: `cosign verify --key <public-key> <image@digest>`.
- **Signature verification vs admission enforcement**:
  - **Signature verification**: Cosign independently verifies the image signature. This can happen outside the cluster (CI pipeline, local developer workflow).
  - **Admission enforcement**: Kyverno `verifyImages` or a custom Gatekeeper constraint can require that an image has been verified via Cosign before admission.
- Example Kyverno policy integrating Cosign verification:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-images-cosign
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-cosign-signature
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment", "ReplicaSet", "StatefulSet", "DaemonSet", "Job"]
      verifyImages:
        allow:
          - registry: "registry.internal"
            # Cosign verification is enforced via external pipeline; this policy
            # ensures only images from verified sources are admitted.
            # The actual signature verification step happens in CI.
```

> **Do not imply**: Cosign alone secures the runtime. It is a supply-chain gate; runtime security (Falco, runtime admission controllers) is separate.

### Image Digest Pinning

- Enforced via Policy 6 (Require Image Digests / Image-Tag Policy) in both Kyverno and Gatekeeper.
- Digest pinning (`@sha256:...`) ensures the exact image content is referenced, not a mutable tag.
- Combined with registry allowlisting (Policy 5), this forms the supply-chain gate.

### SBOM/Provenance Considerations

- **SBOM (Software Bill of Materials)**: Generated during build (e.g., `cyclonedx`, `spdx` formats). Not enforced at admission time; used for vulnerability analysis and compliance auditing.
- **Provenance (SBOM + signature)**: Cosign can sign SBOM artifacts alongside images. Admission policies can require provenance verification as an additional gate.
- **Distinguish**:
  - **Scanning** (Trivy): Reports known vulnerabilities; does not prevent deployment.
  - **Signing** (Cosign): Cryptographically verifies image integrity and provenance.
  - **Signature verification**: The act of checking a Cosign signature; can be an admission-time gate.
  - **Admission enforcement**: The policy that blocks unverified/un-signed images at create time.

**Policy integration pattern**:
1. **Build time**: Image is signed with Cosign; Trivy scan runs and passes.
2. **CI gate**: Pipeline exits non-zero if Trivy finds CRITICAL/HIGH findings OR if Cosign verification fails.
3. **Admission time**: Kyverno `verifyImages` policy ensures only images from approved registries with valid digests are admitted. A separate Gatekeeper or Kyverno rule can check for Cosign signature presence as an additional check.
4. **Runtime**: Falco detects anomalous behavior; OPA Gatekeeper/PSS prevents privileged escalation even if image was previously verified.

### Summary — Scanning vs Signing vs Signature Verification vs Admission Enforcement

| Concept | Tool / Mechanism | Timing | Purpose |
|---|---|---|---|
| **Scanning** | Trivy, Grype, Snyk | Build / CI | Report vulnerabilities; gate promotion |
| **Signing** | Cosign | Build | Cryptographically bind key transparency to image digest |
| **Signature verification** | `cosign verify`, Kyverno `verifyImages`, Gatekeeper constraints | Admission / Deploy | Verify that image carries a valid signature from trusted key |
| **Admission enforcement** | Kyverno policies, Gatekeeper constraints | Admission time | Block deployment of non-compliant images; enforce policy at create time |

**Do not claim**: Any single mechanism replaces the others. Scanning, signing, and admission enforcement are complementary layers. A signed, scanned image with strict admission policies provides defense-in-depth; any one layer alone is insufficient.

---

## 4.14 Validation Checklist (Admission Policies)

- [ ] All 10 policies deployed in `security-policies` namespace (or equivalent).
- [ ] Each policy tested in `audit-only` mode first; no workloads blocked for 2 weeks.
- [ ] Each policy transitioned to `enforce`/`deny` mode; verified with compliant and non-compliant test workloads.
- [ ] Exemption namespace list includes `kube-system`, `gatekeeper-system`, `kube-public`.
- [ ] Policy ownership documented per policy ( owner, review cadence, exception registry entry).
- [ ] No duplicate enforcement between Kyverno and Gatekeeper — one authoritative source per policy domain.
- [ ] Version-dependent examples marked (Kyverno feature availability, Gatekeeper API version).
- [ ] Safe rollout/rollback procedure documented per policy.
- [ ] Supply-chain concepts (registry allowlisting, digest pinning, Cosign verification) integrated where applicable.
- [ ] Validation command outputs recorded for each policy's compliant/non-compliant test.

---