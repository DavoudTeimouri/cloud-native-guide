# Kubespray Certificate Lifecycle

## A. Purpose and scope

Document the certificate lifecycle for Kubespray-deployed Kubernetes clusters: certificate types, rotation procedures, OIDC CA provisioning, and expiration handling.

Cross-references `kubespray/kubespray-deployment.md` §L (OIDC CA certificate provisioning), `secrets-management/pki/root-ca-rotation.md`, `secrets-management/pki/index.md`, `kubernetes/control-plane/index.md` §Certificate lifecycle.

## B. Certificate types

| Certificate | Issued by | Used by | Location | Rotation |
|-------------|-----------|---------|----------|----------|
| kube-apiserver | Kubespray PKI | kube-apiserver | /etc/kubernetes/pki/apiserver.crt | Kubespray cluster.yml |
| kubelet | Kubespray PKI | kubelet | /etc/kubernetes/pki/kubelet.crt | Kubespray cluster.yml |
| front-proxy-client | Kubespray PKI | front-proxy | /etc/kubernetes/pki/front-proxy-client.crt | Kubespray cluster.yml |
| etcd | Kubespray PKI | etcd | /etc/kubernetes/pki/etcd/ | Kubespray cluster.yml |
| OIDC CA | Keycloak TLS issuer | kube-apiserver | /etc/kubernetes/pki/oidc-ca.crt | Manual (owner-operated) |
| service account | Kubespray PKI | controller-manager | /etc/kubernetes/pki/sa.key, sa.crt | Kubespray cluster.yml |

## C. Kubespray-managed certificates

Certificates managed by Kubespray are rotated via `cluster.yml`:

```bash
# Rotate all certificates managed by Kubespray
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b

# Rotate certificates on specific nodes only
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit <node>
```

Kubespray regenerates certificates on each run if they're expired or missing. The rotation is automatic — no manual certificate generation is required for Kubespray-managed certs.

### Rotation procedure

1. Update `cluster.yml` if certificate parameters changed
2. Run `cluster.yml -b` on all control-plane nodes
3. Verify: `kubectl get nodes` shows all Ready
4. Verify: `kubectl get --raw='/readyz?verbose'` returns all ok

## D. OIDC CA certificate (manual)

The OIDC CA certificate is **not** managed by Kubespray. It is the CA that signed Keycloak's TLS certificate.

### Location

`/etc/kubernetes/pki/oidc-ca.crt` on every control-plane node.

### Configuration

```yaml
# group_vars/k8s_cluster/k8s-cluster.yml
kube_oidc_ca_file: "/etc/kubernetes/pki/oidc-ca.crt"
```

### Rotation procedure (one control-plane node at a time)

1. Replace `oidc-ca.crt` with the new CA cert on one control-plane node
2. Restart the kube-apiserver static pod (kubelet recreates it when the manifest changes)
3. Verify the node is healthy: `kubectl get nodes` and `kubectl get --raw='/readyz?verbose'`
4. Verify OIDC login still works: `kubectl auth whoami` with a federated user
5. Repeat for the next control-plane node, one at a time, preserving quorum

**Do not restart all control-plane nodes simultaneously** — this removes API server quorum and makes the cluster unreachable.

### Missing certificate behavior

If `kube_oidc_ca_file` points to a missing file, kube-apiserver fails to start and OIDC authentication is unavailable for the entire cluster. Validate before deploying:

```bash
ansible -i inventory/<cluster>/hosts.ini control-plane -m stat -a "path=/etc/kubernetes/pki/oidc-ca.crt"
```

### Source certificate

The certificate is the public CA cert (PEM-encoded) that signed `keycloak.internal`'s TLS certificate. It contains no private key and is safe to store in the repository.

Verify it is a CA certificate before deploying:

```bash
openssl verify -CAfile oidc-ca.crt oidc-ca.crt
openssl x509 -in oidc-ca.crt -noout -text | grep -A1 'Basic Constraints'
```

## D. Certificate expiration

### Detection

Kubespray does not proactively alert on certificate expiration. Monitor:

```bash
# Check kube-apiserver certificate expiry
kubectl -n kube-system get secret <apiserver-cert-secret> -o yaml | \
  grep 'tls.crt:' | head -1 | \
  awk '{print $2}' | base64 -d | openssl x509 -noout -enddate

# Check all certificates
find /etc/kubernetes/pki -name '*.crt' -exec sh -c 'echo "{}:"; openssl x509 -in "{}" -noout -enddate' \;
```

### Remediation

- Kubespray-managed certs: Run `cluster.yml -b` to rotate
- OIDC CA cert: Follow the manual rotation procedure in Section D
- etcd certs: Rotated as part of etcd upgrade (lifecycle/upgrades/kubernetes.md)

## E. Cross-references

- `kubespray/kubespray-deployment.md` §L — OIDC CA certificate provisioning
- `kubespray/kubespray-deployment.md` §J — Upgrades (certificate renewal workflow)
- `secrets-management/pki/root-ca-rotation.md` — PKI root CA rotation
- `secrets-management/pki/index.md` — PKI overview
- `kubernetes/control-plane/index.md` §Certificate lifecycle — Control plane certificate context
- `compatibility/version-matrix.md` — Version pins
