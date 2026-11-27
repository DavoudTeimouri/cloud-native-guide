# GITOPS-RECOVERY

*مثالی است.*

## GITOPS-RECOVERY-1. Git as source of truth

manifests/Helm/Kustomize در Git؛ داده persistent در Git نیست.

## GITOPS-RECOVERY-2. Argo CD recovery

 PostgreSQL dump، secrets/configmaps، repository credentials، App/AppProject re-sync.

## GITOPS-RECOVERY-3. bootstrap order

 control plane → CNI → storage → ingress → Argo CD → apps.

## GITOPS-RECOVERY-4. drift detection

 `argocd app diff`، sync-resume بعد از بازیابی داده.

---

*SND 004-P11.5 — GITOPS-RECOVERY (illustrative)*
