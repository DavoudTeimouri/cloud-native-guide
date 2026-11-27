# cert-manager Troubleshooting

## A. Purpose and scope

Troubleshooting guide for cert-manager certificate issuance failures. Covers certificates stuck in Pending, webhook startup failures, ClusterIssuer configuration errors, and ACME challenge failures. Cross-references `service-mesh/evaluation.md` and `kubespray/kubespray-deployment.md`.

## B. Certificate stuck in Pending

### Symptom: `kubectl get certificate` shows `Ready: False` with reason `Pending`

**Possible causes:**
- Issuer not ready
- ACME challenge not reachable (public ACME path only)
- Secret not found for issuer TLS key
- DNS-01 challenge not configured for internal DNS

**Verification:**
```bash
kubectl describe certificate <name> -n <ns>
kubectl get issuer -n <ns>
kubectl get clusterissuer
```

**Fix:**
- Verify issuer is `Ready`: `kubectl get clusterissuer -o yaml`
- For public ACME: ensure outbound internet connectivity and reachable challenge endpoint
- For internal CA/Vault PKI: verify Vault PKI CA is operational
- Create the referenced secret if missing

## C. cert-manager webhook cannot start

### Symptom: `cert-manager-webhook` pod crash-looping

**Possible causes:**
- Webhook needs a certificate from itself (chicken-and-egg on first install)
- cert-manager CRDs not installed before webhook starts

**Verification:**
```bash
kubectl -n cert-manager get pods -l app=webhook
kubectl -n cert-manager logs -l app=webhook -c webhook
kubectl get crd | grep cert-manager
```

**Fix:**
- Install cert-manager with `--set installCRDs=true` first, then apply issuers, then enable webhook
- Or use the Helm chart which handles ordering automatically

## D. ClusterIssuer configuration errors

### Symptom: `ClusterIssuer` not `Ready`, certificates reference unknown issuer

**Possible causes:**
- `ClusterIssuer` not deployed or not `Ready`
- Certificate references wrong issuer name or namespace
- `ClusterIssuer` is namespace-scoped (use `Issuer` instead)

**Verification:**
```bash
kubectl get clusterissuer -o yaml
kubectl get issuer -A
kubectl describe certificate <name> -n <ns>
```

**Fix:**
- Deploy `ClusterIssuer` before certificates that reference it
- Use `Issuer` for namespace-scoped certificate authority
- Verify issuer name matches in certificate `spec.issuerRef`

## E. ACME challenge failures

### Symptom: `Order` or `Challenge` resources show failure

**Possible causes:**
- DNS-01 challenge: DNS provider credentials missing or wrong
- HTTP-01 challenge: ingress not reachable from public internet
- TLS-ALPN challenge: port 443 not accessible

**Verification:**
```bash
kubectl get order -n <ns>
kubectl get challenge -n <ns>
kubectl describe challenge <name> -n <ns>
```

**Fix:**
- For DNS-01: verify DNS provider secret exists and credentials are valid
- For HTTP-01: ensure ingress controller is reachable from public internet
- For internal CA/Vault PKI path: skip ACME entirely, use Vault PKI issuer

## F. Cross-references

- `service-mesh/evaluation.md` — Service mesh evaluation with cert-manager context
- `kubespray/kubespray-deployment.md` — Kubespray deployment with cert-manager integration
