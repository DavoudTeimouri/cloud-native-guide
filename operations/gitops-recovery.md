# Section 8 — GitOps and Configuration Recovery

*Illustrative only — not production-committed configurations. No live cluster or GitOps automation is modified from this document.*

## 8.1 Git Repository as Source of Truth

The Git repository containing cluster manifests, Helm values, Kustomize overlays, and Argo CD Application resources is the source of truth for desired cluster state. Recovery of configuration starts here.

**Coverage boundary**: Git contains manifest *descriptions*, not running *data*. It does not contain:
- PersistentVolumeClaim data stored on Ceph/CSI volumes
- Container image layers (images live in Harbor/Nexus)
- etcd contents (Kubernetes control-plane state)
- Secrets beyond what is sealed/committed (secrets should not be committed plaintext)

Recovery therefore has two phases: (1) restore Git-controlled configuration, (2) restore stateful data from backups (see Sections 5–7).

## 8.2 Argo CD Recovery

Argo CD reads desired state from Git and reconciles clusters. Its own state (Application resources, projects, credentials, repository definitions, revision history) is stored in the Argo CD database/PostgreSQL and in Kubernetes secrets/configmaps.

### Backup requirements
- PostgreSQL database dump (Argo CD application state, project definitions, repository credentials).
- Kubernetes secrets/configmaps holding Argo CD repository credentials and OIDC/Keycloak client secrets.
- Repository credentials (deploy keys, tokens) — never committed plaintext; stored in Vault/Kubernetes secrets and backed up separately (see Section 9).

### Restore procedure
1. Restore Argo CD PostgreSQL from backup into a clean Argo CD deployment.
2. Restore repository credential secrets (from Vault/backup, not Git).
3. Restore Application and AppProject custom resources (already in Git, but reapply to re-sync revision tracking).
4. Wait for Argo CD to perform initial sync against Git.

### Validation
- `argocd app list` — all expected Applications present.
- `argocd app sync-status <app>` — syncs to Git without error.
- Repository credential test: `argocd repo list` shows repositories reachable.

> **Never** commit Argo CD admin passwords or repository deploy keys to Git. Restore them from the secrets backup.

## 8.3 Application and Repository Credential Recovery

Application credentials (database passwords, API keys, image pull secrets) must not live in Git. Recovery:

1. Rotate credentials that may have been exposed during the outage (assume compromise if the window is unknown).
2. Re-issue secrets from Vault or backup into Kubernetes secrets/imagePullSecrets.
3. Re-apply Argo CD repository credentials (deploy keys/tokens) from the secrets backup.
4. Verify each workload can reach its backing service after restore.

## 8.4 Cluster Bootstrap Dependencies

Before Argo CD can sync, the cluster must be bootstrapped:
- Control plane restored (etcd, API server, scheduler, controller-manager) — see Section 4.
- CNI operational (pod networking) — see Section 6/7.
- Storage classes and CSI drivers available — see Section 5/6.
- Ingress controller and external DNS reachable.
- Argo CD itself deployed (it is not available to restore itself).

Bootstrap order: control plane → CNI → storage → ingress → Argo CD → application sync.

## 8.5 Offline Availability of Charts, Manifests, and Images

For restricted-network/offline recovery:
- Helm charts must be mirrored locally (Nexus/Harbor chart repo) — see Section 7/11 of TASK 004-P11.2.
- Manifests committed to Git must reference images from the internal registry (`harbor.internal/...`), not public registries.
- Container images required for bootstrap (Argo CD, ingress, CNI, CSI) must exist in the internal registry before they are needed.

Do not assume public internet access is available during recovery.

## 8.6 Configuration Drift After Restore

After a restore, cluster state may differ from Git (drift) because:
- Argo CD was offline while changes were applied manually.
- Autoscalers changed replica counts.
- ConfigMaps/Secrets were edited outside Git.

### Detection
- `argocd app diff <app>` — shows differences between Git desired state and live state.
- `kubectl get <resource> -o yaml` compared against Git-committed YAML.

### Safe reconciliation
1. Review the diff before syncing — confirm manual changes are intentional or should be reverted.
2. `argocd app sync <app>` — applies Git desired state.
3. For intentional manual changes, commit them to Git first, then sync.
4. Monitor for reconciliation loops (Application repeatedly OutOfSync).

## 8.7 Preventing GitOps from Overwriting Restored State

After a disaster restore, Argo CD may immediately sync and overwrite just-restored state with stale Git content. Safeguards:

- **Pause sync temporarily** on critical Applications during data restore: `argocd app sync-pause <app>`.
- **Restore data first**, then resume GitOps sync: `argocd app sync-resume <app>`.
- **Use a recovery ApplicationSet/project** isolated from production Applications until validation passes.
- **Never** force-sync an Application whose data layer is still being restored.

## 8.8 Validation Commands

```bash
# 1. Argo CD applications present and healthy
argocd app list
# Expected: all production apps listed, status Healthy/Synced

# 2. Diff against Git (detect drift)
argocd app diff <app-name>
# Expected: empty diff or only intentional post-restore changes

# 3. Repository connectivity
argocd repo list
# Expected: all repositories reachable, no credential errors

# 4. Sync status
argocd app get <app-name>
# Expected: OperationState: Successful, SyncStatus: Synced
```

## 8.9 Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Argo CD app stuck OutOfSync | Repository credential invalid or image unavailable | Restore credential from backup; verify image in internal registry |
| Sync overwrites restored data | Sync resumed before data layer restored | Pause sync; restore data; resume |
| Application shows Unknown | Argo CD controller unreachable or repo not cloned | Check Argo CD pods; restore repo credentials |
| Diff shows unexpected changes | Drift from manual edits | Review diff; commit intentional changes to Git, then sync |

---

*SND 004-P11.5 — GitOps and Configuration Recovery (illustrative)*
