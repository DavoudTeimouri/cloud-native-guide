# TLS/Certificates Troubleshooting

## Symptoms

- `openssl s_client` returns verification failure
- Kubernetes API rejects client certificates
- Pods fail with "x509: certificate has expired"
- cert-manager certificates stuck in Pending
- mTLS handshake failures between services

## Likely causes

- Certificate expired or not yet valid
- CA chain incomplete or wrong
- Wrong certificate for the hostname (SAN mismatch)
- Clock skew between client and server
- Private key doesn't match certificate
- Intermediate CA missing from chain

## Diagnostic commands

```bash
# Verify certificate
openssl x509 -in <cert.pem> -text -noout
openssl verify -CAfile <ca.pem> <cert.pem>

# Test TLS connection
openssl s_client -connect <host>:443 -servername <name>
openssl s_client -connect <host>:443 -showcerts

# Check certificate dates
openssl x509 -in <cert.pem> -noout -dates

# Check SANs
openssl x509 -in <cert.pem> -noout -ext subjectAltName

# Verify key matches cert
openssl x509 -noout -modulus -in <cert.pem> | openssl md5
openssl rsa -noout -modulus -in <key.pem> | openssl md5

# Check clock
date -u
```

## Expected healthy state

- Certificate valid (not expired, not yet valid)
- `openssl verify` returns "OK"
- `openssl s_client` returns verify return code 0
- Key modulus matches certificate modulus
- Clock within 5 minutes of server time

## Remediation

- Renew expired certificate
- Add missing intermediate CA to chain
- Reissue certificate with correct SANs
- Fix clock skew (see troubleshooting/time.md)
- Re-generate key/cert pair if mismatch
- Update trust store with correct CA

## Risks

- Renewing certificates can briefly break existing TLS connections
- Wrong CA in trust store can cause widespread verification failures
- Removing expired CA can break legacy systems still using it

## Verification

```bash
openssl verify -CAfile <ca.pem> <cert.pem>
openssl s_client -connect <host>:443 -servername <name> </dev/null 2>&1 | grep "Verify return code"
date -u```
