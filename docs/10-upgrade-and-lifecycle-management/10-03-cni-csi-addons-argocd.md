# CNI, CSI, Add-ons, Argo CD

## Purpose and scope
CNI/CSI/add-on/Argo CD upgrades; compatibility, rollback.

## Steps
1. Check version compatibility matrix
2. Backup application data/state
3. Upgrade add-on one at a time via Helm/Argo CD
4. Verify add-on healthy
5. Rollback if issues

## Implementation
```bash
# Upgrade Helm chart
helm upgrade <release> <chart> --version <new-version> -n <namespace>

# Upgrade via Argo CD
kubectl patch application <app> -n argocd --type merge -p '{"spec":{"source":{"targetRevision":"<new-version>"}}}'

# Verify
kubectl get pods -n <namespace>
kubectl get application <app> -n argocd
```

## Validation
- Add-on pods Running
- Application Synced/Healthy
- Functionality verified

## Related
- [06 · Kubernetes Infrastructure (6.11 Kubernetes Add-ons)](../06-kubernetes-infrastructure/6.11-kubernetes-add-ons.md)
- [06 · Kubernetes Infrastructure (6.12 GitOps and Application Delivery)](../06-kubernetes-infrastructure/6.12-gitops-and-application-delivery.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
