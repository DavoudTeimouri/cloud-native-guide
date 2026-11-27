# Authentication and AD

## Symptoms
- User cannot log in to Rancher/GitLab/Argo CD
- OIDC token invalid or expired
- LDAP group not syncing
- RBAC permission denied
- Service account token rejected

## Possible causes
- Keycloak not running or unreachable
- LDAP/AD connection misconfigured
- OIDC client secret expired
- User not in required group/role
- Service account token expired or revoked

## Diagnostic commands
```bash
# Keycloak
kubectl get pods -n keycloak
curl -vk https://keycloak.management.internal/realms/platform/.well-known/openid-configuration

# GitLab/Argo CD login
curl -vk https://gitlab.internal/users/sign_in
curl -vk https://argocd.management.internal/api/v1/session

# RBAC
kubectl auth can-i <verb> <resource> --as <user>
kubectl get rolebinding,clusterrolebinding -A | grep <user>

# Service account
kubectl get sa <sa> -o yaml
kubectl describe sa <sa>
```

## Expected output
- Keycloak: OIDC config JSON returned
- GitLab/Argo CD: login page returned
- kubectl auth can-i: yes/no
- SA: token present and valid

## Investigation procedure
1. Check Keycloak pod running and OIDC config reachable
2. Test GitLab/Argo CD login page
3. Check user group membership in Keycloak
4. Check RBAC bindings for user/service account
5. Check service account token validity

## Resolution
- Restart Keycloak; fix LDAP/AD connection
- Update OIDC client secret
- Add user to required group/role
- Create/update RBAC binding
- Rotate service account token

## Verification
- User can log in; kubectl auth can-i returns expected; service account can perform actions

## Prevention
- Monitor Keycloak health; alert on crash
- Monitor OIDC client secret expiry; rotate before expiry
- Regular RBAC review; remove unused bindings

## Related
- [Kubernetes Infrastructure (6.16 Security and Identity)](../06-kubernetes-infrastructure/6.16-security-and-identity.md)
