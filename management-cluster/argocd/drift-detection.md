# Argo CD Drift Detection

## A. Purpose and scope

Document Argo CD drift detection: detection frequency, notification, manual sync vs auto-sync, conflict resolution.

Cross-references `management-cluster/argocd/argocd.md`, `management-cluster/argocd/application-sync.md`, `management-cluster/argocd/gitops-boundaries.md`.

## B. Drift detection frequency

Argo CD detects drift at configurable intervals:

```yaml
# Application spec with drift detection
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
  revisionHistoryLimit: 10
```

Drift detection happens every 3 minutes by default. The interval is controlled by the Argo CD `status.processors` and `reconciliationTimeout` settings.

## C. Notification on drift

Drift notifications are sent via:

| Channel | Configuration |
|---------|---------------|
| Argo CD UI | Application shows OutOfSync status |
| Webhook | `argocd-notifications` with Slack/Teams |
| Email | `argocd-notifications` email template |

## D. Manual sync vs auto-sync

| Mode | When to use |
|------|-------------|
| Manual sync | Production clusters where changes require approval |
| Auto-sync | Development/staging clusters where rapid iteration is preferred |
| Self-heal only | Detect and alert on drift, but don't auto-remediate |

```bash
# Enable auto-sync with self-heal
argocd app set <application> --sync-policy automated --self-heal

# Enable auto-sync with prune
argocd app set <application> --sync-policy automated --prune

# Disable auto-sync (manual only)
argocd app set <application> --sync-policy none
```

## E. Conflict resolution

When drift is detected:

1. Review the diff: `argocd app diff <application>`
2. Decide: accept drift (update Git) or reconcile (sync from Git)
3. If accepting drift: update Git manifest, commit, push
4. If reconciling: `argocd app sync <application>`

## F. Cross-references

- `management-cluster/argocd/argocd.md` — Argo CD deployment
- `management-cluster/argocd/application-sync.md` — Application sync
- `management-cluster/argocd/gitops-boundaries.md` — GitOps boundaries
