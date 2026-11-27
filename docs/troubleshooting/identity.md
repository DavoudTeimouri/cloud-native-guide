# Identity Troubleshooting

## Symptoms

- Users cannot log in through Keycloak
- LDAP/AD synchronization fails
- OIDC token validation fails
- Group membership not reflected in Kubernetes RBAC
- Identity provider not reachable

## Likely causes

- Keycloak not running or unhealthy
- LDAP bind credentials wrong or expired
- OIDC client configuration mismatch
- Keycloak realm not imported or misconfigured
- Network policy blocking LDAP/AD port (389/636)

## Diagnostic commands

```bash
# Is Keycloak running?
kubectl -n keycloak get pods
kubectl -n keycloak logs -l app=keycloak

# Can we reach LDAP?
ldapsearch -x -H ldap://<ldap-server> -D <bind-dn> -w <password> -b <base-dn>

# Is OIDC endpoint reachable?
curl -k https://<keycloak-url>/realms/<realm>/.well-known/openid-configuration

# Check Keycloak clients
curl -k -H "Authorization: Bearer <admin-token>" \
  https://<keycloak-url>/admin/realms/<realm>/clients

# Check user federation
kubectl -n keycloak exec <keycloak-pod> -- /opt/keycloak/bin/kcad.sh \
  get users -r <realm>
```

## Expected healthy state

- Keycloak pods: Running, 0 restarts
- LDAP bind succeeds and returns user entries
- OIDC well-known endpoint returns valid JSON
- Keycloak admin API returns client list
- User federation shows synced users

## Remediation

- Restart Keycloak: `kubectl -n keycloak rollout restart deployment/keycloak`
- Fix LDAP bind credentials in Keycloak user federation
- Re-import Keycloak realm configuration
- Fix OIDC client redirect URIs and scopes
- Add network policy allowing LDAP/AD access

## Risks

- Restarting Keycloak briefly interrupts all authentication
- Wrong LDAP config can cause lockout of directory users
- Realm misconfiguration can break SSO for all applications

## Verification

```bash
kubectl -n keycloak get pods
curl -k https://<keycloak-url>/realms/<realm>/.well-known/openid-configuration | python3 -m json.tool | head -5
ldapsearch -x -H ldap://<ldap-server> -D <bind-dn> -w <password> -b <base-dn> | head -5```
