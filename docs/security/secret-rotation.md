# Vault Secret Rotation

## A. Purpose and scope

Document secret rotation procedures for HashiCorp Vault: PKI certificate rotation, Kubernetes secret rotation, application secret rotation, and etcd encryption key rotation.

Cross-references `secrets-management/vault/vault-architecture.md`, `secrets-management/pki/root-ca-rotation.md`, `secrets-management/kubernetes-integration/secret-delivery.md`, `lifecycle/backup/backup-and-dr.md` §Vault.

## B. Vault PKI certificate rotation

### 1. Rotate intermediate CA

```bash
# Generate new intermediate CA
vault write -format=json pki_int/intermediate/set-signed \
  certificate=@new_intermediate.crt \
  ca_chain=@new_ca_chain.crt

# Update the role to use the new CA
vault write pki/roles/<role-name> \
  allowed_domains=<domain> \
  allow_subdomains=true \
  max_ttl="72h"

# Verify new certificates are issued with the new CA
vault write pki/issue/<role-name> common_name=test.<domain>
```

### 2. Rotate leaf certificates

Certificates issued by Vault PKI have short TTLs (typically 24-72h). Rotation is automatic on renewal:

```bash
# Renew a certificate before expiry
vault write pki/issue/<role-name> common_name=<name>

# Revoke a compromised certificate
vault write pki/revoke serial_number=<serial>
```

### 3. Verification

```bash
# Check CA expiry
vault read pki_int/cert/ca

# Check CRL
vault read pki/crl/pem
```

## C. Kubernetes secret rotation

### 1. Rotate secrets via External Secrets Operator

If using External Secrets Operator with Vault:

```bash
# Update the secret in Vault
vault kv put secret/<path> key=<new-value>

# External Secrets Operator automatically syncs to Kubernetes
kubectl get secret <k8s-secret> -o yaml | grep data:
```

### 2. Rotate service account tokens

Service account tokens are automatically rotated by Kubernetes. Verify:

```bash
kubectl get serviceaccount <sa> -o yaml
kubectl describe serviceaccount <sa>
```

### 3. Verify rotation

```bash
# Check secret age
kubectl get secret <secret> --sort-by=.metadata.creationTimestamp

# Verify secret content matches Vault
vault kv get secret/<path>
```

## D. Application secret rotation

### 1. Application reads secrets at startup

Applications should read secrets from Vault at startup and cache them in memory. Rotation requires restart:

```bash
# Rollout restart to pick up new secrets
kubectl rollout restart deployment/<app>

# Verify new secret is in use
kubectl exec <pod> -- <app-command> --verify-secret
```

### 2. Dynamic secrets

Vault dynamic secrets (e.g., database credentials) are short-lived and automatically expire:

```bash
# Check lease
vault lease lookup <lease-id>

# Revoke lease early if compromised
vault lease revoke <lease-id>
```

## E. etcd encryption key rotation

### 1. Rotate etcd encryption keys

```bash
# Create new encryption config
cat > /etc/kubernetes/encryption-config.yaml << 'EOF'
kind: EncryptionConfiguration
apiVersion: apiserver.k8s.io/v1
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: new-key-<date>
              key: <new-base64-key>
            - name: old-key-<date>
              key: <old-base64-key>
      - identity: {}
EOF

# Apply new config to kube-apiserver
kubectl apply -f /etc/kubernetes/encryption-config.yaml

# Re-encrypt all secrets
kubectl get secrets --all-namespaces -o json | \
  kubectl apply -f -
```

### 2. Verify

```bash
# Check encryption config is active
kubectl get --raw='/readyz?verbose'

# Verify secrets are encrypted in etcd
ETCDCTL_API=3 etcdctl get /registry/secrets/ --prefix --keys-only --write-out=table
```

## E. Rotation schedule

| Secret type | Rotation frequency | Method |
|-------------|-------------------|--------|
| Vault PKI intermediate CA | Every 1-2 years | Manual via Vault CLI |
| Leaf certificates | 24-72h (TTL-based) | Automatic renewal |
| Kubernetes secrets | As needed | External Secrets Operator sync |
| Service account tokens | Automatic | Kubernetes controller |
| Application secrets | 90 days | Application restart |
| etcd encryption keys | Every 90 days | Manual re-encryption |
| Vault unseal keys | Every 365 days | Key ceremony |

## F. Cross-references

- `secrets-management/vault/vault-architecture.md` — Vault deployment architecture
- `secrets-management/pki/root-ca-rotation.md` — PKI root CA rotation
- `secrets-management/kubernetes-integration/secret-delivery.md` — Secret delivery to workloads
- `lifecycle/backup/backup-and-dr.md` §Vault — Vault backup RPO/RTO
