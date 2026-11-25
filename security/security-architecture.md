# Security Architecture & Policy Responsibilities

*Illustrative only — not production-committed configurations. Marked as such where indicated.*

This document documents the responsibilities and enforcement boundaries of security controls across the Kubernetes platform. Each control is classified by its enforcement layer and mapped to the defense-in-depth strata: admission-time, network, runtime, supply-chain, and external integrations. No control is claimed to enforce policy in isolation; all rely on layered responsibility.

---

## Control Layer Overview

| Control | Classification(s) | Primary Enforcement Layer |
|---|---|---|
| Pod Security Standards | Native Kubernetes | Admission-time |
| Kyverno policies | Admission-time enforcement | Admission-time |
| OPA Gatekeeper constraints | Admission-time enforcement | Admission-time |
| Kubernetes RBAC | Native Kubernetes | Admission-time / API server |
| Kubernetes NetworkPolicy | Native Kubernetes | Network enforcement |
| Cilium NetworkPolicy | CNI extension | Network enforcement |
| Cosign image provenance | Supply-chain verification | Supply-chain |
| Vault/OpenBao secret management | External security integrations | Runtime / startup |
| Falco runtime detection | Runtime detection | Runtime |
| Trivy image/artifact scanning | Supply-chain verification | Supply-chain |

---

## 1. Kubernetes Pod Security Admission and Pod Security Standards

**Classification**: Native Kubernetes / Admission-time enforcement

The Pod Security Standards (PSS) framework replaces the deprecated Pod Security Policy (PSP). Three profiles are available, applied at the namespace label level:

- **`privileged`**: No restrictions; workloads have full host access.
- **`baseline`**: Moderate restrictions; precursor to `restricted`.
- **`restricted`**: Strongest default profile; closest to CIS Kubernetes benchmark.

**Responsibility boundary**: The `pod-security.kubernetes.io/enforce` namespace label triggers the `defaulting` admission webhook in `kube-apiserver`. The label alone is only an audit signal — enforcement requires the admission webhook or a complementary admission controller (e.g., Kyverno, Gatekeeper).

**Illustrative example** — enforce `restricted` across all non-control-plane namespaces:

```bash
# Label namespaces; kube-system and kube-privileged remain privileged
kubectl label --overwrite ns default pod-security.kubernetes.io/enforce=restricted
kubectl label --overwrite ns kube-system pod-security.kubernetes.io/enforce=privileged
kubectl label --overwrite ns kube-public pod-security.kubernetes.io/enforce=privileged
```

Enforced `restricted` profile implies: `allowPrivilegeEscalation: false`, `runAsNonRoot: true`, `seccompProfile.type: RuntimeDefault`, `capabilities.drop: ["ALL"]`, and no `hostPath`, `hostNetwork`, `hostPID`, or `privileged` fields.

**Verification**: `kubectl get pod <name> -o yaml` — restricted-profile pods must have `runAsNonRoot: true` and `seccompProfile.type` set. Privileged pods in a restricted namespace are rejected at admission.

**Do not imply**: The namespace label alone enforces policy. The admission webhook must be active and accepting requests.

---

## 2. Kyverno (admission-time policy)

**Classification**: Admission-time enforcement

Kyverno is a Kubernetes-native policy engine that operates as an admission webhook. It natively understands Kubernetes resources (CRDs, Deployments, Jobs, etc.) and writes policies in YAML/JSON using pattern matching, validation, mutation, and generation.

**Responsibility boundary**: Kyverno policies are evaluated during `create`, `update`, and `delete` operations against the API server. A `validationFailureAction: Enforce` (default `Fail`) determines whether the webhook rejection blocks the operation or allows it with a warning. Unlike OPA Gatekeeper, Kyverno policies do not require Rego — they use Kubernetes-native pattern matching.

**Illustrative example** — require image digests for all container images:

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
              kinds: ["Pod"]
      validate:
        message: "Images must be pinned by digest and come from harbor.internal"
        pattern:
          spec:
            containers:
              - image: "harbor.internal/*@sha256:*"
```

**Key distinction from Gatekeeper**: Kyverno policies are Kubernetes-native YAML; no Rego learning curve. Gatekeeper uses Rego templates. Both can coexist — Kyverno handles image provenance and resource mutation; Gatekeeper enforces structural constraints (e.g., PSP replacement, label requirements). Avoid duplicate rules by assigning Kyverno image-related policies and Gatekeeper structural policies.

**Verification**: `kyverno policy list --all` — verify the policy is loaded. Trigger a violating resource create and confirm rejection.

---

## 3. Open Policy Agent Gatekeeper (admission-time policy, OPA constraints)

**Classification**: Admission-time enforcement

Gatekeeper extends the Kubernetes API server with validating/admission webhooks backed by OPA. Policies are expressed as Rego constraint templates and constraints. Gatekeeper supports structural constraints (pod shapes, resource limits) and behavioral constraints (label requirements, annotation checks).

**Responsibility boundary**: Gatekeeper constraints aremutated into MutatingWebhook/ValidatingWebhook configurations by the Gatekeeper controller. The `validatingWebhookFailurePolicy` setting is critical: `Fail` blocks writes when Gatekeeper is down or misconfigured; `Ignore` lets writes through. For application namespaces, `Fail` is recommended; for platform namespaces, `Ignore` with a documented exception process.

**Illustrative example** — block privileged containers:

```yaml
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
  parameters:
    exemptNamespaces: ["kube-system", "gatekeeper-system"]
```

**Key distinction from Kyverno**: Gatekeeper uses Rego; Kyverno uses pattern-matching YAML. Gatekeeper is better suited for structural/orchestration constraints; Kyverno excels at image verification and resource mutation. Do not duplicate the same rule in both engines — assign one authoritative source per policy domain.

**Verification**: `kubectl get constrainttemplates -A` and `kubectl get constraints -A` — confirm the constraint is loaded. Test with a violating Pod create and confirm denial.

---

## 4. Kubernetes RBAC

**Classification**: Native Kubernetes / Admission-time enforcement

Kubernetes RBAC (Role-Based Access Control) regulates who can perform what actions within the cluster. It is enforced by the `kube-apiserver` via `Role`, `ClusterRole`, `RoleBinding`, and `ClusterRoleBinding` objects. RBAC operates at the API server layer — every `kubectl` command, API request, and internal service communication is checked against the RBAC ruleset.

**Responsibility boundary**: RBAC decisions are binary: allowed or denied. There is no partial enforcement. The `cluster-admin` ClusterRole grants unrestricted access; all other roles must be explicitly assigned. The `system:authenticated` and `system:anonymous` groups provide baseline access; these should be narrowed in production.

**Illustrative example** — minimal role for pod management in a namespace:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-manager
  namespace: team-alpha
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/exec", "pods/portforward"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

**Critical**: `pods/exec` and `pods/portforward` provide shell-like access to the node; these must be restricted via RBAC andNetworkPolicy where possible. Grant only the verbs required for the workload's operation.

**Verification**: `kubectl auth can-i <verb> <resource> --namespace=<ns> --as=<user>` — test each intended privilege. Run `kubectl auth can-i '*' '*' --all-namespaces` as various users to verify the access boundary.

---

## 5. Kubernetes NetworkPolicy

**Classification**: Native Kubernetes / Network enforcement

Kubernetes NetworkPolicy objects express allow/deny rules for traffic between pods and across namespaces. The default is to allow all traffic (no NetworkPolicy = unrestricted). NetworkPolicy rules are evaluated by the CNI plugin in use; not all plugins support the full API.

**Responsibility boundary**: NetworkPolicy is the primary traffic-control layer between namespaces and between pods. It operates at layer 3/4 (IP/port) and, with CNI extensions, layer 7 (HTTP/HTTPS). A namespace with no NetworkPolicy accepts traffic from any other namespace. NetworkPolicies are additive — if any policy exists in a namespace, the default-allow is replaced by explicit rules.

**Illustrative example** — allow only HTTP/HTTPS traffic from `frontend` to `backend` namespace:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443
  egress: []  # explicit deny of egress unless added
```

**Key integration**: Cilium NetworkPolicy (see next section) extends native Kubernetes NetworkPolicy with L7 filtering, identity-based policies, and BPF-based traffic enforcement. Cilium can native-k8s NetworkPolicy-compatible mode, but full capabilities require Cilium CRDs.

**Verification**: `kubectl get networkpolicy -A` — list all policies. `kubectl describe networkpolicy <name> -n <ns>` — inspect rules. Use `tcpdump` or CNI-specific diagnostics to confirm enforced behavior.

---

## 6. Cilium Network Policy and Cilium Security Capabilities

**Classification**: Network enforcement / External security integrations

Cilium provides a CNI and Kubernetes device plugin that replaces or augments `kube-proxy` and `kube-dns`. Cilium NetworkPolicy (CNM/BPF-based) offers L3/L4 and L7 traffic filtering with identity-based semantics (labels, not just pod selectors). Cilium also provides service mesh capabilities (mTLS), endpoint security, and observability.

**Responsibility boundary**: Cilium NetworkPolicy can operate in native-k8s compatibility mode, but its full feature set (L7 protocols, service mesh, socket-level security) is exclusive to Cilium. When Cilium is the cluster CNI, native Kubernetes NetworkPolicy rules are still honored, but Cilium adds richer filtering and identity tracking.

**Illustrative example** — Cilium NetworkPolicy with L7 HTTP path filtering:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-http-path
  namespace: default
spec:
  egress:
    - toports:
        - ports: ["443"]
          http:
            methods: ["GET", "HEAD"]
            paths: ["/api/*"]
  ingress:
    - fromEndpointSelector:
        matchLabels:
          app: ingress
    - toports:
        - ports: ["8080"]
          into:
            ports: ["8080"]
```

**Key distinction from native NetworkPolicy**: Cilium enforces L7 protocol awareness, can track east-west traffic across cluster mesh, and integrates with Hubble for visibility. Native Kubernetes NetworkPolicy is a subset — if Cilium is present, it is the enforcement engine for both.

**Verification**: `cilium policy list` — display active Cilium policies. `hubble observe` — live traffic flow view. Confirm that expected traffic flows and that denied traffic is blocked at the BPF level.

---

## 7. Image Signature and Provenance Verification (Cosign)

**Classification**: Supply-chain verification

Cosign (from the Sigstore project) provides signing and verification of container images and other artifacts. It integrates with OCI registries (Harbor, GitHub Container Registry, etc.) and signs images by digest using key transparency and PKI. Verification is `cosign verify --key <public-key> <image@digest>`.

**Responsibility boundary**: Cosign operates outside the Kubernetes cluster — typically in CI pipelines or local developer workflows. It does not prevent an unsigned image from being pushed to a registry, but it can block deployment of unverified images via admission controllers (e.g., Kyverno `verifyImages`, Gatekeeper constraints, or custom webhooks). Verification must happen before the image is pulled for deployment.

**Illustrative example** — sign an image and verify:

```bash
# Sign the image
cosign sign --key cosign.key myimage@sha256:abc123...

# Verify the image
cosign verify --key cosign.pub myimage@sha256:abc123...
```

**In deployment pipeline** — example Kyverno policy that verifies image signatures before allowing deployment:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-images
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-signed-image
      match:
        any:
          - resources:
              kinds: ["Pod"]
      validate:
        message: "Image must be signed and verified"
        pattern:
          spec:
            containers:
              - image: "registry.internal/*@sha256:*"
              # Additional verification can be wired via Kyverno's verifyImages feature
```

**Do not imply**: Cosign alone secures the runtime. It is a supply-chain gate; runtime security (Falco, runtime admission controllers) is separate.

**Verification**: `cosign verify-image <image@digest>` — confirm signature validation. In CI, ensure the pipeline step exits non-zero for unsigned images.

---

## 8. Secret Management through Vault/OpenBao

**Classification**: External security integrations

HashiCorp Vault (or OpenBao, the open-source fork) provides dynamic secret generation, leasing, and revocation. Secrets are not stored in etcd or environment variables; they are fetched at runtime via the Vault Agent sidecar or init container. Vault supports database credentials, SSH keys, TLS certificates, and generic key-value secrets.

**Responsibility boundary**: Vault itself is an external service — compromise of the Vault server exposes all managed secrets. The Kubernetes integration (Vault Agent, External Secrets Operator) fetches secrets at pod startup and renews leases. Secrets cached in environment volumes must be rotated via leases; static secrets in ConfigMap or etcd are outside Vault's scope.

**Illustrative example** — Vault Agent sidecar injecting a database credential:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-vault
spec:
  containers:
    - name: app
      image: myapp:latest
      env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: vault-token
              key: db-password
    - name: vault-agent
      image: hashicorp/vault:latest
      args: ["server", "-config=/vault/config/vault-agent.json"]
      volumeMounts:
        - name: vault-config
          mountPath: /vault/config
        - name: vault-token
          mountPath: /vault/secrets
  volumes:
    - name: vault-config
      configMap:
        name: vault-agent-config
    - name: vault-token
      emptyDir: {}
```

**Vault-agent config** (`vault-agent.json`):

```json
{
  "address": "https://vault.example.com:8200",
  "role": "app-role",
  "auth": {
    "kubernetes": {
      "role": "my-app-role",
      "jwt": "/var/run/secrets/kubernetes.io/serviceaccount/token"
    }
  },
  "secret_paths": ["db/creds/app"],
  "outgoing_interfaces": {
    "dns": ["eth0"]
  },
  "transformers": [{"type": "jwt", "lease": "30s"}],
  " secret_transfer": {
    "default_mode": "environment"
  }
}
```

**Do not imply**: Vault eliminates secret rotation risk. Dynamic secrets have TTLs; leases must be renewed. Static secrets loaded into pods outside Vault are outside its control. Vault HA, sealing, and backup are infrastructure concerns outside this document's scope.

**Verification**: `kubectl exec <pod> -c vault-agent -- sh -c 'printenv DB_PASSWORD'` — confirm the secret is present at runtime but absent from the image. Test secret revocation by rotating the Vault lease and confirming pod restart picks up the new value.

---

## 9. Runtime Detection through Falco

**Classification**: Runtime detection

Falco watches kernel system calls and container runtime events to detect anomalous behavior at runtime. It runs as a DaemonSet on each node and exports events to a variety of sinks (stdout, syslog, Prometheus, Kafka). Default rules are extensive but noisy; a tuned ruleset is required for production use.

**Responsibility boundary**: Falco does not enforce policy or block actions. It detects and reports runtime deviations (e.g., shell in a container, writes to `/etc`, unexpected network connections). Detection events are surfaced to security teams or SIEM; they do not prevent the action that triggered them.

**Responsibility boundary clarification**: Falco is detection, not admission-time enforcement. A process that writes to `/etc/passwd` inside a container continues to run; Falco raises an alert after the fact. Admission-time controls (PSS, Kyverno, Gatekeeper) prevent the container from being scheduled with privileged capabilities; Falco alerts if those controls are bypassed or misconfigured.

**Illustrative example** — tuned Falco rule: shell spawned inside a container:

```yaml
- rule: Shell in container
  desc: Shell spawned inside a container
  condition: container and evt.type=execve and fd.name contains "sh"
  output: "Suspicious shell in container (user=%user.name container=%container.name command=%fd.name)"
  priority: warning
  tags: [runtime, detective]
```

**Tuning guidance**: Retire default rules that fire on package managers (`apk`, `apt`, `yum`), container startup, and legitimate init processes. Keep rules for: writes to `/etc`, `/usr/bin`, `/var/lib/ceph`; `setuid`/`setgid` binaries; Kubernetes API token reads from containers; outbound connections to known-bad IP addresses (via integration with threat intelligence).

**Verification**: `kubectl port-forward svc/falco 8666:8666` and `curl http://localhost:8666/events` — stream events. Trigger a rule (e.g., `touch /etc/test-falco` in a running container) and confirm the event appears.

---

## 10. Image and Artifact Scanning through Trivy

**Classification**: Supply-chain verification

Trivy scans container images and filesystem layers for known vulnerabilities (CVEs), misconfigurations, and secrets. It supports scanning by digest (recommended) or tag, and integrates with CI pipelines, Kubernetes operators, and local developer workflows. Trivy does not prevent deployment of vulnerable images; it reports findings. Policy-as-code (e.g., `trivy config --exit-on-severity CRITICAL`) can be used to gate CI/CD.

**Responsibility boundary**: Trivy is a scanning/reporting tool. It does not enforce runtime policy. A clean scan does not guarantee a runtime-free image; a scanned image may receive new CVEs between scan and deployment. Scanning must be integrated into the CI pipeline as a gate, and images with critical/high findings must not be promoted without review and remediation.

**Illustrative example** — scan an image for critical/high CVEs:

```bash
trivy image --severity CRITICAL,HIGH myimage@sha256:abc123...
```

**CI pipeline integration** — gate promotion on critical findings:

```yaml
# GitHub Actions example
- name: Scan image with Trivy
  run: |
    trivy image --severity CRITICAL,HIGH --exit-code 1 myimage@sha256:abc123...
```

**Do not imply**: A Trivy-clean image is exploit-free. Trivy checks known CVAs at scan time; zero-days, runtime configuration, and environment-specific risks are outside its scope.

**Verification**: Run `trivy image --severity 0 myimage@sha256:abc123...` — confirm no vulnerabilities are reported for a known-clean image. Run against an image with known vulnerabilities and confirm they are detected. Integrate into a CI step and confirm the pipeline fails on CRITICAL findings.

---

## Validation (Mandatory Subset)

The following minimum controls must be verified in any deployment:

- [ ] Privileged pod denied via Pod Security Standards (or equivalent admission controller)
- [ ] Gatekeeper constraint enforced (or Kyverno equivalent) in application namespaces
- [ ] Falco test alert raised for a tuned rule (shell in container, write to /etc)
- [ ] CRITICAL image blocked in CI (Trivy exit-code 1 on critical findings)
- [ ] Cosign verification passes for signed images and fails for unsigned
- [ ] No secrets found in Git (gitleaks or equivalent)
- [ ] TLS scan clean (no deprecated protocols, weak ciphers)
- [ ] Break-glass login works with the IdP down (documented exception process)

**Verification**: Run the mandatory subset checks in a staging environment before promoting to production. Document any accepted deviations with rationale and monitoring.

---

## What This File Is NOT

- A deployment guide for any single tool. Each control has its own documentation; this file maps responsibilities and boundaries.
- A claim that any single control enforces policy in isolation. All controls are layered — overlap is intentional, not accidental.
- A substitute for vendor-specific documentation on version compatibility, HA, or upgrade paths.

*Next steps*: Validate each control in a staging cluster. Document accepted deviations. Integrate scanning and enforcement into the CI/CD pipeline. Track findings by severity and time-to-remediate.