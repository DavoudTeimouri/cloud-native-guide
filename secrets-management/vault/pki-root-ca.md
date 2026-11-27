# Vault PKI Root CA Management

## Root CA Creation

The root CA is the trust anchor of the entire PKI hierarchy. **The root CA private key must never leave offline storage** — it should be generated in an air-gapped environment and stored in an HSM or encrypted offline vault secret.

### Initial Root CA Setup (online, in Vault)

```bash
# Enable PKI secrets engine at path 'pki'
vault secrets enable pki

# Configure root CA with 10-year validity (adjust per cryptographic policy)
vault write pki/root/generate/internal \
  common_name="cloud-native-guide.internal" \
  ttl=87600h \
  key_type=rsa \
  key_bits=4096

# Root CA is now live; immediately disable automatic issuance
# by creating a role that does not automatically sign certificates
vault write pki/roles/root-ca \
  client_flag=false \
  server_flag=false \
  max_ttl=87600h
```

### Root CA Export and Offline Storage

```bash
# Export the root CA certificate (PEM format)
vault read -field=certificate pki/root/cert > root-ca.crt

# Export the root CA private key (PEM, encrypted — password set separately)
vault read -field=private_key pki/root/key > root-ca-key.enc

# Store root-ca-key.enc in offline hardware security module or encrypted vault secret
# Store root-ca.crt in a secure offline location (e.g., air-gapped HSM, encrypted USB)

# Verify the exported key matches what Vault holds
openssl rsa -in root-ca-key.enc -check -noout 2>&1
```

### Root Key Rotation Prerequisites

See `secrets-management/pki/root-ca-rotation.md` for the full rotation runbook. The root key rotation process is multi-step and downtime-sensitive — do not attempt it without reading that document first.

## Intermediate CA Hierarchy

Intermediate CAs sign end-entity certificates and serve as the operational CA. They can be **strict** (only sign roles explicitly assigned) or **permissive** (sign any certificate within the role's path).

### Enable Intermediate CA (signed by root)

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

## Certificate Issuance Policies

### Certificate Issuance

```bash
# Issue a certificate for the server-api role
vault write pki/issue server-api \
  common_name="api.cloud-native-guide.internal" \
  alt_names="api.cloud-native-guide.internal" \
  ttl=8760h
```

### Certificate Output

The above command returns JSON with the certificate, request, serial number, and CA chain:

```json
{
  "request": "-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----\n",
  "certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
  "serial_number": "196604",
  "ca_chain": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n"
}
```

### Issuance Restrictions by Role

| Practice | Recommendation |
|---|---|
| `client_flag` | Set to `false` unless client auth is needed |
| `server_flag` | Set to `true` for server TLS certificates |
| `allow_subdomains` | `false` for exact matching; `true` for wildcards |
| `key_bits` | Minimum 4096 for root; 2048 acceptable for intermediates |
| `path_length` | Limit chain depth; `0` for end-entity, `1` for one intermediate |
| `ttl` | Align with application rotation cadence (hours to days) |

### Revocation Workflows

#### Revoke a Specific Certificate

```bash
# Revoke a specific certificate by serial number
vault write pki/revoke serial="196604"
```

#### Revoke All Certificates Matching a Pattern

```bash
# Revoke all certificates matching a serial prefix
vault write pki/revoke prefix="0x1234"
```

#### Refresh CRL After Revocation

After revocation, the CRL must be refreshed so all clients pick up the change:

```bash
# Force CRL regeneration
vault write pki/crl/set

# Verify the CRL includes the revoked serial
vault read pki/crl
```

### Revocation Best Practices

- Revoke certificates only when compromise is confirmed or access must be immediately terminated
- After revoking, always refresh the CRL and verify it propagates
- Clients may cache CRLs — reduce CRL cache TTL or force a CRL reload
- Do not revoke the old intermediate before all leaves under it have expired (see root CA rotation runbook)

## Root CA Rotation Procedures

Root key rotation is a multi-step, downtime-sensitive process. **See `secrets-management/pki/root-ca-rotation.md`** for the complete runbook.

### High-Level Rotation Flow

1. **Prepare.** Generate the new root key and self-signed root certificate offline. Record the custodian, storage location, and serial number. Do not touch the running intermediate yet.

2. **Distribute trust.** Add the new root certificate to every trust store that validates platform certificates — nodes, ingress clients, and any external system that pins the chain. Both roots are trusted at this point.

3. **Issue the new intermediate.** From the new root, issue an intermediate and import it into Vault's PKI engine alongside the old one.

4. **Switch issuance.** Point the cert-manager `ClusterIssuer` at the new intermediate. New certificates now chain to the new root; existing ones still chain to the old.

5. **Wait for leaf expiry.** Keep the old intermediate and old root trusted until the longest-lived certificate issued under the old chain has expired. Do not revoke the old intermediate before this point, or every unexpired certificate becomes invalid at once.

6. **Retire.** Revoke the old intermediate, remove the old root from trust stores, and archive the old root key according to the retention policy.

### Critical: Steps 2 and 5 are the long poles

- Skipping step 2 breaks every client that has not yet learned the new root
- Skipping step 5 causes an outage when the old intermediate is revoked

### Verification

```bash
# Issuer now points at the new intermediate
kubectl get clusterissuer -o yaml | grep -A3 vault

# Newly issued certificate chains to the new root
kubectl get certificate -A

# Validate the full chain
openssl s_client -connect <host>:443 -servername <host> </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer -dates

# Old root still trusted during the transition (expected until step 6)
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt <leaf>.pem
```

### Rollback

- **Before step 6:** Rollback is a configuration change — point the `ClusterIssuer` back at the old intermediate.
- **After step 6:** Rollback requires re-trusting the old root and re-issuing under the old intermediate — treat it as a new rotation, not a revert.

### Record Keeping

Record in the change ticket:
- Old and new root serials
- Intermediate serials
- The date each trust store was updated
- The expiry date of the last certificate issued under the old chain
- The date the old root was removed from trust stores

## Cross-References

- `secrets-management/pki/index.md` — Internal CA and PKI overview
- `secrets-management/pki/root-ca-rotation.md` — Root CA rotation runbook
- `secrets-management/vault/vault-architecture.md` §8.7 — Vault architecture reference
- `secrets-management/vault/pki-ca-management.md` — Broad PKI CA management
- `secrets-management/vault/secret-rotation.md` — General secret rotation procedures
- https://www.vaultproject.io/docs/pki — Official Vault PKI documentation