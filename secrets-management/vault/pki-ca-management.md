# Vault PKI CA Management

## Overview

Vault's PKI secrets engine provides a certificate authority (CA) capable of signing X.509 certificates. This document covers the full lifecycle: root and intermediate CA configuration, certificate issuance, revocation, CRL distribution, role management, and rotation procedures.

---

## Root CA Configuration

The root CA is the trust anchor. **The root CA private key must never leave offline storage.** Intermediate CAs derive trust from the root and handle day-to-day certificate issuance.

### Initial Root CA Setup

```bash
# Enable PKI secrets engine at path 'pki'
vault secrets enable pki

# Configure root CA with 10-year validity
vault write pki/root/generate/internal \
  common_name="cloud-native-guide.internal" \
  ttl=87600h \
  key_type=rsa \
  key_bits=4096

# Root CA is now live; immediately disable automatic issuance
vault write pki/roles/root-ca \
  client_flag=false \
  server_flag=true \
  max_ttl=87600h
```

### Root CA Export and Offline Storage

```bash
# Export the root CA certificate
vault read -field=certificate pki/root/cert > root-ca.crt

# Export the root CA private key (PEM, encrypted)
vault read -field=private_key pki/root/key > root-ca-key.enc

# Store root-ca-key.enc in offline hardware security module or encrypted vault secret
# Store root-ca.crt in a secure offline location (e.g., air-gapped HSM, encrypted USB)
```

### Root Key Rotation

Root key rotation is a multi-step, downtime-sensitive process:

1. Generate a new root CA using `vault write pki/root/generate/internal`
2. Issue a new intermediate CA from the new root
3. Update all intermediate CA roles to point to the new intermediate
4. Wait for all existing certificates to expire before decommissioning the old root
5. Revoke the old intermediate and rotate it out

**Document the runbook in `secrets-management/pki/root-ca-rotation.md`.**

---

## Intermediate CA Configuration

Intermediate CAs sign end-entity certificates and serve as the operational CA. They can be **strict** (only sign roles explicitly assigned) or **permissive** (sign any certificate within the role's path).

### Enable Intermediate CA

```bash
# Generate a new intermediate CA signed by the root
vault write pki/intermediate/generate/internal \
  common_name="cloud-native-guide Intermediate CA" \
  ttl=87600h \
  key_type=rsa \
  key_bits=4096
```

### Intermediate CA Registration with Root

```bash
# Download the root CA certificate for CSR signing
vault read -field=certificate pki/root/cert > root-ca.crt

# Register the intermediate CA with the root
vault write pki/intermediate/set-signed \
  signing_cert=@root-ca.crt \
  csr=pki_intermediate_csr.csr
```

### Intermediate CA Roles

Define roles that map certificate fields to paths where certificates are stored.

```bash
# Strict role: only signs certificates with exact SAN matching
vault write pki/roles/server-api \
  domains="api.cloud-native-guide.internal" \
  ttl=8760h \
  max_ttl=87600h \
  allow_subdomains=false \
  client_flag=false \
  server_flag=true \
  key_type=rsa \
  key_bits=4096 \
  path_length=0 \
  sans="DNS:api.cloud-native-guide.internal"

# Permissive wildcard role for internal services
vault write pki/roles/internal-service \
  domains="*.internal.cloud-native-guide" \
  ttl=72h \
  max_ttl=8760h \
  allow_subdomains=true \
  client_flag=false \
  server_flag=true \
  key_type=rsa \
  key_bits=2048 \
  path_length=1
```

### CRL Distribution Point

Configure where the Certificate Revocation List (CRL) is published:

```bash
# Enable CRL generation
vault write pki/crl/set \
  crl_distribution_points="http://pki.crl.cloud-native-guide.internal/crl.pem"

# Set CRL expiry (default is 24h; adjust per policy)
vault write pki/crl/set \
  expiry="24h"
```

---

## Certificate Issuance

### Issue a Certificate

```bash
# Issue a certificate for the server-api role
vault write pki/issue server-api \
  common_name="api.cloud-native-guide.internal" \
  alt_names="api.cloud-native-guide.internal" \
  ttl=8760h
```

### Certificate Output

The above command returns:

```json
{
  "request": "-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----\n",
  "certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
  "serial_number": "196604",
  "ca_chain": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n"
}
```

### Revoke a Certificate

```bash
# Revoke a specific certificate by serial number
vault write pki/revoke serial="196604"

# Revoke all certificates matching a pattern
vault write pki/revoke prefix="0x1234"
```

### Revocation List (CRL)

After revocation, the CRL must be refreshed:

```bash
# Force CRL regeneration
vault write pki/crl/set

# Verify the CRL includes the revoked serial
vault read pki/crl
```

---

## Role Management

### List All Roles

```bash
vault list pki/roles/
```

### Read Role Configuration

```bash
vault read pki/roles/server-api
```

### Update Role

```bash
# Add a new SAN
vault write pki/roles/server-api \
  altnames="DNS:api2.cloud-native-guide.internal"

# Change TTL
vault write pki/roles/server-api ttl=48h
```

### Delete Role

```bash
vault delete pki/roles/deprecated-role
```

### Role Best Practices

| Practice | Recommendation |
|---|---|
| `client_flag` | Set to `false` unless client auth is needed |
| `server_flag` | Set to `true` for server TLS certificates |
| `allow_subdomains` | `false` for exact matching; `true` for wildcards |
| `key_bits` | Minimum 4096 for root; 2048 acceptable for intermediates |
| `path_length` | Limit chain depth; `0` for end-entity, `1` for one intermediate |
| `ttl` | Align with application rotation cadence (hours to days) |

---

## Certificate Rotation Procedures

### Automated Rotation (cert-manager Integration)

When using cert-manager with the Vault PKI issuer:

```yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: vault-pki
  namespace: cert-manager
spec:
  vault:
    server: "https://vault.cloud-native-guide.internal:8200"
    path: "pki/issue/server-api"
    secretName: vault-tls-secret
    ttl: "8760h"
    maxTTL: "87600h"
    clientCertificateFile: "/certs/client.root.ca.crt"
    clientKeyFile: "/certs/client.root.ca.key"
```

### Manual Rotation

1. **Issue new certificate** from the same or updated role
2. **Deploy the new certificate** to the target service
3. **Update service configuration** to use the new cert
4. **Revoke the old certificate** once the new one is confirmed valid
5. **Wait for certificate expiry** before cleaning up old roles/CRL entries

### Rotation Checklist

- [ ] New certificate issued with correct SANs and expiry
- [ ] Certificate deployed and service validated
- [ ] Old certificate revoked via `vault write pki/revoke`
- [ ] CRL regenerated and published
- [ ] All clients updated to use new certificate
- [ ] Old certificate removed from trust stores
- [ ] Rotation documented and dated

---

## Rotation Schedules

| Component | Recommended Rotation | Trigger |
|---|---|---|
| Root CA private key | Annually or after compromise | Security incident, key expiration |
| Intermediate CA certificate | Every 1–2 years | Expiry, policy change |
| Service server certificates | Per application cycle or 30–90 days | Expiry, compliance |
| CRL | Every 24 hours (configurable) | Automatic |
| Vault PKI roles | As needed when service topology changes | Topology change, role deprecation |

---

## Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| "no valid certificate found" | SAN mismatch or role misconfiguration | Verify `domains` and `altnames` in role; check `common_name` |
| CRL not updating | CRL expiry too long or publication path inaccessible | Reduce CRL expiry; verify web server serving CRL |
| Certificate revocation not taking effect | Client caching old CRL | Reduce CRL cache time; force CRL reload |
| "max path length exceeded" | `path_length` set too high in role | Lower `path_length`; restructure CA hierarchy |
| Intermediate CA not signing | Intermediate not registered with root | Run `vault write pki/intermediate/set-signed` |

### Debug Commands

```bash
# Check current CRL
vault read pki/crl

# List all active roles
vault list pki/roles/

# Show role details
vault read pki/roles/<role-name>

# Check active certifications
vault list pki/certs/
```

---

## Cross-References

- `secrets-management/vault/architecture.md` — Vault deployment architecture
- `secrets-management/vault/secret-rotation.md` — General secret rotation procedures
- `secrets-management/vault/policy-management.md` — Vault policy management
- `kubernetes/security/security-controls.md` — TLS and PKI in Kubernetes context
- `identity/directory-integration.md` — Certificate-based identity integration
- `secrets-management/pki/root-ca-rotation.md` — Root CA rotation runbook
- `https://www.vaultproject.io/docs/pki` — Official Vault PKI documentation
