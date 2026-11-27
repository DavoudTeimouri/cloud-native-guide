# Ingress TLS Configuration

## A. Purpose and scope

This document covers Ingress TLS configuration for Kubernetes clusters using
Ingress resources, cert-manager, and Let's Encrypt. It addresses certificate
management, TLS termination, custom certificate deployment, and HTTP-to-HTTPS
redirect policies.

## B. Requirements

- A Kubernetes cluster with an Ingress controller installed (e.g., NGINX,
  Cilium, Contour).
- cert-manager v1.11+ installed and configured.
- A DNS domain reachable from the cluster (for Let's Encrypt challenges).
- Appropriate RBAC permissions for cert-manager to create ClusterIssuer/Issuer
  resources.
- Node-level access to port 80 and 443 for ACME challenges.

## C. Offline preparation

- cert-manager chart: `harbor.internal/charts/cert-manager` (v1.11.0).
- Images: `cert-manager/controller`, `cert-manager/webhook`,
  `cert-manager/ca-controller`, `cert-manager/cainjector`.
- ClusterIssuer resources must be mirrored in the internal chart repository.
- If using external-dns, ensure it mirrors DNS records for propagated domains.

## D. Installation

### 1. Install cert-manager

```bash
helm repo add jet https://charts.jetstack.io
helm repo update jet

helm install cert-manager jet/cert-manager \
  --namespace cert-manager --create-namespace \
  --version 1.11.0 \
  --set image.repository=harbor.internal/platform/cert-manager \
  --set node-drainer.enabled=false
```

### 2. Create the cert-manager namespace

```bash
kubectl create namespace cert-manager
```

### 3. Deploy a ClusterIssuer

#### a) Let's Encrypt production (ACME DNS-01 challenge)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
    - dns01:
        provider: azure
        resourceGroup: my-rg
        subscriptionID: my-sub-id
```

#### b) Let's Encrypt staging (for testing)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-staging-key
    solvers:
    - dns01:
        provider: azure
        resourceGroup: my-rg
        subscriptionID: my-sub-id
```

#### c) Self-signed CA for internal/custom certificates

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned
spec:
  selfSigned: {}
```

## E. TLS Termination

Ingress resources terminate TLS at the Ingress controller. The flow is:

1. Client initiates an HTTPS connection to the Ingress VIP.
2. The Ingress controller presents the TLS certificate.
3. TLS is decrypted and the cleartext HTTP request is forwarded to the backend service.

### 1. Automatic TLS with cert-manager

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: payment-api-ingress
  namespace: payments
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - payments.example.com
    secretName: tls-payments
  rules:
  - host: payments.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: payment-api
            port:
              number: 443
```

### 2. Manual TLS with a pre-provisioned secret

```bash
# Create a TLS secret from existing certificates
kubectl create secret tls tls-manual \
  --key=key.pem \
  --cert=cert.pem \
  --namespace payments
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-api-ingress
  namespace: internal
  annotations:
    cert-manager.io/cluster-issuer: "selfsigned"
spec:
  tls:
  - hosts:
    - internal-api.example.com
    secretName: tls-manual
  rules:
  - host: internal-api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-api
            port:
              number: 8080
```

## F. Custom Certificates

### 1. Deploying a custom CA bundle

```bash
# Create a ConfigMap with the CA bundle
kubectl create configmap custom-ca \
  --from-file=ca.crt=/path/to/internal-ca.crt \
  -n cert-manager
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: internal-ca-bundle
  namespace: cert-manager
data:
  ca.crt: |
    -----BEGIN CERTIFICATE-----
    MIIDazCCAl+gAwIBAgIUCg+y... (truncated)
    -----END CERTIFICATE-----
```

### 2. Reference the CA in a ClusterIssuer

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: internal-ca
spec:
  ca:
    secretName: internal-ca-bundle
    rootKeySelector: {}
    rootCertificateSelector: {}
```

### 3. Issue a certificate for an internal host

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: internal-api-cert
  namespace: internal
spec:
  secretName: tls-internal-api
  issuerRef:
    name: internal-ca
    kind: ClusterIssuer
  commonName: internal-api.example.com
  dnsNames:
  - internal-api.example.com
  sans:
  - api-gateway.internal.example.com
  renewable: false
```

## G. HTTP-to-HTTPS Redirect Policies

### 1. Global redirect via Ingress annotation

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  namespace: payments
  annotations:
    # Redirect all HTTP traffic to HTTPS
    nginx.ingress.kubernetes.io/rewrite-to: https://$host$request_uri
    # OR for Contour/Envoy:
    # ingress.kubernetes.io/ssl-redirect: "true"
spec:
  rules:
  - host: web.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-frontend
            port:
              number: 80
```

### 2. Explicit HTTP redirect route

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: redirect-ingress
  namespace: payments
  annotations:
    # Redirect anything under /old-path to the HTTPS equivalent
    nginx.ingress.kubernetes.io/rewrite-to: https://$host/new-path$request_uri
spec:
  rules:
  - host: web.example.com
    http:
      paths:
      - path: /old-path
        pathType: Prefix
        backend:
          service:
            name: web-frontend
            port:
              number: 80
  - host: web.example.com
    https:
      paths:
      - path: /new-path
        pathType: Prefix
        backend:
          service:
            name: web-frontend
            port:
              number: 443
```

### 3. Catch-all HTTP redirect to HTTPS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secure-ingress
  namespace: payments
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    # Alternatively, use a dedicated redirect Ingress with no backend
spec:
  defaultBackend:
    service:
      name: web-frontend
      port:
        number: 80
  rules:
  - host: web.example.com
    http:
      paths: []  # Explicitly disable HTTP paths
    https:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-frontend
            port:
              number: 443
```

## H. Validation

```bash
# Check that the Ingress has TLS configured
kubectl get ingress -A -o yaml

# Verify the certificate is issued and valid
kubectl describe certificate -A

# Check cert-manager status
kubectl -n cert-manager get pod -l app.kubernetes.io/name=cert-manager

# Test the TLS connection
openssl s_client -connect payments.example.com:443 -servername payments.example.com </dev/null 2>&1 | head -20

# Verify the error budget impact
# If using SLOs: ensure TLS failures are counted as errors
```

## I. Known traps

1. **ClusterIssuer vs Issuer scope** — Use `ClusterIssuer` for cluster-wide
   TLS; use `Issuer` for namespace-scoped certificates.
2. **Propagation delay** — ACME certificate issuance can take 1–5 minutes after
   the Ingress is updated; cert-manager does not auto-reconcile on every
   Ingress change.
3. **Rate limits** — Let's Encrypt enforces per-domain and global rate limits.
   Use the staging server for development and testing.
4. **Secret mounting** — cert-manager creates the TLS secret referenced in
   `tls.secretName`; do not manually manage this secret if cert-manager is
   the sole issuer.
5. **Default backend** — Ensure the Ingress `defaultBackend` serves a valid
   page or redirect; otherwise clients may hit a 404 on HTTP-to-HTTPS redirect.
6. **DNS propagation** — For DNS-01 challenges, ensure the DNS provider's
   propagation delay is accounted for before expecting the certificate to
   become ready.
7. **TLS version/cipher mismatch** — Verify the Ingress controller supports
   the desired TLS version (1.2/1.3) and that cert-manager's issued
   certificates negotiate the expected protocol.

## J. Related Documentation

- `kubernetes/networking/cilium.md` — Cilium CNI with embedded Ingress
- `kubernetes/networking/metallb.md` — MetalLB load-balancer integration
- cert-manager official documentation: https://cert-manager.io/docs/
- Let's Encrypt ACME specification: https://acme-v02.api.letsencrypt.org/directory
