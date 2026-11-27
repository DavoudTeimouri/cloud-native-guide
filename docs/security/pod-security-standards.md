# Pod Security Standards

## A. Purpose and scope

Document Pod Security Standards (PSS) implementation for the platform: restricted/baseline/privileged profiles per namespace, admission enforcement, and exceptions process.

Cross-references `kubernetes/security/security-controls.md` §Pod Security Standards, `kubernetes/networking/network-policy-examples.md`, `kubernetes/control-plane/index.md` §Security.

## B. Pod Security Standards profiles

| Profile | Description | Use case |
|---------|-------------|----------|
| `privileged` | Unrestricted, widest range of permissions | System workloads (CNI, storage, monitoring agents) |
| `baseline` | Minimally restrictive, prevents known privilege escalations | Most applications |
| `restricted` | Heavily restricted, follows pod security best practices | General workloads, default |

## C. Namespace-level enforcement

Apply PSS at the namespace level via labels:

```bash
# Cluster-wide defaults
kubectl label --overwrite ns default pod-security.kubernetes.io/enforce=restricted
kubectl label --overwrite ns default pod-security.kubernetes.io/enforce-version=latest
kubectl label --overwrite ns default pod-security.kubernetes.io/audit=restricted
kubectl label --overwrite ns default pod-security.kubernetes.io/warn=restricted

kubectl label --overwrite ns kube-system pod-security.kubernetes.io/enforce=privileged
kubectl label --overwrite ns kube-system pod-security.kubernetes.io/enforce-version=latest
kubectl label --overwrite ns kube-public pod-security.kubernetes.io/enforce=privileged
kubectl label --overwrite ns kube-public pod-security.kubernetes.io/enforce-version=latest

# Application namespaces use restricted by default
kubectl label --overwrite ns <app-namespace> pod-security.kubernetes.io/enforce=restricted
kubectl label --overwrite ns <app-namespace> pod-security.kubernetes.io/enforce-version=latest
```

The `kube-system` and `kube-public` namespaces stay at `privileged` because CNI and control-plane components require it. Every other namespace is `restricted`.

## D. Enforce with admission policy

The PSS label is only an audit signal by itself. Enforce with an admission controller (OPA Gatekeeper or Kyverno):

```yaml
# OPA Gatekeeper constraint template
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sPSPPrivilegedContainer
metadata:
  name: block-privileged
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    excludedNamespaces: ["kube-system", "gatekeeper-system"]
  parameters:
    exemptNamespaces: ["kube-system", "gatekeeper-system"]
```

```yaml
# Kyverno ClusterPolicy
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

## E. Restricted profile requirements

The `restricted` profile means:

- `allowPrivilegeEscalation: false`
- `runAsNonRoot: true`
- `seccompProfile.type: RuntimeDefault` or `Localhost`
- `capabilities.drop: ["ALL"]`
- No `hostPath`, no `hostNetwork`, no `hostPID`, no `hostIPC`
- No `privileged: true` containers

## F. Exceptions process

Workloads needing less than `restricted` run in their own namespace with the correct label — not with a cluster-wide exemption:

```bash
# Create namespace for workloads needing baseline
kubectl create ns <baseline-ns>
kubectl label ns <baseline-ns> pod-security.kubernetes.io/enforce=baseline
kubectl label ns <baseline-ns> pod-security.kubernetes.io/enforce-version=latest
```

All exceptions require:
1. Documented reason
2. Compensating control
3. Owner assignment
4. Review date

## G. Validation

```bash
# Check PSS labels on all namespaces
kubectl get ns --show-labels | grep pod-security

# Test that privileged pods are denied in restricted namespaces
kubectl run test-privileged --image=busybox --restart=Never --privileged -n <restricted-ns> --dry-run=client -o yaml | kubectl apply -f -

# Check admission controller enforcement
kubectl get gatekeeperconstraints  # or kyverno policies
```

## H. Cross-references

- `kubernetes/security/security-controls.md` §C — Pod Security Standards
- `kubernetes/networking/network-policy-examples.md` — NetworkPolicy for restricted namespaces
- `kubernetes/control-plane/index.md` §Certificate lifecycle — API server security
- `security/host-baseline.md` — Host CIS baseline
