# cert-manager

cert-manager provisions and renews TLS certificates for ingress and service workloads only. Kubernetes internal PKI (API server, kubelet, front-proxy, etcd) is owned by Kubespray and is out of scope for cert-manager.

Two issuance paths exist:

- **Public ACME (Let's Encrypt):** requires outbound internet connectivity and a reachable ACME challenge endpoint (HTTP-01 or DNS-01). Optional, not a dependency, and unsuitable for air-gapped clusters.
- **Internal CA / Vault PKI:** the air-gapped path. Vault PKI provides CA signing; cert-manager requests and renews leaf certificates. See `secrets-management/pki/index.md` for the full PKI workflow, and `kubernetes/ingress/nginx-ingress.md` for the `internal-ca` ClusterIssuer example.

**Responsibility boundary:**

| Component | Responsibility |
|---|---|
| Vault PKI | Provides internal CA/intermediate signing capability; CA key never stored in Git |
| cert-manager | Requests and renews leaf certificates; writes TLS Secrets |
| Platform | Distributes internal CA trust to workloads and clients |

## Symptom: Certificate stuck in `Pending`

**Likely cause:** Issuer not ready, or ACME challenge not reachable (public ACME path only).

**Fix:**
```bash
kubectl get certificate -A
kubectl get issuer,clusterissuer -A
kubectl describe certificate <name> -n <ns>
```

**Self-check:** `kubectl get certificate <name> -n <ns>` shows `READY: True`.

## Symptom: cert-manager webhook cannot start

**Likely cause:** cert-manager webhook needs a certificate from itself (chicken-and-egg on first install).

**Fix:** Install cert-manager with `--set installCRDs=true` first, then apply issuers, then enable the webhook. Or use the Helm chart which handles ordering.

## Air-gapped deployment notes

- Use the internal CA/Vault PKI path; public ACME is not usable without internet connectivity.
- Mirror the cert-manager Helm chart and images to the internal registry (`registry.internal:5000/...`).
- Install CRDs before issuers; cert-manager writes certificates into Kubernetes Secrets automatically.

See `secrets-management/pki/index.md` for the complete root CA, intermediate CA, and cert-manager ClusterIssuer bootstrap order. The `internal-ca` ClusterIssuer example is in `kubernetes/ingress/nginx-ingress.md`.
