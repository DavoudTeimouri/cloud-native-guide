# cert-manager

cert-manager provisions and renews TLS certificates (Let's Encrypt, internal CA, Vault PKI).

## Symptom: Certificate stuck in `Pending`

**Likely cause:** Issuer not ready, or ACME challenge not reachable.

**Fix:**
```bash
kubectl get certificate -A
kubectl get issuer,clusterissuer -A
kubectl describe certificate <name> -n <ns>
```

**Self-check:** `kubectl get certificate <name> -n <ns>` shows `READY: True`.

## Symptom: cert-manager webhook cannot start

**Likely cause:** cert-manager cert-manager-webhook needs a certificate from itself (chicken-and-egg on first install).

**Fix:** Install cert-manager with `--set installCRDs=true` first, then apply issuers, then enable the webhook. Or use the Helm chart which handles ordering.

**Ponytail:** Scope ceiling — cert-manager install and basic issuance. Add ACME DNS01, Vault PKI issuer, and certificate rotation when those patterns are used.
