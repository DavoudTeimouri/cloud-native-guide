# Argo CD

## Symptoms
- Application OutOfSync
- ApplicationSet not generating Applications
- Image Updater not updating image tags
- Argo CD server unreachable
- Application stuck in Unknown/Progressing

## Possible causes
- Argo CD server/repo-server/dex not running
- GitLab repository credentials invalid or expired
- Repository URL inaccessible
- Image tag not found in Harbor
- Application manifest invalid
- Resource quota exceeded

## Diagnostic commands
```bash
# Argo CD components
kubectl get pods -n argocd
kubectl get applications -A
kubectl get applicationsets -A
kubectl get imagestreams.argoproj.io -A

# Application details
kubectl get application <app> -o yaml
kubectl describe application <app>

# Logs
kubectl logs -n argocd deploy/argocd-server
kubectl logs -n argocd deploy/argocd-repo-server
kubectl logs -n argocd deploy/argocd-dex

# Credentials
kubectl get secret -n argocd | grep -i cred
```

## Expected output
- Argo CD server: Running
- Application: Synced/Healthy
- ImageUpdater: new tag detected and applied

## Investigation procedure
1. Check Argo CD component pods running
2. Check Application status and sync status
3. Check ApplicationSet triggers and generators
4. Check ImageUpdater logs for image tag detection
5. Verify GitLab credentials and repository access

## Resolution
- Restart Argo CD components
- Update repository credentials in secret
- Fix Application manifest
- Update image tag or ensure image exists in Harbor
- Adjust ApplicationSet generator

## Verification
- Application Synced/Healthy; Image Updater applying new tags; drift detected and corrected

## Prevention
- Monitor Argo CD component health; alert on crash
- Monitor Application sync status; alert on OutOfSync
- Monitor Image Updater; alert on failed updates

## Related
- [Kubernetes Infrastructure (6.12 GitOps and Application Delivery)](../06-kubernetes-infrastructure/6.12-gitops-and-application-delivery.md)
