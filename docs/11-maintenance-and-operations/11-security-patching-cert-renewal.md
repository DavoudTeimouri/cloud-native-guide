# Security Patching & Certificate Renewal

## Purpose and scope
Security patching, certificate renewal, PKI/CA rotation, Vault unseal shares.

## Security patching
- Apply OS security patches monthly (maintenance window)
- Apply container runtime/Kubernetes patches as CVEs announced
- Test patches in staging before production
- Rollback plan documented before applying

## Certificate renewal
- cert-manager auto-renews in-cluster certificates (leaf 90 days, renew at 30 days)
- Vault PKI issues/renews certificates
- External certificates (load balancer, registry) renewed before expiry
- Expiry alerting at 14 days (warning) and 7 days (page)

## Implementation
```bash
# Check certificate expiry
openssl x509 -in <cert> -text -noout | grep "Not After"

# cert-manager certificates
kubectl get certificate -A
kubectl describe certificate <cert>

# Vault PKI
vault write pki/issue/<role> common_name=<name>
vault list pki/keys
```

## Validation
- All certificates valid; none expired or expiring within 14 days
- cert-manager Certificates Ready/True
- Vault PKI issuing certificates successfully

## Related
- [06 · Kubernetes Infrastructure (6.16 Security and Identity)](../06-kubernetes-infrastructure/6.16-security-and-identity.md)
- [08 · Troubleshooting (08-certificates-and-tls.md)](../08-troubleshooting-and-diagnostics/08-certificates-and-tls.md)
