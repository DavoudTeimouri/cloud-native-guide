# Certificate Rotation

## A. Purpose and scope

Document certificate rotation for Kubespray-deployed Kubernetes clusters: kube-apiserver, kubelet, etcd, front-proxy, and service account certificates.

Cross-references `kubespray/kubespray-deployment.md` §Certificate renewal, `kubespray/certificate-lifecycle.md`, `kubernetes/control-plane/index.md` §Certificate expiry.

## B. Certificate types managed by Kubespray

| Certificate | Managed by | Location | Rotation method |
|-------------|------------|----------|-----------------|
| kube-apiserver | Kubespray PKI | /etc/kubernetes/pki/apiserver.crt | cluster.yml |
| kubelet | Kubespray PKI | /etc/kubernetes/pki/kubelet.crt | cluster.yml |
| front-proxy-client | Kubespray PKI | /etc/kubernetes/pki/front-proxy-client.crt | cluster.yml |
| etcd server/client | Kubespray PKI | /etc/kubernetes/pki/etcd/ | cluster.yml |
| service account | Kubespray PKI | /etc/kubernetes/pki/sa.key, sa.crt | cluster.yml |
| OIDC CA | Manual (owner-operated) | /etc/kubernetes/pki/oidc-ca.crt | Manual replacement |

## C. Kubespray certificate renewal

Kubespray manages Kubernetes internal PKI. Certificates are renewed by running `cluster.yml`:

```bash
# Renew all certificates managed by Kubespray
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b

# Renew certificates on specific nodes only
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit <node>
```

Kubespray regenerates certificates on each run if they are expired or approaching expiry. The renewal is automatic — no manual certificate generation is required.

### Rotation procedure

1. Update `cluster.yml` if certificate parameters changed
2. Run `cluster.yml -b` on all control-plane nodes
3. Run `cluster.yml -b` on all worker nodes
4. Verify: `kubectl get nodes` shows all Ready
5. Verify: `kubectl get --raw='/readyz?verbose'` returns all ok

## D. etcd certificate rotation

etcd certificates are managed by Kubespray as part of the control plane. Rotation follows the same `cluster.yml` procedure:

```bash
# Rotate etcd certificates on one control-plane node at a time
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-1

# Verify etcd health after rotation
kubectl -n kube-system exec etcd-k8s-cp-1 -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster
```

**One control-plane node at a time** — never rotate etcd certificates on all control-plane nodes simultaneously.

## E. Certificate expiration detection

Kubespray does not proactively alert on certificate expiration. Monitor:

```bash
# Check kube-apiserver certificate expiry
kubectl -n kube-system get secret <apiserver-cert-secret> -o yaml | \
  grep 'tls.crt:' | head -1 | awk '{print $2}' | base64 -d | \
  openssl x509 -noout -enddate

# Check all certificates on a node
find /etc/kubernetes/pki -name '*.crt' -exec sh -c 'echo "{}:"; openssl x509 -in "{}" -noout -enddate' \;

# Check etcd certificate expiry
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  certificate list
```

## F. OIDC CA certificate (manual rotation)

The OIDC CA certificate is not managed by Kubespray. Follow the manual rotation procedure in `kubespray/certificate-lifecycle.md` §D:

1. Replace `oidc-ca.crt` on one control-plane node
2. Restart kube-apiserver static pod
3. Verify node health
4. Repeat for remaining control-plane nodes, one at a time

## G. Cross-references

- `kubespray/kubespray-deployment.md` §J — Upgrades (certificate renewal workflow)
- `kubespray/kubespray-deployment.md` §L — OIDC CA certificate provisioning
- `kubespray/certificate-lifecycle.md` — Certificate lifecycle overview
- `kubernetes/control-plane/index.md` §Certificate expiry — Control plane certificate context
- `compatibility/version-matrix.md` — Version pins
