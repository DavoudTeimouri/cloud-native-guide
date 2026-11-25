# Identity Troubleshooting

## Common Issues

### Keycloak Unreachable

**Symptoms**: Cannot access Keycloak admin console or OIDC endpoints.

**Likely Causes**:
- Keycloak pods not running
- Database unavailable
- Ingress not routing correctly
- TLS certificate expired

**Diagnosis**:
```bash
kubectl get pods -n keycloak
kubectl logs -n keycloak -l app=keycloak
curl -k https://keycloak.internal/health/ready
```

**Resolution**:
- Restart Keycloak pods
- Check PostgreSQL connectivity
- Verify ingress configuration
- Renew TLS certificates

### OIDC Login Fails

**Symptoms**: Users cannot log in via OIDC.

**Likely Causes**:
- Incorrect client configuration
- Redirect URI mismatch
- Clock skew between Keycloak and client
- Invalid client secret

**Diagnosis**:
```bash
# Check Keycloak logs
kubectl logs -n keycloak -l app=keycloak | grep -i oidc

# Test OIDC discovery
curl -k https://keycloak.internal/realms/platform/.well-known/openid-configuration

# Test token endpoint
curl -X POST https://keycloak.internal/realms/platform/protocol/openid-connect/token \
  -d "grant_type=client_credentials&client_id=<client>&client_secret=<secret>"
```

**Resolution**:
- Verify client configuration in Keycloak
- Ensure redirect URIs match exactly
- Sync clocks (NTP) across all components
- Regenerate client secret if needed

### SSSD/realmd AD Join Fails

**Symptoms**: Linux hosts cannot join AD domain.

**Likely Causes**:
- DNS not resolving AD DC
- Time skew > 5 minutes
- Incorrect realm name
- Firewall blocking AD ports

**Diagnosis**:
```bash
realm discover internal.example.com
realm join --user=domain-join-account internal.example.com
journalctl -u sssd -f
```

**Resolution**:
- Fix DNS resolution (forward + reverse)
- Sync time with AD DC (chrony)
- Verify realm name case-sensitivity
- Open firewall ports: 53, 88, 389, 636, 445, 3268, 3269

### OIDC Token Validation Fails

**Symptoms**: Applications reject OIDC tokens.

**Likely Causes**:
- JWKS endpoint unreachable
- Token expired
- Audience mismatch
- Issuer mismatch

**Diagnosis**:
```bash
# Check JWKS endpoint
curl -k https://keycloak.internal/realms/platform/protocol/openid-connect/certs

# Decode token
echo <token> | cut -d. -f2 | base64 -d | jq

# Check audience claim
echo <token> | cut -d. -f2 | base64 -d | jq .aud
```

**Resolution**:
- Ensure JWKS endpoint accessible from all clusters
- Verify client configuration matches token audience
- Check token expiration and clock sync

### LDAP/AD Sync Issues

**Symptoms**: Users/groups not syncing from AD to Keycloak.

**Likely Causes**:
- LDAP bind credentials incorrect
- User/Group filters too restrictive
- Pagination not configured
- TLS certificate not trusted

**Diagnosis**:
```bash
# Check Keycloak logs
kubectl logs -n keycloak -l app=keycloak | grep -i ldap

# Test LDAP connection
ldapsearch -H ldaps://ad.internal.example.com:636 \
  -D "cn=ldap-bind,ou=service-accounts,dc=internal,dc=example,dc=com" \
  -W -b "dc=internal,dc=example,dc=com" "(objectClass=user)"
```

**Resolution**:
- Verify bind DN and password
- Adjust user/group filters
- Enable LDAPS with valid TLS
- Configure page size for large directories

---

*Status: DRAFT | Owner: Identity Team | Last reviewed: 2026-11-23*