# Kubernetes API Server Troubleshooting

## Symptoms

- `kubectl` commands fail with "connection refused" or "timeout"
- `kubectl get --raw='/readyz?verbose'` returns failures
- API server pod crash-looping
- Authentication/authorization failures
- Admission webhooks rejecting all requests

## Likely causes

- API server static pod not created by kubelet
- etcd unreachable from API server
- Certificate expired or wrong
- Admission webhook configuration pointing to wrong service
- etcd quorum lost

## Diagnostic commands

```bash
# Is API server running?
kubectl -n kube-system get pods -l component=kube-apiserver
kubectl -n kube-system logs -l component=kube-apiserver

# Is etcd reachable?
kubectl get --raw='/readyz?verbose'
kubectl get --raw='/healthz'

# Check API server certificate
kubectl get -n kube-system secret <apiserver-cert-secret> -o yaml

# Check admission webhooks
kubectl get validatingwebhookconfiguration
kubectl get mutatingwebhookconfiguration

# Test authentication
kubectl auth whoami
kubectl auth can-i create pods
```

## Expected healthy state

- API server pods: Running, 0 restarts
- `kubectl get --raw='/readyz?verbose'` returns all checks ok
- `kubectl auth whoami` returns authenticated user
- etcd endpoint health: all endpoints healthy

## Remediation

- Restart API server: delete static pod manifest, kubelet recreates
- Fix etcd connectivity (see etcd troubleshooting)
- Rotate expired API server certificates
- Fix admission webhook service references
- Restore etcd quorum (see etcd troubleshooting)

## Risks

- Deleting API server pod makes cluster temporarily unreachable
- Fixing admission webhooks can block all cluster operations if done wrong
- Certificate rotation can break existing client connections

## Verification

```bash
kubectl get --raw='/readyz?verbose'
kubectl auth whoami
kubectl get nodes
kubectl get pods -A | head -5```
