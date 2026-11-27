# Argo CD Application Sync

## A. Purpose and scope

Document Argo CD application sync: sync waves, pruning, self-heal, drift detection, rollback procedures.

Cross-references `management-cluster/argocd/argocd.md`, `management-cluster/argocd/drift-detection.md`, `management-cluster/argocd/gitops-boundaries.md`.

## B. Application sync

```bash
# Manual sync
argocd app sync <application>

# Sync with prune
argocd app sync <application> --prune

# Sync with self-heal
argocd app sync <application> --self-heal

# Rollback to previous version
argocd app rollback <application> <revision>
```

## C. Sync waves

Sync waves control the order of resource creation:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
  source:
    directoryRecurse: true
    kustomize:
      namePrefix: platform-
  destination:
    server: https://kubernetes.default.svc
    namespace: platform
```

Sync waves are set via annotation:
```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"
```

## D. Drift detection

Argo CD detects drift between desired and actual state:

```bash
# Check for drift
argocd app diff <application>

# Auto-sync on drift
argocd app set <application> --sync-policy automated
```

## E. Rollback procedures

```bash
# List revisions
argocd app history <application>

# Rollback to specific revision
argocd app rollback <application> <revision>

# Verify rollback
argocd app get <application>
```

## F. Cross-references

- `management-cluster/argocd/argocd.md` — Argo CD deployment
- `management-cluster/argocd/drift-detection.md` — Drift detection
- `management-cluster/argocd/gitops-boundaries.md` — GitOps boundaries
