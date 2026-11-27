# GitOps Troubleshooting

## Common Issues

### Argo CD Application Stuck in Progressing

**Symptoms**: Application stuck in `Progressing` state indefinitely.

**Likely Causes**:
- Resource not becoming ready (Pod stuck, PVC pending)
- Health check failing
- Sync window blocking
- Resource conflict

**Diagnosis**:
```bash
argocd app get <app-name>
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp
kubectl describe <resource> -n <namespace>
```

**Resolution**:
- Check underlying resource health
- Force sync if appropriate: `argocd app sync <app-name> --force`
- Check sync windows/policies

### Argo CD Application Stuck in Degraded

**Symptoms**: Application shows `Degraded` health status.

**Likely Causes**:
- Resource missing
- Health check failing
- Resource modified outside GitOps

**Diagnosis**:
```bash
argocd app get <app-name> --show-health
kubectl get <resource> -n <namespace> -o yaml
```

**Resolution**:
- Fix underlying resource issue
- Force refresh: `argocd app refresh <app-name>`
- Hard refresh: `argocd app sync <app-name> --force --prune`

### Argo CD Sync Fails

**Symptoms**: Sync operation fails with error.

**Likely Causes**:
- Resource validation error
- CRD not installed
- RBAC permissions insufficient
- Resource conflict (field immutable)

**Diagnosis**:
```bash
argocd app sync <app-name> --dry-run
argocd app sync <app-name> --loglevel debug
kubectl apply --dry-run=server -f <manifest>
```

**Resolution**:
- Fix manifest validation errors
- Install required CRDs first
- Grant necessary RBAC permissions
- Force replace if field immutable: `kubectl replace --force -f <manifest>`

### Argo CD Application Out of Sync

**Symptoms**: Application shows `OutOfSync` status.

**Likely Causes**:
- Manual changes made outside GitOps
- Git repository not updated
- Argo CD not polling

**Resolution**:
```bash
# Auto-sync enabled
argocd app sync <app-name>

# Force sync with prune
argocd app sync <app-name> --prune

# Force override
argocd app sync <app-name> --force --prune
```

### Argo CD Cannot Connect to Cluster

**Symptoms**: Argo CD shows cluster as `Unknown` or `Failed`.

**Likely Causes**:
- Cluster secret expired/incorrect
- Network connectivity issue
- API server unreachable
- RBAC permissions changed

**Diagnosis**:
```bash
argocd cluster list
argocd cluster get <cluster-name>
kubectl get secret <cluster-secret> -n argocd -o yaml
```

**Resolution**:
- Update cluster secret with valid token
- Verify network connectivity
- Check RBAC permissions for Argo CD service account

### Argo CD Repository Connection Fails

**Symptoms**: Cannot connect to Git repository.

**Likely Causes**:
- Repository URL incorrect
- SSH key/token expired
- SSH host key changed
- Network connectivity issue

**Diagnosis**:
```bash
argocd repo list
argocd repo get <repo-url>
ssh -T git@gitlab.internal
```

**Resolution**:
- Update repository URL
- Regenerate SSH key or update token
- Update known_hosts for SSH
- Verify network connectivity

### Argo CD Project Permissions

**Symptoms**: Users cannot access applications in project.

**Likely Causes**:
- User not in project role
- Project role bindings missing
- RBAC misconfigured

**Resolution**:
```bash
argocd proj get <project-name>
argocd proj role list <project-name>
argocd proj role create <project-name> <role-name> --permissions <permissions>
```

### Argo CD Resource Hook Failures

**Symptoms**: PreSync/PostSync hooks fail.

**Likely Causes**:
- Hook script fails
- Hook timeout
- Hook resource not cleaned up

**Diagnosis**:
```bash
kubectl get pods -n <namespace> -l argocd.argoproj.io/hook=PreSync
kubectl logs <hook-pod> -n <namespace>
```

**Resolution**:
- Fix hook script
- Increase timeout: `argocd.argoproj.io/hook-timeout: "300"`
- Clean up failed hook resources

### Argo CD App-of-Apps Not Syncing Children

**Symptoms**: Parent app synced but children not.

**Likely Causes**:
- Child apps not created
- Child app spec incorrect
- Sync policy not propagated

**Resolution**:
```bash
argocd app get <parent-app>
kubectl get applications -n argocd -l argocd.argoproj.io/instance=<parent>
argocd app sync <child-app>
```

### Argo CD Resource Customization Not Applied

**Symptoms**: Kustomize/Helm values not applied.

**Likely Causes**:
- Kustomize/Helm parameters incorrect
- Overlay not applied
- Values file not found

**Resolution**:
```bash
# Test locally
kustomize build <overlay-path>
helm template <release> <chart> -f values.yaml

# Check Argo CD source
argocd app get <app-name> --show-source
```

### Argo CD Performance Issues

**Symptoms**: Slow UI, slow syncs, high resource usage.

**Likely Causes**:
- Too many applications
- Large repositories
- Insufficient resources
- Repository polling too frequent

**Resolution**:
- Increase Argo CD resources (CPU/memory)
- Reduce polling interval
- Use webhook instead of polling
- Split into multiple Argo CD instances

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*