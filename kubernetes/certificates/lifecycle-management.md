# Kubernetes Certificate Lifecycle Management

## Overview

Kubernetes clusters rely on X.509 certificates for mutual TLS authentication between components. This document covers the complete certificate lifecycle: issuance, renewal, rotation, and emergency procedures.

---

## Certificate Authority Rotation

### Root CA Rotation

1. **Generate new root key and CSR**
   ```bash
   openssl genrsa -out new-root-ca.key 4096
   openssl req -new -key new-root-ca.key -out new-root-ca.csr \
     -subj "/CN=kubernetes-root-CA"
   ```

2. **Sign intermediate CA (if used)**
   ```bash
   openssl x509 -req -in new-root-ca.csr -CA existing-intermediate-ca.pem \
     -CAkey existing-intermediate-ca.key -CAcreateserial \
     -out new-intermediate-ca.pem -days 3650
   ```

3. **Distribute new CA bundle to all nodes**
   - Update ConfigMaps containing CA certificates
   - Rotate kubelet client certificates signed by new CA
   - Rotate etcd peer and client certificates
   - Rotate front-proxy certificates
   - Rotate service account signing keys

4. **Validate cluster health after rotation**
   ```bash
   kubectl cluster-info --kubeconfig=kubeconfig-with-new-ca
   ```

### Intermediate CA Rotation

Follow the same process as root CA rotation, but maintain the root CA trust anchor.

---

## Kubelet Certificate Renewal

### Automatic Renewal (recommended)

Kubelet can automatically rotate its serving certificate via the `--rotate-certificates` flag (default: `true` in kubeadm-managed clusters).

```yaml
# kubelet configuration snippet
kubeconfig: /etc/kubernetes/kubeconfig
clientcafile: /etc/kubernetes/pki/ca.crt
autoRotateCertificates: true
```

### Manual Renewal

1. **Check certificate expiration**
   ```bash
   openssl x509 -in /var/lib/kubernetes/kubelet-client-current.pem -text -noout | grep -A2 "Validity"
   ```

2. **Generate new kubelet client certificate**
   ```bash
   openssl genrsa -out kubelet-client.key 2048
   openssl req -new -key kubelet-client.key -out kubelet-client.csr \
     -subj "/CN=kubelet-client-kubernetes-node-XXXXXXXXXXXX"

   # Sign with cluster CA
   kubectl certificate sign --cluster=kubernetes \
     --cert=ca.crt --key=ca.key \
     --request=kubelet-client.csr \
     --kubeconfig=kubeconfig \
     --duration=2160h
   ```

3. **Distribute and restart kubelet**
   ```bash
   cp kubelet-client.pem /var/lib/kubernetes/kubelet-client-current.pem
   systemctl restart kubelet
   ```

---

## etcd Peer and Client Certificates

### Certificate Components

| Certificate Type | CN | Usage |
|-----------------|-----|-------|
| **peer** | `etcd-peer` | etcd peer communication |
| **client** | `etcd-client` | etcd API client communication |
| **legacy-client** | `etcd-legacy` | Deprecated: legacy kubelet etcd access |

### Rotation Procedure

1. **Generate new etcd certificates**
   ```bash
   # Generate peer key and CSR
   openssl genrsa -out etcd-peer.key 2048
   openssl req -new -key etcd-peer.key -out etcd-peer.csr \
     -subj "/CN=etcd-peer"

   # Generate client key and CSR
   openssl genrsa -out etcd-client.key 2048
   openssl req -new -key etcd-client.key -out etcd-client.csr \
     -subj "/CN=etcd-client"

   # Sign certificates
   kubectl certificate sign --cluster=kubernetes \
     --cert=ca.crt --key=ca.key \
     --request=etcd-peer.csr \
     --kubeconfig=kubeconfig \
     --duration=2160h --name=etcd-peer

   kubectl certificate sign --cluster=kubernetes \
     --cert=ca.crt --key=ca.key \
     --request=etcd-client.csr \
     --kubeconfig=kubeconfig \
     --duration=2160h --name=etcd-client
   ```

2. **Distribute certificates to etcd members**
   ```bash
   cp etcd-peer.pem /etc/etcd/peer/peer.pem
   cp etcd-client.pem /etc/etcd/client/client.pem
   # Distribute CA certificate if rotated
   cp ca.crt /etc/etcd/ca/ca.crt
   ```

3. **Restart etcd services**
   ```bash
   systemctl restart etcd
   ```

4. **Verify etcd health**
   ```bash
   etcdctl endpoint health --endpoints=https://localhost:2379
   ```

---

## Front-Proxy Certificates

### Purpose

Front-proxy certificates protect the Kubernetes API server access via the front-proxy endpoint (default: `:8080`). These control who can interact with the cluster via `kubectl --request-header-urlPrefix=`.

### Rotation Procedure

1. **Generate new front-proxy key and CSR**
   ```bash
   openssl genrsa -out front-proxy.key 2048
   openssl req -new -key front-proxy.key -out front-proxy.csr \
     -subj "/CN=front-proxy-client"
   ```

2. **Sign with appropriate extensions**
   ```bash
   kubectl certificate sign --cluster=kubernetes \
     --cert=ca.crt --key=ca.key \
     --request=front-proxy.csr \
     --kubeconfig=kubeconfig \
     --duration=2160h --name=front-proxy-client \
     --extfile=<(printf "subjectAltName=DNS:front-proxy-client,IP:127.0.0.1")
   ```

3. **Distribute to front-proxy components**
   ```bash
   cp front-proxy.pem /etc/kubernetes/front-proxy/front-proxy-client.pem
   # Update kubeconfig for kubectl access
   cp front-proxy.kubeconfig /etc/kubernetes/front-proxy/kubeconfig
   ```

4. **Restart kube-apiserver (if serving front-proxy cert)**
   ```bash
   systemctl restart kube-apiserver
   ```

---

## Service Account Keys

### Token Signing Key Rotation

1. **Check current key expiration**
   ```bash
   # List signing keys
   kubectl get configmap/tka -n kube-system -o yaml
   ```

2. **Rotate token signing key**
   ```bash
   # Create new signing key
   openssl genrsa -out tsig-key.pem 2048

   # Create CA certificate for signing
   openssl req -new -x509 -key tsig-key.pem -out tsig-key.crt \
     -days 365 -subj "/CN=token-signing-key"

   # Create ConfigMap with new key
   kubectl create configmap tka --from-file=tsig-key.pem \
     --from-file=tsig-key.crt -n kube-system --dry-run=client -o yaml | kubectl apply -f -
   ```

3. **Rotate aggregated API server signing keys** similarly, updating the relevant ConfigMaps.

### API Server Certificate with SANs

Ensure the API server certificate includes the front-proxy SAN:
```bash
# When generating API server cert
openssl req -new -key apiserver.key -out apiserver.csr \
  -subj "/CN=kubernetes"

# Add SANs
openssl x509 -req -in apiserver.csr -CA ca.crt -CAkey ca.key \
  -out apiserver.crt -days 365 \
  -extfile <(printf "subjectAltName=DNS:kubernetes,DNS:kubernetes.default,DNS:kubernetes.default.svc,DNS:kubernetes.default.svc.cluster,DNS:kubernetes.default.svc.cluster.local,IP:10.96.0.1")
```

---

## Emergency Renewal Procedures

### Trigger Emergency Rotation

When a certificate is compromised or expiring outside the normal rotation window:

1. **Immediate actions**
   - Identify all affected components and their certificates
   - Generate new certificates with short validity (24-48 hours for emergency)
   - Document the reason for emergency rotation

2. **Accelerated distribution**
   - Use configuration management tools (Ansible, Terraform) for mass distribution
   - Validate each component starts with new certificates before decommissioning old ones
   - Monitor for authentication failures during transition

3. **Post-rotation verification**
   ```bash
   # Verify all plane connectivity
   kubectl cluster-info
   etcdctl endpoint health --endpoints=https://localhost:2379

   # Check kubelet status
   kubectl get nodes

   # Verify front-proxy access
   kubectl get nodes --request-header-urlPrefix=
   ```

4. **Update monitoring and alerting**
   - Update certificate expiration metrics
   - Set short-term alerts for newly-rotated certificates
   - Document the rotation in the change log

### Revocation Workflow

If a certificate is compromised:

1. **Revoke the certificate** using your internal PKI
2. **Update CRL distribution points** if using CRL-based revocation
3. **Accelerate rotation** using the emergency procedure above
4. **Investigate the compromise** and fix the root cause before returning to normal rotation

---

## Renewal Schedule and Monitoring

| Certificate Type | Default Validity | Renewal Trigger | Monitoring Metric |
|-----------------|-----------------|-----------------|-------------------|
| **API Server** | 1 year | 30 days before expiry | `kube_ap_server_certificate_expiry_seconds` |
| **Kubelet** | 1 year | 30 days before expiry | `kubelet_certificate_expiry_seconds` |
| **etcd peer** | 1 year | 30 days before expiry | `etcd_peer_certificate_expiry_seconds` |
| **etcd client** | 1 year | 30 days before expiry | `etcd_client_certificate_expiry_seconds` |
| **Front-proxy** | 1 year | 30 days before expiry | `front_proxy_certificate_expiry_seconds` |
| **SA token key** | 1 year | 30 days before expiry | `service_account_token_key_age` |

### Automated Monitoring Example

```yaml
# Prometheus alert for certificate expiry
alert: CertificateExpiryWarning
expr: (kubelet_certificate_expiry_seconds - time()) < 2592000
for: 10m
labels:
  severity: warning
annotations:
  summary: "Kubelet certificate expiring within 30 days"
  description: "Kubelet certificate will expire in less than 30 days. Renewal required."
```

---

## References

- [Kubernetes TLS Bootstrapping](https://kubernetes.io/docs/reference/setup-tools/kubectl/kubectl-bootstrap/)
- [Managing TLS Certificates in Kubernetes](https://kubernetes.io/docs/concepts/security/tls/)
- [kubeadm Certificate Management](https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-certs/)