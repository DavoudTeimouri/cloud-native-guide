# Deliverable — Vault Kubernetes Auth Method

**Path**: `secrets-management/vault/k8s-auth-and-secret-delivery.md`

## Overview

HashiCorp Vault's Kubernetes auth method provides short-lived, dynamic tokens to pods running inside a Kubernetes cluster. Unlike static AppRole secrets, the Kubernetes auth method uses the cluster's service account token volume projection to obtain an JWT, which Vault validates against the Kubernetes API server's Certificate Signing Request (CSR) / token review API. This eliminates long-lived credentials from the threat model and enables per-pod, per-namespace token revocation.

---

## 1. Auth Role Configuration

An **auth role** is the named mapping between a Kubernetes service account and a Vault policy. Each role defines:

- The service account(s) that may authenticate
- The bound audience (aud) claim
- The bound service account name (optional, for exact match)
- The TTL and max TTL for the resulting Vault token
- The associated Vault policy

### Example: `dev-readonly` auth role

```hcl
resource "vault_kubernetes_role" "dev_readonly" {
  name = "dev-readonly"

  # The Kubernetes service account that may authenticate
  bound_service_account_name = "dev-readonly"

  # The JWT audience claim — must match what the KSA token projects
  bound audience = "vault"

  # Service accounts in any namespace that match the name
  user_claim = "kubernetes.io/serviceaccount.name"

  # TTL for the dynamically issued Vault token
  ttl = "1h"
  max_ttl = "24h"

  # Associated Vault policy name
  policy = "dev-readonly"
}
```

**Key points:**

- `bound_service_account_name` enforces exact match; omit to allow any SA with the same name in any namespace.
- `user_claim` controls which JWT claim maps to the identity; `kubernetes.io/serviceaccount.name` is standard.
- `ttl` and `max_ttl` bound the token lifetime — short TTLs reduce the blast radius if a token is compromised.
- The role name is arbitrary but must be referenced by in-cluster clients.

---

## 2. Service Account Binding

For a pod to authenticate to Vault via the Kubernetes auth method, its container must run under a **Kubernetes Service Account** that is bound to the auth role.

### Steps:

1. **Create the Service Account** in the target namespace:

   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: dev-readonly
     namespace: production
   ```

2. **Annotate workloads** to use that service account (or set `serviceAccountName` in the controller specification).

3. **Verify the token is projected** into the pod:

   ```bash
   $ cat /var/run/secrets/kubernetes.io/serviceaccount/token
   eyJhbGciOiJSUzI1NiIsImtpZCI6IjE4azEyNTY ...
   ```

4. **Test authentication** using the Vault CLI:

   ```bash
   $ VAULT_ADDR=http://vault.example.com:8200 vault write -method=kubernetes role=dev-readonly token
   Success! Data returned: token=...
   ```

**Best practice**: Use distinct service accounts per environment (dev/staging/prod) and per workload criticality. Avoid a single shared SA across namespaces unless intentionally designing for broad access.

---

## 3. Secret Injection

Once authenticated, the pod can retrieve secrets from Vault. There are three primary patterns:

### 3.1 Injector (init-container) Pattern

An init-container calls `vault kv get` (or the Vault Agent sidecar) and writes secrets into a K8s Secret or environment variables.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-injector
spec:
  serviceAccountName: dev-readonly
  initContainers:
    - name: inject-secrets
      image: hashicorp/vault:1.16
      command: ["sh", "-c", "vault kv get secret/app-config | jq -r '.data.data | to_entries[] | \"\(.key)=\(.value)\"' > /etc/secrets/env && env -i env")
      volumeMounts:
        - name: etc-secrets
          mountPath: /etc/secrets
  containers:
    - name: app
      image: myapp:latest
      envFrom:
        - secretRef:
            name: app-config
```

### 3.2 Sidecar Pattern (Vault Agent Injector)

The **Vault Agent Injector** (admission controller) automatically injects a sidecar container that runs `vault agent` with a configured template. The sidecar fetches secrets and refreshes them lease-bound.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-sidecar
spec:
  serviceAccountName: dev-readonly
  vault:
    injector:
      enabled: true
      # Configuration injected by the Helm chart / admission webhook
    sidecar:
      containerName: vault
      image: hashicorp/vault:1.16
      resources:
        limits: 100m 200Mi
      env:
        - name: VAULT_ADDR
          value: "http://vault:8200"
      # Template renders secrets as files or env vars
      volumeMounts:
        - name: vault-secret
          mountPath: /vault/secrets
  containers:
    - name: app
      image: myapp:latest
      volumeMounts:
        - name: vault-secret
          mountPath: /etc/app/secrets
  volumes:
    - name: vault-secret
      emptyDir: {}
```

**Result**: The app container reads secrets from `/etc/app/secrets` — files auto-updated by the sidecar as leases renew.

### 3.3 External Secrets Operator (ESO)

ESO bridges Vault to K8s native Secrets. It synchronizes Vault KV paths into K8s `Secret` objects, which applications consume normally.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: app-config-secret
spec:
  secretStoreRef:
    kind: Vault
    name: vault-secret-store
    namespace: vault
  target:
    name: app-config
  data:
    - secretPath: secret/infra/app/config
      literalPath: ""
```

**Advantage**: No application code changes; standard K8s Secret workflows apply. **Trade-off**: One layer of abstraction; ESO must be configured with the correct Vault auth method.

---

## 4. Sidecar Injection Details

The Vault Agent sidecar performs these functions:

1. **Authenticate** using the projected KSA token via the Kubernetes auth method.
2. **Fetch secrets** from the configured Vault KV path.
3. **Render templates** — either write secret data as files or export as environment variables.
4. **Refresh leases** periodically before expiry, using the same auth token (no re-login needed while the token is valid).
5. **Rotate on TTL approach** — as the Vault token TTL nears expiry, the sidecar re-authenticates with the KSA token to obtain a fresh token.

### Sidecar resource template example:

```hcl
# Template: renders secret data as file content
{{- $path := "secret/infra/app/config" -}}
{{- $secret := kv $path -}}
{{- range $key, $value := .data.data -}}
{{- $key | trimSuffix \".\" }}: {{ $value | quote }}
{{- end }}
```

This template, combined with the sidecar's volume mount, produces a file like `/vault/secrets/config` that the application reads.

---

## 5. Secret Delivery Patterns

| Pattern | Use Case | Advantages | Considerations |
|---|---|---|---|
| **Init-container injector** | One-time setup, CI/CD pipelines, ephemeral jobs | No persistent sidecar; simple for short-lived workloads | Secrets written at pod start only; not auto-refreshed |
| **Vault Agent sidecar** | Long-running services needing auto-rotation | Transparent refresh; lease-aware; file or env output | Requires admission controller or Helm; adds a sidecar resource |
| **External Secrets Operator** | Standard K8s Secret consumers, multi-cluster | Uses native K8s Secret API; no app code changes | ESO component adds another control plane; sync latency |
| **Volume projection** | Config as files, not env vars | Secrets appear as regular files; apps read `FILE` env vars pointing to mount paths | Requires app to read files instead of env; mount propagation delays |

**Recommended default**: Use the **Vault Agent sidecar** for long-running workloads (deployments, stateful sets) and **ESO** for stateless services or migrations. Reserve init-container injection for CI/CD and batch jobs.

---

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Error response from daemon: failed to setup child process` | Vault Agent sidecar can't reach K8s API server | Ensure the pod's SA has `aggregate-cluster-admin-reader` or equivalent; check RBAC |
| `authentication failure: cannot parse token` | SA token not projected or wrong `bound_service_account_name` | Verify `serviceAccountName` on the workload; inspect the projected token |
| Secrets not refreshing | Vault token TTL expired; sidecar re-auth failed | Check Vault Agent logs; ensure KSA token is still valid and not revoked |
| `403 for permission denied` | Vault policy doesn't allow the role's path | Attach the correct Vault policy to the auth role; verify `policy` field |

---

## 7. References

- HashiCorp Vault Kubernetes Auth Method documentation: <https://www.vaultproject/docs/auth/kubernetes>
- Vault Agent Injector Helm chart: <https://github.com/hashicorp/vault-helm/tree/main/charts/vault>
- External Secrets Operator Vault secret store: <https://external-secrets.io/vault-docs/>
- Kubernetes Service Account token volumes: <https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/>