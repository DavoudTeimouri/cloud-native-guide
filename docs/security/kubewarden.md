# Kubewarden Deployment Guide

Kubewarden is a policy engine for Kubernetes that uses WebAssembly (Wasm)
policies. Use it as an alternative to OPA Gatekeeper or Kyverno for admission
control, policy enforcement, and security validation.

## Prerequisites

- Kubernetes cluster is deployed and healthy (Phase 1 complete).
- `kubectl` is configured to target the cluster.
- Helm 3 is installed.
- Your cluster supports WebAssembly runtime modules (K8s 1.25+ recommended).

## Step 1 — Add Helm Repository

```bash
helm repo add kubewarden https://charts.kubewarden.io
helm repo update
```

## Step 2 — Create Namespace

```bash
kubectl create namespace kubewarden
```

## Step 3 — Deploy Kubewarden Controller

```bash
helm install kubewarden-crds kubewarden/kubewarden-crds \
  --namespace kubewarden \
  --create-namespace

helm install kubewarden-controller kubewarden/kubewarden-controller \
  --namespace kubewarden \
  --set defaultPolicyExecMode=frontend
```

Wait for readiness:

```bash
kubectl -n kubewarden rollout status deployment/kubewarden-controller --timeout=300s
```

## Step 4 — Deploy Default Admission Policy

Apply a built-in policy from the Kubewarden policy store:

```yaml
# policy-psp-disallow-proxy.yaml
apiVersion: policies.kubewarden.io/v1
kind: ClusterAdmissionPolicy
metadata:
  name: psp-disallow-proxy
spec:
  module: "registry://ghcr.io/kubewarden/policies/psp-disallow-proxy:v0.2.0"
  rules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE"]
      resources: ["pods"]
  settings:
    annotations:
      - "security.openshift.io/scc.podName"
      - "openshift.io/sa.scc.mcs"
      - "openshift.io/sa.scc.supplemental-groups"
      - "openshift.io/sa.scc.uid-range"
      - "openshift.io/sa.scc.range"
```

```bash
kubectl apply -f policy-psp-disallow-proxy.yaml
```

## Step 5 — Apply Mutator Policies (Optional)

Mutator policies modify resources on admission (e.g., inject labels,
annotations, or sidecar containers):

```yaml
# mutator-example.yaml
apiVersion: policies.kubewarden.io/v1
kind: MutatorPolicy
metadata:
  name: inject-sidecar
spec:
  module: "registry://ghcr.io/kubewarden/policies/inject-sidecar:v0.1.0"
  rules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE"]
      resources: ["pods"]
  settings:
    sidecar:
      image: "ghcr.io/kubewarden/policy-sidecar:latest"
      name: "policy-sidecar"
```

```bash
kubectl apply -f mutator-example.yaml
```

## Step 6 — Validate Policy Enforcement

```bash
# All Kubewarden components running
kubectl -n kubewarden get pods

# Policy is active
kubectl get clusteradmissionpolicy psp-disallow-proxy

# Test policy: this pod should be REJECTED
kubectl run --rm -i --tty --image=nginx test-pod -- \
  --annotations="security.openshift.io/scc.podName=test" 2>&1 | head -20
```

## Validation Commands

```bash
# Kubewarden controller healthy
kubectl -n kubewardan get deployment kubewarden-controller

# Policies loaded
kubectl get clusteradmissionpolicies

# Policy events
kubectl get events -n kubewarden --sort-by=.lastTimestamp
```

## Rollback

```bash
kubectl delete clusteradmissionpolicy psp-disallow-proxy
kubectl delete mutatorpolicy inject-sidecar
helm uninstall kubewarden-controller -n kubewarden
helm uninstall kubewarden-crds -n kubewarden
kubectl delete namespace kubewarden
```

> **Note:** Kubewarden policies run in WebAssembly. If your nodes cannot run
> Wasm modules, use OPA Gatekeeper or Kyverno instead (see
> `docs/security/pod-security-standards.md` for OPA Gatekeeper integration).
