# Secret Rotation — HashiCorp Vault

## Rotation Schedule

| Secret Category | Path Pattern | Rotation Frequency | Method |
|---|---|---|---|
| Database credentials | `database/creds/*` | Every 24 hours (dynamic TTL) | Vault DB engine auto-issues with lease; application must re-read on renewal |
| SSH certificates | `secret/infra/ssh/*` | Every 90 days or on use | Vault SSH signer issues short-lived certs; host trusts against CA |
| PKI certificates | `pki/issue/*` | 30 days, auto-renew via cert-manager | Vault PKI issues/renews certs; cert-manager consumes |
| Cloud/registry static tokens | `secret/registry/*` | Every 90 days | Rotate via automation; upstream may support dynamic tokens |
| Application secrets | `secret/apps/*` | Every 30 days | External Secrets Operator sync; re-read or restart required |
| Monitoring credentials | `secret/observability/*` | Every 90 days | External Secrets rotation on interval |
| Keycloak client secrets | `secret/identity/*` | Every 90 days | Ansible or External Secrets rotation |
| Backup encryption keys | `secret/backup/*` | Every 180 days | Ansible / Velero rotation |
| Linux/root credentials | `secret/infra/linux/*` | Every 90 days | Ansible fetch at runtime |
| SSH keys | `secret/infra/ssh/*` | Every 90 days / on use | Ansible + Vault SSH agent signing |
| Kubespray bootstrap creds | `secret/infra/kubespray/*` | Every 90 days | Ansible vault lookup |
| Argo CD repo creds | `secret/gitops/*` | Every 90 days | Argo CD repo API (not stored in Git) |
| GPU service creds | `secret/ai/*` | Every 90 days | External Secrets |
| Model API keys | `secret/ai/models/*` | Every 90 days | External Secrets |
| Ceph keys | `secret/infra/ceph/*` | Every 180 days | Ansible -> Ceph |
| Root CA private key | `pki/root/ca` | Long duration; rotate by re-issue | Offline only; multi-step process — document runbook in `secrets-management/pki/root-ca-rotation.md` |

**General TTL defaults**: Unless otherwise specified, all Vault dynamic secrets use a 24-hour default TTL with a 75% renewal window. Static credentials rotated on schedule use the frequencies above.

---

## Automated Rotation Workflow

The automated rotation pipeline is triggered by Vault's native TTL/expiry mechanism and validated by CI/CD checks. Steps:

1. **Lease expiry** — Vault dynamic secrets expire according to their configured TTL. The application or external system must renew or fetch a new secret.

2. **External Secrets Operator (ESO) sync** — For static secrets managed by ESO, the sync interval (default 5m) detects the changed secret value and updates the Kubernetes Secret. If the secret has a short TTL, configure ESO's `refreshInterval` to match.

3. **Ansible automation** — For secret categories managed by Ansible (Linux creds, SSH keys, Ceph keys, backup keys), run the rotation playbook:

   ```bash
   ansible-playbook -i inventory.yaml rotate-secrets.yml \
     --extra-vault "vault_address=https://vault.example.com:8200" \
     --extra-vault-token "$VAULT_TOKEN"
   ```

   The playbook performs:
   - Reads the current secret from Vault
   - Generates a new value at the source (DB, KMS, certificate authority)
   - Writes the new secret to Vault (`vault kv put`)
   - Updates dependent configurations (K8s Secrets, config files)
   - Commits changes to the appropriate repo (if applicable)

4. **CI/CD gate** — Every PR that modifies secret paths must pass:
   - `checkov` — infrastructure policy check for any IaC changes
   - `gitleaks` — secret detection to prevent new credentials from being committed
   - `trivy` — container image vulnerability scan if the rotation involves container images

5. **Health validation** — After rotation, a smoke test verifies the dependent service can read the new secret without errors. If the service requires a restart or SIGHUP, the rotation pipeline blocks until the restart completes.

6. **Rollback** — If the new secret fails validation within the 24-hour window, revert to the previous value:

   ```bash
   # Restore previous secret version
   vault kv put secret/infra/linux/app-key @previous_version
   # Or restore from backup
   ansible-playbook -i inventory.yaml restore-secrets.yml
   ```

---

## Manual Rotation Steps

Manual rotation is required when automated rotation is unavailable (static credentials, upstream services without dynamic support, or after compromise).

### General Manual Rotation Flow

1. **Pre-rotation preparation**
   - Document the current secret value and its usage
   - Identify all consumers of the secret
   - Schedule a maintenance window
   - Ensure rollback procedure is ready

2. **Generate new credential**
   - For database credentials: use `vault read -field=password database/creds/<role>` and rotate at the source (e.g., RDS master password reset)
   - For API keys: generate a new key from the upstream provider (AWS IAM user, GCP service account, etc.)
   - For SSH keys: generate a new key pair and replace the CA-signed certificate

3. **Write new secret to Vault**
   ```bash
   # Example: rotating a static credential
   vault kv put secret/infra/linux/app-key value=new-credential value=old-credential  # keep old as version label
   ```

   Or for dynamic secrets:
   ```bash
   vault lease renew database/creds/myapp  # renew or extend TTL
   ```

4. **Update consumers**
   - **Kubernetes Secrets** — if managed by ESO, the sync will pick up the change. Otherwise, update the Secret manually:
     ```bash
     kubectl delete secret <secret-name> && kubectl create secret generic <secret-name> --from-literal=key=new-credential
     ```
   - **Application config** — if the app reads from a file or environment, update the source and restart/reload the pod
   - **Ansible/automation** — update the inventory/group_vars to reference the new path/key

5. **Post-rotation verification**
   - Verify the new secret works: `vault read secret/infra/linux/app-key`
   - Confirm no downtime: application logs show successful authentication with new credential
   - Run the health smoke test from the CI/CD pipeline

6. **Cleanup**
   - Revoke the old Vault lease: `vault lease revoke database/creds/myapp`
   - Remove old version labels from the secret if using versioned storage
   - Update documentation with rotation date and operator

---

## Audit Logging Requirements

All secret rotation events must be captured in Vault's audit log and shipped to the centralized logging platform. The following fields must be structured and retained for **minimum 365 days** (compliance mode):

| Field | Example | Requirement |
|---|---|---|
| `rotation_date` | `2024-02-15T14:30:00Z` | Mandatory |
| `secret_path` | `secret/infra/linux/app-key` | Mandatory |
| `secret_category` | `linux-credentials` | Mandatory |
| `rotated_by` | `automation` or `operator` or `manual` | Mandatory |
| `rotation_method` | `ttl-expiry`, `manual-rotation`, `post-compromise` | Mandatory |
| `old_lease_id` | `vaultokv/2` | Mandatory for dynamic secrets |
| `new_lease_id` | `vaultokv/3` | Mandatory for dynamic secrets |
| `trigger` | `scheduled`, `expiry`, `compromise`, `admin-request` | Mandatory |
| `status` | `success`, `failed` | Mandatory |
| `error_message` | (if failed) | Conditional |
| `consumers_updated` | `k8s-secret/frontend`, `k8s-secret/backend` | Recommended |
| `rollback_performed` | `true`/`false` | Recommended |

**Audit log configuration** — Ensure Vault has an audit device configured (file or syslog) with the following minimum settings in `hcl.hcl` or via `vault audit`:

```hcl
audit "file" {
  path = "/var/log/vault/audit.log"
  mode = "0640"
}
```

**Shipping to centralized platform** — The audit log file must be tailed by Filebeat/Metricbeat and shipped to the SIEM/logging platform. Configure rotation of the audit log itself so it does not fill the disk.

**Immutable retention** — The S3 bucket storing archived audit logs (if applicable) must have Object Lock in COMPLIANCE mode with 365-day retention, matching the compliance requirement.

**Quarterly audit review** — Security team reviews a random sample of rotation events each quarter to verify:
- All required fields are present
- No secret values appear in the audit log (metadata only)
- Rotation frequencies match the schedule
- Failed rotations are investigated and resolved

---

## Revision History

| Date | Author | Change |
|---|---|---|
| 2024-02-15 | Security Architect | Initial draft |
| 2024-05-01 | Platform Engineer | Added ESO sync details |
| 2024-08-20 | Cloud Security Architect | Updated audit logging requirements |