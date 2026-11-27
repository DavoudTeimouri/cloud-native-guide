# Kubernetes Auth Method Configuration

## Purpose

Document Vault's Kubernetes auth method configuration for in-cluster workload identity. This governs how Kubernetes service accounts map to Vault roles and obtain short-lived tokens.

## Kubernetes Auth Method

Enable the Kubernetes auth method:

```bash
vault auth enable kubernetes
```

Configure the Kubernetes auth method with the cluster's CA certificate and API server URL. The following parameters are required:

| Parameter | Description |
|---|---|
| `kubernetes_host` | URL of the Kubernetes API server (e.g. `https://kubernetes.default.svc`) |
| `kubernetes_ca_cert` | CA certificate for TLS verification of the API server |
| `kubernetes_service_account_token` | Path to the service account token (optional, for bootstrap) |
| `token_review_jwt` | JWT for token review requests to the API server |

## Auth Role

Create a Kubernetes auth role that binds a service account to a Vault policy. The role defines which service accounts can authenticate and what permissions they receive.

```bash
# Write a policy first (if not already created)
vault policy write readonly policy/readonly.hcl
```

```bash
# Create the auth role binding a service account to the policy
vault write auth/kubernetes/role/platform \
  bound_service_account_names=platform-app \
  bound_service_account_namespaces=platform \
  policies=readonly \
  ttl=24h \
  audience=vault
```

### Role parameters

| Parameter | Required | Description |
|---|---|---|
| `bound_service_account_names` | yes | Comma-separated list of service account names that can authenticate |
| `bound_service_account_namespaces` | yes | Comma-separated list of namespaces where the above SAs reside |
| `policies` | yes | Comma-separated list of Vault policies to assign |
| `ttl` | no | Maximum token time-to-live; defaults to system max |
| `max_ttl` | no | Maximum allowed TTL; cannot exceed system max |
| `audience` | no | Audience claim to validate in token requests |

### Example: Restricted role with short TTL

```bash
vault write auth/kubernetes/role/api-reader \
  bound_service_account_names=api-reader \
  bound_service_account_namespaces=production,staging \
  policies=api-reader \
  ttl=10m \
  max_ttl=15m
```

## Service Account

Workloads authenticate to Vault by presenting a Kubernetes service account token. The token is exchanged via the Kubernetes TokenReview API for a Vault token.

### Creating the service account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-reader
  namespace: production
  annotations:
    # Optional: configure token lifetime
    vault.hashicorp.com/role: api-reader
```

### Token review mechanism

When a workload presents a service account token, Vault's Kubernetes auth method performs a `TokenReview` against the Kubernetes API server:

1. The workload mounts its service account token at `/var/run/secrets/kubernetes.io/serviceaccount/token`
2. The application calls `vault token create` or uses the Vault Agent Injector/CSI driver
3. Vault sends a `TokenReview` request to the Kubernetes API server:
   ```json
   {
     "apiVersion": "authentication.k8s.io/v1",
     "kind": "TokenReview",
     "spec": {
       "token": "<presented-token>"
     }
   }
   ```
4. Kubernetes validates the token and returns:
   - `status.authenticated: true/false`
   - `status.user.username`: the service account name (`<namespace>/<name>`)
   - `status.user.uid`: the service account UID
   - `status.user.groups`: the service account groups

The token review is the core mechanism that ties Kubernetes identity to Vault access. Without a valid token review, no Vault token is issued.

### Verifying token review is functional

```bash
# Check the Kubernetes API server's token review endpoint
kubectl get apiservers.authorization.k8s.io

# Example TokenReview request
cat <<'EOF' | kubectl apply -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: <service-account-token>
EOF
```

## Workload Identity (Kubernetes 1.24+)

For clusters running Kubernetes 1.24+, projected service account tokens can be used. These tokens are automatically managed and have shorter lifetimes, reducing the risk of token theft.

### Projected token configuration

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-reader
  namespace: production
  annotations:
    kubernetes.io/service-account.name: api-reader
    # Project the token into the container volume
    volumes:
      - name: sa-token
        projected:
          sources:
            - serviceAccountToken:
                name: api-reader
                mountPath: /var/run/sa
```

The projected token is automatically refreshed by the Kubelet and presented to Vault's Kubernetes auth method via the TokenReview API.

## Cross-references

- `secrets-management/vault/vault-architecture.md` — Overall Vault deployment architecture and identity integration
- `secrets-management/vault/access-control.md` — Auth methods, roles, policies, and token policies
- `secrets-management/kubernetes-integration/secret-delivery.md` — Secret delivery to workloads via Vault
- `kubernetes/security/security-controls.md` — Kubernetes security controls including audit policy for token reviews

## Key Points

- **Auth role** binds a Kubernetes service account to a Vault policy, controlling what permissions the workload receives
- **Service account** is the Kubernetes identity that workloads present via their mounted token
- **Token review** is the Kubernetes API mechanism that validates the service account token and passes the identity to Vault
- All three components (auth role, service account, token review) must be correctly configured for in-cluster workloads to authenticate to Vault without static credentials