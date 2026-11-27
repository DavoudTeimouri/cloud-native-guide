# Certificate Inventory

## A. Purpose and scope

Document certificate inventory: kube-apiserver, kubelet, front-proxy, etcd, OIDC CA, ingress certs, Vault unseal keys, backup locations.

Cross-references `kubernetes/control-plane/cert-rotation.md`, `kubernetes/control-plane/index.md` §Certificate expiry, `secrets-management/vault/vault-architecture.md`.

## B. Certificate inventory table

| Certificate | Purpose | Location | Issued by | Expiry | Backup |
|-------------|---------|----------|-----------|--------|--------|
| kube-apiserver.crt | API server TLS | /etc/kubernetes/pki/ | Kubespray PKI | ~1 year | /backups/pki/ |
| kubelet.crt | kubelet TLS | /etc/kubernetes/pki/ | Kubespray PKI | ~1 year | /backups/pki/ |
| front-proxy-client.crt | Front proxy client | /etc/kubernetes/pki/ | Kubespray PKI | ~1 year | /backups/pki/ |
| etcd/ca.crt | etcd CA | /etc/kubernetes/pki/etcd/ | Kubespray PKI | ~10 years | /backups/pki/ |
| etcd/server.crt | etcd server TLS | /etc/kubernetes/pki/etcd/ | Kubespray PKI | ~1 year | /backups/pki/ |
| etcd/client.crt | etcd client TLS | /etc/kubernetes/pki/etcd/ | Kubespray PKI | ~1 year | /backups/pki/ |
| sa.key/sa.crt | Service account keys | /etc/kubernetes/pki/ | Kubespray PKI | N/A | /backups/pki/ |
| oidc-ca.crt | OIDC issuer CA | /etc/kubernetes/pki/ | Manual owner-operated | ~2 years | Vault |
| ingress-tls.crt | Ingress TLS | /etc/kubernetes/pki/ingress/ | Manual or cert-manager | ~90 days | /backups/pki/ |
| vault-unseal-keys | Vault unseal shares | Vault data dir / offsite | Vault key ceremony | N/A | Offline storage |

## C. Backup locations

| Backup type | Location | Frequency |
|-------------|----------|-----------|
| PKI directory | /backups/pki/ | Daily |
| Vault unseal keys | Offline key storage | On rotation |
| Vault raft snapshot | /backups/vault/ | Every 4 hours |

## D. Certificate expiry monitoring

```bash
# Check all certificate expiry dates
find /etc/kubernetes/pki -name '*.crt' -exec sh -c 'echo "{}:"; openssl x509 -in "{}" -noout -enddate -dates' \;

# Check ingress certificate expiry
kubectl get secret -l ingress-tls -o jsonpath='{.items[*].metadata.name}'

# Alert when < 30 days remaining
```

## E. Cross-references

- `kubernetes/control-plane/cert-rotation.md` — Certificate rotation procedure
- `kubernetes/control-plane/index.md` §Certificate expiry — Control plane context
- `secrets-management/vault/vault-architecture.md` — Vault certificate storage
