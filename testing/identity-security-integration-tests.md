# Section 8: Identity/Secrets/Access Integration Tests

**Purpose**: Cross-component tests for identity federation, secrets management, and access control integration across the platform. All tests are designed against ephemeral/lab clusters only — no live or shared clusters are used.

> **Important**: Auth success does not imply authorization correctness. Sensitive values (passwords, tokens, secrets) must never appear in test output or evidence. Mask or omit all secrets from recorded output.

---

## 8.1 Keycloak OIDC Authentication Integration

| Field | Details |
|---|---|
| **Test ID** | ID-001 |
| **Scope** | Keycloak OIDC authentication flow against a lab Keycloak instance |
| **Positive Test** | |
| **Preconditions** | Keycloak is running; client registration is configured; redirect URI is validated; TLS is trusted |
| **Test Command** | `curl -s -X POST /auth/realms/master/protocol/openid-connect/token -H "Content-Type: application/x-www-form-urlencoded" -d "username=testuser&password=testpass&grant_type=password&client_id=my-client"` |
| **Expected Output** | JSON Web Token (JWT) is issued; token contains expected `sub`, `aud`, `exp` claims; `access_token` field present |
| **Failure Condition** | Invalid credentials; token not issued; `invalid_grant` error; TLS handshake failure against Keycloak |
| **Remediation** | Verify client configuration in Keycloak; check username/password; ensure TLS CA is trusted for the Keycloak endpoint |
| **Evidence** | JWT header and payload (non-sensitive claims only: `alg`, `typ`, `sub`, `aud`, `exp`, `iat`); token issuance output |
| **Automated** | Yes — OAuth2 client library scripted; assert token fields and expiry |
| **Manual** | Yes — `curl` to token endpoint; inspect JWT at jwt.io (redact sensitive fields) |

---

## 8.2 Negative Authentication Test (ID-001-NEG)

| Field | Details |
|---|---|
| **Test ID** | ID-001-NEG |
| **Scope** | Keycloak authentication with invalid credentials |
| **Preconditions** | Same as positive; but incorrect username or password |
| **Test Command** | `curl -s -X POST /auth/realms/master/protocol/openid-connect/token -H "Content-Type: application/x-www-form-urlencoded" -d "username=invalid&password=wrong&grant_type=password&client_id=my-client"` |
| **Expected Output** | `invalid_grant` error response; no token issued; HTTP 400 or 401 |
| **Failure Condition** | Invalid credentials accepted — indicates authentication bypass |
| **Remediation** | Verify Keycloak realm configuration; check user existence and password; enable account lockout if brute-force is a concern |
| **Evidence** | Error response JSON (no sensitive data); `curl` exit code |
| **Automated** | Yes — scripted token request with assert on `invalid_grant` |
| **Manual** | Yes — manual `curl` with error capture |

---

## 8.3 OIDC ID Token Claims Validation

| Field | Details |
|---|---|
| **Test ID** | ID-002 |
| **Scope** | Validation of OIDC ID token claims (audience, issuer, expiry) |
| **Positive Test** | |
| **Preconditions** | JWT received from Keycloak; public key is available for signature verification |
| **Test Command** | Decode and verify JWT: `jwt.io` or `openssl`/`jq` with Keycloak's public key; verify `iss` matches Keycloak server URL; verify `aud` matches client ID; verify `exp` is in the future |
| **Expected Output** | All claims validate; signature verification passes; no claim mismatches |
| **Failure Condition** | `iss` mismatch; `aud` mismatch; `exp` in the past; signature verification fails |
| **Remediation** | Verify Keycloak realm URL; re-register client if client ID changed; rotate keys if signature verification fails |
| **Evidence** | Claim validation output (claim names only, values masked if sensitive); `jq` or `openssl` verification output |
| **Automated** | Yes — JWT library scripted with claim assertions |
| **Manual** | Yes — inspect JWT at jwt.io; manually verify each claim |

---

## 8.4 Rancher Authentication Integration

| Field | Details |
|---|---|
| **Test ID** | ID-003 |
| **Scope** | Rancher API authentication (Bearer token or kubeconfig generation) |
| **Positive Test** | |
| **Preconditions** | Rancher server is running; API token is configured or kubeconfig is generated; TLS is trusted |
| **Test Command** | `curl -s -H "Authorization: Bearer <rancher-token>" https://rancher.example.com/v3/currentUser` |
| **Expected Output** | JSON with current user information; HTTP 200; user ID and roles returned |
| **Failure Condition** | Token rejected; 401 Unauthorized; TLS handshake failure |
| **Remediation** | Verify API token; regenerate kubeconfig; check Rancher server health; ensure TLS CA is trusted |
| **Evidence** | `curl` output (user fields only; mask secrets); HTTP status code |
| **Automated** | Yes — `curl` scripted with JSON parsing and user field assertion |
| **Manual** | Yes — `curl` with visual inspection of user info |

---

## 8.5 Kubernetes RBAC Authorization

| Field | Details |
|---|---|
| **Test ID** | ID-004 |
| **Scope** | K8s RBAC: authorized and unauthorized actions against the API server |
| **Positive Test** | |
| **Preconditions** | RBAC rules are configured in K8s API server; user/serviceAccount has specified permissions; TLS is to the K8s API |
| **Test Command** | `kubectl --as=user:get pods --namespace=default get pods` (if user has `get pods` permission) |
| **Expected Output** | List of pods in namespace; HTTP 200 from API server; pod names returned |
| **Failure Condition** | `Error: pods is forbidden: User "user" cannot get pods at the namespace level`; 403 Forbidden |
| **Remediation** | Review RBAC ClusterRole/Role bindings; add or adjust permissions; check `aggregateclusterroles` if using custom roles |
| **Evidence** | `kubectl` output (resource names only; no secrets); API server audit log entry |
| **Automated** | Yes — `kubectl` commands scripted with assert on output or error |
| **Manual** | Yes — manual `kubectl --as=` with observation of authorization result |

---

## 8.6 Negative RBAC Authorization Test (ID-004-NEG)

| Field | Details |
|---|---|
| **Test ID** | ID-004-NEG |
| **Scope** | K8s RBAC: unauthorized action should be denied |
| **Preconditions** | Same as positive; but the user/serviceAccount does not have the requested permission |
| **Test Command** | `kubectl --as=another-user get pods --namespace=system` |
| **Expected Output** | `Error: pods is forbidden: User "another-user" cannot get pods at the namespace level`; HTTP 403; resource not listed |
| **Failure Condition** | Unauthorized action passes through — indicates RBAC rule misconfiguration or missing binding |
| **Remediation** | Review RBAC bindings; ensure `subjects` match the intended user or serviceAccount; check `namespace` scope of the Rule |
| **Evidence** | `kubectl` forbidden error; audit log entry showing the denial |
| **Automated** | Yes — `kubectl` scripted with assert on forbidden error |
| **Manual** | Yes — manual `kubectl --as=another-user` with observation of denial |

---

## 8.7 Service Account Permissions

| Field | Details |
|---|---|
| **Test ID** | ID-005 |
| **Scope** | ServiceAccount token-driven access to K8s API |
| **Positive Test** | |
| **Preconditions** | Pod runs with a ServiceAccount; that ServiceAccount has API server RBAC rules; in-pod `curl` to the K8s API |
| **Test Command** | From within a pod: `curl -s -H "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" https://kubernetes.default/api/v1/namespaces/default/pods` |
| **Expected Output** | List of pods in `default` namespace; HTTP 200; pod names returned |
| **Failure Condition** | `Error: pods is forbidden`; token not found; API server unreachable from pod network |
| **Remediation** | Review ServiceAccount RBAC rules; check if ServiceAccount is associated with the pod; ensure correct namespace scoping |
| **Evidence** | `curl` output (pod names only; no secrets); pod `describe` showing ServiceAccount binding |
| **Automated** | Yes — init container or e2e test that spins up a pod and introspects API access |
| **Manual** | Yes — exec into a running pod; `curl` the K8s API |

---

## 8.8 Vault/OpenBao Auth Integration

| Field | Details |
|---|---|
| **Test ID** | ID-006 |
| **Scope** | Vault or OpenBao authentication and secret retrieval from within a lab instance |
| **Positive Test** | |
| **Preconditions** | Vault/OpenBao is running; initial root token is configured (or AppRole/K8s auth is set up); TLS is trusted |
| **Test Command** | `curl -s --cacert /path/to/ca.crt -H "X-Vault-Token: <token>" https://vault.example.com/v1/sys/health` |
| **Expected Output** | `{"type":"ready","sealed":false,"status":"sealed"..."}` or health check response; HTTP 200 |
| **Failure Condition** | Token rejected; 403 Forbidden; TLS handshake failure; Vault not initialized |
| **Remediation** | Verify token; check Vault initialization status; ensure TLS CA is trusted; configure AppRole or K8s auth method if token-based auth fails |
| **Evidence** | Health check output (status fields only; no secret values); `curl` exit code |
| **Automated** | Yes — health check scripted with assert on `ready: true` and `sealed: false` |
| **Manual** | Yes — `curl` with visual inspection of health status |

---

## 8.9 Secret Retrieval from Vault/OpenBao

| Field | Details |
|---|---|
| **Test ID** | ID-007 |
| **Scope** | Retrieving a secret from Vault/OpenBao KV secret engine |
| **Positive Test** | |
| **Preconditions** | Secret is stored at a known path; token has read permission on that path; TLS is configured |
| **Test Command** | `curl -s --cacert /path/to/ca.crt -H "X-Vault-Token: <token>" https://vault.example.com/v1/data/secret/my-app-config` |
| **Expected Output** | `{"data":{"data":{"config-key":"config-value","db-password":"********"}}}` — sensitive values masked in evidence |
| **Failure Condition** | 404 Not Found; 403 Forbidden (insufficient token permission); TLS error |
| **Remediation** | Verify secret path; check token permissions; ensure KV engine is enabled at the path; correct secret engine version syntax |
| **Evidence** | API response with sensitive values masked/replaced by `********` in test output; no clear-text secrets in evidence |
| **Automated** | Yes — scripted curl with regex to mask `password`, `token`, `key` fields before evidence capture |
| **Manual** | Yes — manual `curl` with redaction of known secret field names |

---

## 8.10 Secret Rotation

| Field | Details |
|---|---|
| **Test ID** | ID-008 |
| **Scope** | Rotating a secret in Vault/OpenBao and verifying the new value is used |
| **Positive Test** | |
| **Preconditions** | A secret exists at a known path; token has write permission; rotation procedure is documented |
| **Test Command** | Vault rotate secret: `vault kv rotate secret/my-app-config` (or equivalent OpenBao command); then retrieve with `curl` |
| **Expected Output** | New secret version is generated; previous version is archived or invalidated; retrieval of new version succeeds with different value |
| **Failure Condition** | Rotation fails; no new version generated; old version still returns previous value |
| **Remediation** | Verify rotation command syntax; check token has `rotate` permission; consult Vault/OpenBao documentation for KV engine rotation support |
| **Evidence** | Before/after comparison with sensitive values masked; rotation command output; no clear-text values in evidence |
| **Automated** | Yes — rotation command scripted; assert new value differs from old; mask all values in evidence |
| **Manual** | Yes — manual vault command with before/after comparison (redacted) |

---

## 8.11 App Access to Secrets

| Field | Details |
|---|---|
| **Test ID** | ID-009 |
| **Scope** | Application (workload) access to secrets injected via K8s volume or environment variable |
| **Positive Test** | |
| **Preconditions** | Pod is configured with `volumeMount` referencing a Secret; Secret contains known keys; application reads the secret |
| **Test Command** | Create a Secret and a Pod that mounts it as a volume; exec into the pod and `cat` the mounted file |
| **Expected Output** | File contents are readable; secret values appear in the expected paths; application starts successfully |
| **Failure Condition** | `Error: secret "my-secret" not found`; permission denied; volume mount path incorrect |
| **Remediation** | Verify Secret name in Pod spec; check that Secret keys match the expected file paths; ensure ServiceAccount has permission to pull the Secret |
| **Evidence** | `kubectl get secret` output (object metadata only); `kubectl exec` output with file contents masked if sensitive; pod `describe` showing volume mount |
| **Automated** | Yes — manifest scripted; assert file contents match expected values; mask secrets in captured output |
| **Manual** | Yes — create manifest; `kubectl apply`; exec into pod; `cat` mounted files |

---

## 8.12 Unauthorized Access Denial

| Field | Details |
|---|---|
| **Test ID** | ID-010 |
| **Scope** | Access to resources without proper authentication/authorization is denied |
| **Positive Test (as negative)** | |
| **Preconditions** | Resource exists; no authentication is provided or an invalid token is used |
| **Test Command** | `kubectl --token=invalid get pods` or `curl -H "Authorization: Bearer invalid-jwt" https://api.example.com/protected` |
| **Expected Output** | `Error: cannot parse ...` or `401 Unauthorized` or `403 Forbidden`; resource listing denied |
| **Failure Condition** | Invalid token accepted — indicates authentication bypass |
| **Remediation** | Review authentication middleware configuration; validate token issuance and signature; add token introspection or revocation if needed |
| **Evidence** | Error response JSON (no sensitive data); `curl` exit code; API server audit log |
| **Automated** | Yes — scripted `kubectl`/`curl` with assert on forbidden/unauthorized error |
| **Manual** | Yes — manual `kubectl`/`curl` with error capture |

---

## 8.13 Audit Event Generation

| Field | Details |
|---|---|
| **Test ID** | ID-011 |
| **Scope** | Audit events are generated for authentication and authorization actions |
| **Positive Test** | |
| **Preconditions** | Audit logging is enabled in K8s API server or Vault/OpenBao; an authentication or authorization action is performed |
| **Test Command** | Perform an authenticated `kubectl get pods` or Vault secret retrieval; check audit log output |
| **Expected Output** | Audit event record is created with `timestamp`, `user`, `action`, `resource`, `result` (allow/deny); no sensitive values in the event |
| **Failure Condition** | No audit event generated; event contains sensitive data (passwords, tokens); event is missing required fields |
| **Remediation** | Enable audit logging in K8s API server (`--audit-log-path`, `--audit-log-format`); configure Vault/OpenBao audit device; ensure event schema includes required fields |
| **Evidence** | Audit log file or endpoint output (field names only; values masked if sensitive); `kubectl get events` or direct log capture |
| **Automated** | Yes — action scripted; assert audit event record exists and has required fields; mask all sensitive values |
| **Manual** | Yes — perform action; inspect audit log file or endpoint |

> **Key Principle**: Auth success ≠ authorization correctness. A user may successfully authenticate (receive a JWT, token, or session) but still be denied access to resources based on their RBAC roles or attributes. Every test must validate both authentication *and* authorization paths independently.

---

## 8.14 Sensitive Value Masking Policy

All test evidence MUST adhere to the following:

- Clear-text passwords, tokens, keys, or secrets must NOT appear in any captured output
- Regex-mask known secret patterns: `password`, `token`, `secret`, `key` (case-insensitive) replaced with `********`
- JWT evidence must only include non-sensitive claims: `alg`, `typ`, `sub`, `aud`, `exp`, `iat` — omit `jti`, `nbf`, and any custom claims that may contain sensitive data
- Vault/OpenBao evidence must mask `data.data.*` fields that contain secret values
- `kubectl` output must not include token values from service account paths
- Evidence files must be redacted before commit or publication

