# Admission Policy

## A. Purpose and scope

Document admission policy implementation: OPA Gatekeeper constraints, Kyverno policies, validation failure actions.

Cross-references `security/pod-security-standards.md`, `kubernetes/security/security-controls.md` §Admission control.

## B. OPA Gatekeeper

OPA Gatekeeper enforces policies via ConstraintTemplates and Constraints:

```yaml
# Constraint template for required labels
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
  targets:
    - target: admission.k8s.io
      rego: |
        package k8srequiredlabels

        violation[{"msg": msg, "details": {}}] {
          label := input.review.object.metadata.labels[required_label]
          not label
          msg := sprintf("You must set a %v label", [required_label])
        }

---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-app-label
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  parameters:
    required_label: app
    message: "Pods must have an app label"
```

## C. Kyverno

Kyverno policies are Kubernetes-native:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-non-root
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-run-as-non-root
      match:
        any:
          - resources:
              kinds: ["Pod"]
      validate:
        message: "Containers must run as non-root"
        pattern:
          spec:
            containers:
              - (securityContext):
                  runAsNonRoot: true
```

## D. Validation failure actions

| Action | Behavior |
|--------|----------|
| Enforce | Block the request |
| Warn | Allow the request, emit warning |
| Audit | Allow the request, record audit event |

## E. Cross-references

- `security/pod-security-standards.md` — Pod Security Standards
- `kubernetes/security/security-controls.md` §Admission control — Admission control overview
- `kubernetes/control-plane/index.md` — Control plane
