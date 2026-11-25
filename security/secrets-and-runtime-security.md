# Section 9 — Kubernetes Secrets & Runtime Security

*Illustrative only — not production-committed configurations. Marked as such where indicated. No baselines are applied to a live cluster from this document.*

---
## 9.1 Kubernetes Secret Limitations

Kubernetes Secrets are the default mechanism for passing sensitive data into clusters, but they have significant security boundaries that must be understood:

| Limitation | Detail |
|---|---|
| **etcd storage — base64, not encryption** | Secret data is written to etcd as base64-encoded text. By default, etcd provides encryption at rest only if its `--encryption-provider-config` is enabled. Without it, anyone with etcd read access recovers the raw secret. |
| **Namespace-scoped** | A Secret exists only within its namespace. Cluster-wide secrets require copying into each namespace, increasing the attack surface. |
| **No fine-grained access control** | RBAC can limit who can `get/list/create/update/delete` Secrets, but once a user has `Secrets` access in a namespace, they can read all Secrets in that namespace. There is no per-Secret ACL. |
| **Implicit volume mount exposure** | When mounted as a volume, Secret files appear on the filesystem with the container's UID/GID. If the container runs as root, the files are world-readable unless `secretKeyRef` is carefully paired with `readOnly: true` and filesystem permissions. |
| **AutomountServiceAccountToken interaction** | `automountServiceAccountToken: false` does not affect Secrets, but developers sometimes bypass this by mounting a Secret containing a service account token. |
| **Image pull secrets are separate** | `imagePullSecrets` are referenced at the ServiceAccount level and are not visible to workload containers unless explicitly projected or mounted. |
| **Dockerfile/IMAGE leakage** | If a Secret is baked into an image via `COPY --from` or `RUN` commands, the secret becomes part of the image layer and is visible to anyone with image access. |

**Validation checklist:**
- [ ] Verify etcd encryption-at-rest is configured (`--encryption-provider-config`); if not, treat all Secrets as visible to etcd readers.
- [ ] Confirm no Secret is granted cluster-wide scope unless absolutely necessary.
- [ ] Confirm RBAC follows least-privilege: users can only act on the specific Secrets their workloads need.
- [ ] Confirm all Secret volume mounts have `readOnly: true` unless the application explicitly writes to the mounted path.
- [ ] Confirm no image contains hardcoded Secrets (audit Dockerfile `RUN` and `COPY` commands).

---
## 9.2 Vault/OpenBao Integration Patterns

Secrets should be fetched at runtime from a secrets broker rather than stored statically in Kubernetes. The following patterns are illustrated with placeholders; do not use real credential values.

### 9.2.1 Sidecar Injector Pattern

A sidecar container (typically HashiCorp Vault Agent or OpenBao sidecar) intercepts the pod's volume mounts and environment variable injection. The sidecar contacts the broker, fetches secrets, and writes them into a projected volume or env vars that the application container reads.

**Illustrative — Vault Agent sidecar injector:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-vault-sidecar
spec:
  serviceAccountName: vault-accessor
  automountServiceAccountToken: false
  containers:
    - name: app
      image: registry.internal/myapp:latest
      env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: {{ vault-injected-secret-name }}
              key: database_url
    - name: vault-agent
      image: hashicorp/vault:latest
      args: ["server", "-config=/vault/config/vault-agent.json"]
      volumeMounts:
        - name: vault-secret
          mountPath: /vault/secrets
  volumes:
    - name: vault-secret
      projected:
        defaultMode: 0600
        sources:
          - secretRef:
              name: {{ vault-fetched-secret }}
              optional: false
```

**How it works:** The Vault Agent sidecar uses the Kubernetes auth method to obtain a token, fetches the secret at pod startup (or on a TTL-based renewal cycle), and projects it into the application container's environment via a projected volume. The application sees only the projected env var; the raw secret never enters the application container's filesystem.

### 9.2.2 CSI Driver Pattern

The Secret CSI driver (HashiCorp Vault CSI or OpenBao CSI) provisions secrets as volumes directly, without a sidecar process. The driver contacts the broker, reads the secret, and makes it available as a volume at the requested path.

**Illustrative — Vault CSI volume:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-vault-csi
spec:
  containers:
    - name: app
      image: registry.internal/myapp:latest
      volumeMounts:
        - name: db-credential
          mountPath: /etc/db-credentials
          readOnly: true
  volumes:
    - name: db-credential
      csi:
        driver: csi.vault.hashi.com
        volumeAttributes:
          secret_name: my-db-credential
        nodePublishSecretRef:
          name: vault-csi-node-credentials
          namespace: vault
```

**How it works:** The CSI driver node plugin provisions the secret from Vault/OpenBao onto the node's filesystem. The application container mounts the volume at `readOnly: true` path. The secret exists only in the node's tmpfs and is cleaned up when the volume is detached.

### 9.2.3 Init Container Pattern

An init container fetches secrets before the application container starts, writes them to a shared volume, and the application container then reads them from that volume.

**Illustrative — init container secret fetch:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init-secret
spec:
  initContainers:
    - name: fetch-secrets
      image: hashicorp/vault:latest
      command: ["sh", "-c"]
      args:
        - |
          vault login -method=kubernetes token=$VAULT_TOKEN
          vault kv get -field=connection_string secret/db > /shared/connection.txt
      volumeMounts:
        - name: shared-volume
          mountPath: /shared
  containers:
    - name: app
      image: registry.internal/myapp:latest
      volumeMounts:
        - name: shared-volume
          mountPath: /etc/app-credentials
          readOnly: true
  volumes:
    - name: shared-volume
      emptyDir: {}
```

**How it works:** The init container runs to completion, writes the fetched secret into an `emptyDir` volume, and the application container then reads it. The secret exists only in memory during init; once the pod is running, the init container is gone.

### 9.2.4 Direct API Pattern

For workloads that cannot use sidecars or CSI (e.g., static binaries, network policy constraints), the application calls the Vault/OpenBao API directly at startup to fetch secrets. This pattern requires the workload to have network egress to the broker and appropriate TLS certificates.

**Illustrative — direct API fetch at startup:**
```bash
# In Dockerfile or entrypoint script
export VAULT_ADDR='https://vault.internal:8200'
export VAULT_TOKEN='${VAULT_INIT_TOKEN}'  # provisioned via Kubernetes auth review

# Fetch secret at runtime
CONNECTION_STRING=$(vault kv get -field=conn secret/app-db)
echo "export DATABASE_URL=${CONNECTION_STRING}" >> /etc/profile.d/env.sh
```

**How it works:** The workload is built with Vault CLI or HTTP client libraries. At container start, it authenticates (via Kubernetes auth method, AppRole, or cloud IAM) and retrieves the secret. The TTL on the Vault secret controls the rotation window.

### 9.2.5 Pattern Summary

| Pattern | Sidecar required? | CSI driver required? | Typical use case |
|---|---|---|---|
| Sidecar Injector | Yes | No | Most common; fine-grained control over env vars vs volumes; works on any cluster. |
| CSI Driver | No | Yes | Volume mounting; lower overhead than sidecar; requires CSI-capable cluster. |
| Init Container | No | No | Short-lived fetch before app starts; simple but no auto-renewal. |
| Direct API | No | No | Legacy workloads; requires network egress and auth setup per binary. |

---
## 9.3 Secret Rotation and Access Control

Rotation turns a long-lived secret into a short-lived credential, shrinking the blast radius of any leak.

### 9.3.1 Rotation Strategies

| Strategy | Description | TTL/Example |
|---|---|---|
| **Provider-managed TTL** | Cloud KMS or broker issues credentials with a time-to-live; the credential is automatically revoked when the TTL expires. | Vault database secrets engine: `default_ttl="15m" max_ttl="1h"` |
| **Periodic rotation** | A scheduled job (CronJob) rotates credentials at a fixed cadence, overlapping old and new during cutover. | Weekly DB password rotation with 24h overlap window |
| **On-exposure rotation** | Any detected exposure (pre-commit scanner flag, CI alert, runtime detection) triggers immediate rotation at the provider. | Rotate AWS IAM key within minutes of gitleaks flag |
| **Dynamic per-workload** | Each workload instance fetches its own credential; no shared static key across deployments. | Vault dynamic DB roles: each pod gets a unique username/password |

### 9.3.2 Access Control Boundaries

- **One credential per workload** — no shared "god" credentials across namespaces or deployments.
- **Least-privilege broker policies** — the Vault/OpenBao role granted to the workload permits only the operations the workload needs (SELECT on specific tables, read on specific keys, etc.).
- **RBAC on Secrets** — even when using a broker, any remaining Kubernetes Secrets must have RBAC scoped to the service account that requires them.
- **Review rotation non-breaking** — overlap old and new credentials during cutover so rotation never becomes an outage. For DB credentials, grant the new role access before revoking the old one.

### 9.3.3 Validation checklist
- [ ] Every credential has a known TTL or rotation cadence documented.
- [ ] Every credential has an identified owner (team or service).
- [ ] Every credential has a known revocation path (API call, CLI command, or kill-switch).
- [ ] Rotation overlaps old and new credentials during cutover; no downtime window.
- [ ] Broker policies are least-privilege: workload can only operate on its allocated scope.
- [ ] On-exposure rotation is documented and tested (rotate within 10 minutes of a simulated leak).

---
## 9.4 Avoiding Secrets in Git, Manifests, Logs, and Container Images

The gold standard: **no secret ever lands in a git repository, manifest YAML, container image, or runtime log.** The following patterns prevent each vector.

### 9.4.1 Git

- Never commit `.env` files, PEM keys, API tokens, or connection strings.
- Add patterns to `.gitignore` and use a pre-commit hook (e.g., gitleaks) that blocks commits containing high-entropy strings matching secret patterns.
- If a secret is accidentally committed, treat it as compromised from the commit timestamp — rotate at the provider first, then remove from history with `git filter-repo` or BFG, then coordinate a repo rewrite.

**Illustrative — `.gitignore` entry:**
```
# Block common secret patterns from committing
.env*
*.pem
*.key
*.cert
*credentials*
*token*
*auth*
```

**Illustrative — gitleaks pre-commit hook (`.pre-commit-config.yaml`):**
```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

### 9.4.2 Manifests (YAML)

- Secrets should be referenced via `secretKeyRef`, never inlined.
- Use external secret operators or brokers to inject secrets at runtime; keep the manifest free of raw values.
- If a placeholder is needed in a manifest, use a clearly marked pattern that tools can flag.

**Illustrative — manifest referencing a broker-derived secret (placeholder):**
```yaml
apiVersion: v1
kind: Deployment
metadata:
  name: app-configurable
spec:
  template:
    spec:
      serviceAccountName: broker-accessor
      automountServiceAccountToken: false
      containers:
        - name: app
          image: registry.internal/myapp:latest
          env:
            - name: DATABASE_URL
              # PLACEHOLDER: injected by Vault CSI sidecar at runtime
              valueFrom:
                secretKeyRef:
                  name: {{vault-injected-db-url}}
                  key: connection_string
```

### 9.4.3 Logs

- Never `echo`, `print`, or log a raw secret value.
- Redact secrets in application code before writing to any log output.
- If an error message inadvertently includes a secret value, treat the entire log stream as compromised and rotate the secret.

**Illustrative — redaction example (pseudocode):**
```python
import re
SECRET_PATTERN = re.compile(r'(?i)(password|secret|token)\s*[:=]\s*\S+')

def safe_log(message):
    redacted = SECRET_PATTERN.sub(lambda m: m.group(1) + '=***REDACTED***', message)
    print(redacted)
```

### 9.4.4 Container Images

- No secret data in `Dockerfile` `RUN` commands, `COPY --from`, or artifacts baked into the image.
- If a secret must be available at image-build time, use `secret` build arguments from Docker BuildKit or fetch from a broker during the build step, then discard the value before the final image layer is committed.

**Illustrative — BuildKit secret build arg (illustrative only):**
```dockerfile
# syntax=docker/dockerfile:1.2
# This arg is available ONLY during build; it is NOT exported in the final image.
secret my-db-pass

RUN mysql -u user -p${my-db-pass} ...  # arg value not persisted in image
```

### 9.4.5 Summary Vector

| Vector | Prevention Pattern |
|---|---|
| Git commit | pre-commit gitleaks hook; `.gitignore`; treat as compromised if found |
| Manifest YAML | `secretKeyRef` only; no inlined values; external secret operators |
| Runtime logs | Application-level redaction; never echo raw secrets |
| Container image | BuildKit secret args (discard after use); broker fetch at runtime; no `COPY` of secrets |

---
## 9.5 Falco Runtime Detection and Response Workflow

Falco is the de facto standard for runtime security event detection in Kubernetes. It monitors system calls and other kernel-level events to detect anomalous behavior that indicates an attack has bypassed preventive controls. **Falco detects runtime threats; it does not enforce admission policies.** Admission controllers like Gatekeeper and Kyverno prevent unwanted resources from entering the cluster; Falco alerts when something unexpected happens at runtime after those controls have been bypassed or are absent.

### 9.5.1 Core Falco Rules (illustrative)

The following ruleset detects common runtime security violations. All rules are illustrative and should be tuned for your environment.

#### Container Escape

```yaml
- rule: Detect Container Escape via /dev/pts/* Mount
  open_read: /dev/pts/*
  success: yes
  output: "Container escape detected — pts device accessed from container (user=%user container=%container)"
  priority: WARNING
```

```yaml
- rule: Detect Host filesystem Mounted from Container
  open_read:
    - /proc/1/root/etc/shadow
    - /proc/1/root/bin/bash
  success: yes
  output: "Host filesystem accessed from container (user=%user container=%container)"
  priority: ERROR
```

#### Cryptomining

```yaml
- rule: Detect Cryptomining Process Execution
  execve: /usr/bin/xmrig
  output: "Cryptomining process detected (user=%user container=%container)"
  priority: WARNING
```

```yaml
- rule: Detect Cryptomining Network Connection
  syscall: connect
  condition: open_read and wide_string contains "/xmrig"
  output: "Cryptomining connection established (user=%user container=%container)"
  priority: WARNING
```

#### Reverse Shells

```yaml
- rule: Detect Reverse Shell via /bin/sh with -i flag
  execve: /bin/sh
  wide_string: "-i"
  output: "Reverse shell detected (user=%user container=%container)"
  priority: ERROR
```

```yaml
- rule: Detect Reverse Shell via netcat
  execve: /bin/nc
  wide_string: "-e"
  output: "Reverse shell via netcat detected (user=%user container=%container)"
  priority: ERROR
```

#### Sensitive File Access

```yaml
- rule: Detect /etc/shadow Read from Container
  open_read: /etc/shadow
  success: yes
  output: "Sensitive file /etc/shadow read from container (user=%user container=%container)"
  priority: WARNING
```

```yaml
- rule: Detect SSH Private Key Access from Container
  open_read: /root/.ssh/id_rsa
  success: yes
  output: "SSH private key accessed from container (user=%user container=%container)"
  priority: ERROR
```

#### Unauthorized Process Execution

```yaml
- rule: Detect New Process Execution in Container
  execve: /bin/sh
  parent: docker-
  output: "Process execution in container detected (user=%user container=%container)"
  priority: WARNING
```

```yaml
- rule: Detect Suspicious Binary Execution to Localhost
  execve: /usr/bin/curl
  condition: open_write and wide_string contains "http://127.0.0.1"
  output: "Suspicious curl execution to localhost from container (user=%user container=%container)"
  priority: WARNING
```

#### Privilege Escalation

```yaml
- rule: Detect setuid/root Binary Execution via su
  execve: "/bin/su"
  output: "Privilege escalation attempt via su detected (user=%user container=%container)"
  priority: WARNING
```

```yaml
- rule: Detect Kernel Module Loading from Container
  execve: /sbin/insmod
  output: "Kernel module loading attempted from container (user=%user container=%container)"
  priority: ERROR
```

### 9.5.2 Falco Response Workflow (alert → triage → contain → remediate → recover)

When a Falco rule fires, follow this workflow:

| Step | Action | Owner | SLA |
|------|--------|-------|-----|
| 1 | Falco rule fires → alert sent to configured webhook/destination | Falco agent | Immediate |
| 2 | Security team verifies the alert (check pod spec, container image, user, command) | On-call analyst | < 5 min |
| 3 | If violation confirmed: isolate the compromised container | Platform team | < 15 min |
| 4 | Rotate any credentials potentially exposed | Credentials engineer | < 30 min |
| 5 | Remove compromised artifact from cluster | Release engineer | < 1 hour |
| 6 | Investigate root cause: how did the bypass occur? | SOC | < 2 hours |
| 7 | Post-incident: update Falco rules, adjust preventive controls, document root cause | Team lead | < 1 week |

### 9.5.3 Security Event Forwarding and Monitoring Integration

Detected events from Falco must be forwarded to a central monitoring platform for correlation, retention, and alerting. *For full forwarding configuration details, see Section 9.6.*

#### Falco → Forwarding Configuration

Falco can forward events to:
- **Webhook destination** (e.g., internal Slack channel, PagerDuty)
- **Syslog** → forward to Elasticsearch, Splunk, or Graylog
- **Kubernetes Event** → visible via `kubectl get events`
- **File** → written to `/var/log/falco/audit.log` for later ingestion

**Illustrative — Falco webhook forwarding (via Falco output listeners):**
```yaml
# falco.yaml output configuration
outputs:
  - name: my_webhook
    module: webhook
    url: https://internal.security.example.com/falco-webhook
    timeout: 10s
    retry_interval: 5s
    retry_count: 3
```

**Illustrative — Falco syslog forwarding:**
```yaml
outputs:
  - name: syslog_output
    module: syslog
    server: logs.internal.example.com
    protocol: tcp
    port: 6514
```

#### Monitoring Platform Ingestion

Forwarded events should include the following enriched fields for correlation:

| Field | Source | Purpose |
|-------|--------|---------|
| `falco_rule` | Falco rule name | Identifies which detection fired |
| `k8s.pod.name` | Falco event | Maps to the violated pod |
| `k8s.namespace.name` | Falco event | Context for RBAC scoping |
| `container.image` | Falco event / Docker metadata | Identifies the image in vulnerability scans |
| `user` | Falco event / auth logs | Determines who triggered the event |
| `timestamp` | Falco event | Correlates with audit logs and CI/CD run timestamps |
| `secret_type` | Custom Falco rule extension | Labels the secret type (DB password, API key, TLS cert) |
| `broker_operation` | Vault/OpenBao API log | Indicates dynamic credential fetch vs static key use |

#### Alerting SLOs

| Condition | Target | Escalation |
|-----------|--------|------------|
| Falco rule fires > 3 times in 5 minutes for same pod | Alert on-call | Page if persists > 10 min |
| Secret scanned pattern found in git push | Fail CI build | Notify team lead; rotate credential |
| Vault/OpenBao auth failure count > 5/minute | Monitoring dashboard | Page SRE lead |
| Credential rotated more than 3 times in 1 hour | Dashboard anomaly | Investigate for exposure |

### 9.5.4 MITRE ATT&CK Mapping for Falco Rules

Falco rules map to MITRE ATT&CK techniques as follows:

| Falco Rule Focus | ATT&CK Technique | ATT&CK Tactic |
|------------------|-------------------|---------------|
| Container escape | T1605.004 | Defense Evasion |
| Cryptomining | T1499 | Impact |
| Reverse shell | T1059.001, T1048 | Execution, Command and Control |
| Sensitive file access | T1005 | Discovery |
| Unauthorized process execution | T1059 | Execution |
| Privilege escalation | T1548 | Privilege Escalation |

*Full ATT&CK mapping per rule is documented in the detection catalog.*

### 9.5.5 False Positive Tuning Guidance

- **Avoid alert fatigue**: Start with `priority: Audit` or `priority: Warning`; promote to `Error` only on confirmed violations.
- **Whitelist known-benign patterns**: The `ignore` field in shell-detection rules prevents false positives from init containers or health checks.
- **Test rules in audit mode first**: `falco -r /etc/falco/falco.rules --audit-mode` generates events without taking action.
- **Context-aware allowlisting**: Whitelist service accounts, health check commands, and legitimate automation patterns. Scope allowlists to specific namespaces or deployments when possible.
- **Monitor rule fire rates**: Track alerts per namespace and per rule; rules firing > 5x/day without confirmed violations should be reviewed.
- **Never rely on parent image name alone**: An attacker can spoof or the parent may be a legitimate process. Always validate the full event context.

### 9.5.6 Validation Commands for Falco

```bash
# Validate rule syntax and configuration
falco -c /etc/falco/falco.rules --validate

# Run Falco in audit mode (generates events, no enforcement)
falco -r /var/log/audit.log --audit-mode

# Run Falco in live mode (monitors system calls)
falco

# List all loaded rules and their status
falco -l

# Check Falco daemon status
systemctl status falco

# Test a specific rule against audit data
falco -r /path/to/audit.log -L rule_name

# Generate events from a specific audit record number
falco -r /var/log/falco/falco.audit.log -i 42
```

### 9.5.7 Runtime Detection (Falco) vs Admission Enforcement (Gatekeeper/Kyverno)

**Runtime detection (Falco)** detects threats at runtime — after an attacker has bypassed preventive controls or when those controls are absent. Falco monitors system calls, system file access, and other kernel-level events to detect anomalous behavior. **Falco does NOT enforce policy**; it alerts on what happens after a pod is running.

**Admission enforcement (Gatekeeper/Kyverno)** enforces policies at pod/Resource creation time. Gatekeeper uses constraint templates and constraints to validate requests against OPA policies. Kyverno uses mutate and validate rules to enforce defaults and restrictions during admission. **Admission controllers run before a resource is created**; they prevent unwanted resources from entering the cluster.

| Aspect | Falco (runtime) | Gatekeeper/Kyverno (admission) |
|--------|-----------------|-------------------------------|
| When it runs | After pod is scheduled, during execution | Before pod is admitted to API server |
| What it monitors | System calls, file access, process activity | Resource manifests, container specs, labels |
| Purpose | Detect threats that bypassed prevention | Prevent unwanted resources from entering |
| Action | Alert, investigate, respond | Admit, reject, mutate the resource |
| Scope | Cluster-wide runtime behavior | Admission-time validation |

**Key principle**: Falco and admission controllers are complementary. Admission controllers reduce the attack surface by preventing known-bad configurations from running. Falco detects what slips through or what involves compromised credentials/keys that were admitted legitimately. A defense-in-depth strategy uses both: admission controllers to prevent common misconfigurations, and Falco to detect runtime anomalies and post-exploitation behavior.

---

## 9.6 Security Event Forwarding and Monitoring Integration

## 9.6 Security Event Forwarding and Monitoring Integration

Detected events from Falco, secret scanners, and broker access logs must be forwarded to a central monitoring platform for correlation, retention, and alerting.

### 9.6.1 Falco → Forwarding Configuration

Falco can forward events to:
- **Webhook destination** (e.g., internal Slack channel, PagerDuty)
- **Syslog** → forward to Elasticsearch, Splunk, or Graylog
- **Kubernetes Event** → visible via `kubectl get events`
- **File** → written to `/var/log/falco/audit.log` for later ingestion

**Illustrative — Falco webhook forwarding (via Falco output listeners):**
```yaml
# falco.yaml output configuration
outputs:
  - name: my_webhook
    module: webhook
    url: https://internal.security.example.com/falco-webhook
    timeout: 10s
    retry_interval: 5s
    retry_count: 3
```

**Illustrative — Falco syslog forwarding:**
```yaml
outputs:
  - name: syslog_output
    module: syslog
    server: logs.internal.example.com
    protocol: tcp
    port: 6514
```

### 9.6.2 Monitoring Platform Ingestion

Forwarded events should include the following enriched fields for correlation:

| Field | Source | Purpose |
|---|---|---|
| `falco_rule` | Falco rule name | Identifies which detection fired |
| `k8s.pod.name` | Falco event | Maps to the violated pod |
| `k8s.namespace.name` | Falco event | Context for RBAC scoping |
| `container.image` | Falco event / Docker metadata | Identifies the image in vulnerability scans |
| `user` | Falco event / auth logs | Determines who triggered the event |
| `timestamp` | Falco event | Correlates with audit logs and CI/CD run timestamps |
| `secret_type` | Custom Falco rule extension | Labels the secret type (DB password, API key, TLS cert) |
| `broker_operation` | Vault/OpenBao API log | Indicates dynamic credential fetch vs static key use |

### 9.6.3 Alerting SLOs

| Condition | Target | Escalation |
|---|---|---|
| Falco rule fires > 3 times in 5 minutes for same pod | Alert on-call | Page if persists > 10 min |
| Secret scanned pattern found in git push | Fail CI build | Notify team lead; rotate credential |
| Vault/OpenBao auth failure count > 5/minute | Monitoring dashboard | Page SRE lead |
| Credential rotated more than 3 times in 1 hour | Dashboard anomaly | Investigate for exposure |

### 9.6.4 Validation checklist
- [ ] Falco events are forwarded to the central monitoring platform (syslog/webhook confirmed).
- [ ] Monitoring dashboard shows Falco rule fire rate per namespace.
- [ ] Secret scanner CI integration failures are tracked in the issue tracker, not just CI output.
- [ ] Vault/OpenBao access logs (auth success/failure, secret_id usage) are forwarded and searchable.
- [ ] Runbook for "Falco alert on secret violation" is documented and tested in a staging cluster.

---
--- 

*End of Section 9*

**Next section**: [Section 10 — Network Policy & Zero Trust Enforcement](network-policy.md)

*No real credentials or insecure sample secrets are included anywhere in this document. All illustrative values use `{{placeholder}}` or `***REDACTED***` markers.*