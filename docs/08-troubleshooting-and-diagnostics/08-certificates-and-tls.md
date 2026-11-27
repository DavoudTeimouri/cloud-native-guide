# Certificates and TLS

## Symptoms
- TLS handshake failing
- Certificate expired or expiring soon
- cert-manager Certificate not issuing
- Ingress TLS not working
- Vault PKI not issuing certificates

## Possible causes
- Certificate expired
- CA certificate not trusted by client
- cert-manager Certificate resource failing
- Issuer not ready or misconfigured
- DNS-01 or HTTP-01 challenge failing

## Diagnostic commands
```bash
# Certificate
kubectl get certificate -A
kubectl describe certificate <cert>
kubectl get issuer,clusterissuer -A
kubectl describe issuer <issuer>

# Ingress TLS
kubectl get ingress <ingress> -o yaml
kubectl describe ingress <ingress>

# Vault PKI
kubectl get pods -n vault
vault write pki/issue/<role> common_name=<name>

# OpenSSL
openssl s_client -connect <host>:443 -showcerts
openssl x509 -in <cert> -text -noout | grep -A2 "Not After"
```

## Expected output
- certificate: Ready/True
- issuer: Ready/True
- ingress: TLS secret bound
- s_client: certificate chain verified, not expired

## Investigation procedure
1. Check Certificate resource status and conditions
2. Check Issuer/ClusterIssuer status
3. Check Ingress TLS secret reference
4. Test TLS handshake with openssl s_client
5. Check cert-manager logs for issuance errors

## Resolution
- Fix Certificate/ Issuer resource; renew certificate
- Install/update CA trust on client
- Fix Ingress TLS secret reference
- Fix DNS-01 or HTTP-01 challenge (DNS credentials, reachability)

## Verification
- Certificate Ready/True; s_client shows valid unexpired certificate; TLS handshake succeeds

## Prevention
- Monitor certificate expiry; alert at 14/7 days
- Enable cert-manager auto-renewal
- Monitor Issuer health; alert on failure

## Related
- [06 · Kubernetes Infrastructure (6.16 Security and Identity)](../06-kubernetes-infrastructure/6.16-security-and-identity.md)
- [07 · Software-Defined Storage (7.7 Maintenance and Data Protection)](../07-software-defined-storage/7.7-maintenance-and-data-protection.md)
