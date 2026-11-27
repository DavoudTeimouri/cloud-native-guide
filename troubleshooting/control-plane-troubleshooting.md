# Kubernetes Control Plane Troubleshooting

This document covers troubleshooting for all Kubernetes control plane components: API server, etcd, controller-manager, and scheduler. Each section includes symptoms, likely causes, diagnostic commands, expected healthy state, remediation steps, risks, and verification checks.

## API Server

### Symptoms

- `kubectl` commands fail with "connection refused" or "timeout"
- `kubectl get --raw='/readyz?verbose'` returns failures
- API server pod crash-looping
- Authentication/authorization failures
- Admission webhooks rejecting all requests

### Likely causes

- API server static pod not created by kubelet
- etcd unreachable from API server
- Certificate expired or wrong
- Admission webhook configuration pointing to wrong service
- etcd quorum lost

### Diagnostic commands

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

### Expected healthy state

- API server pods: Running, 0 restarts
- `kubectl get --raw='/readyz?verbose'` returns all checks ok
- `kubectl auth whoami` returns authenticated user
- etcd endpoint health: all endpoints healthy

### Remediation

- Restart API server: delete static pod manifest, kubelet recreates
- Fix etcd connectivity (see etcd troubleshooting)
- Rotate expired API server certificates
- Fix admission webhook service references
- Restore etcd quorum (see etcd troubleshooting)

### Risks

- Deleting API server pod makes cluster temporarily unreachable
- Fixing admission webhooks can block all cluster operations if done wrong
- Certificate rotation can break existing client connections

### Verification

```bash
kubectl get --raw='/readyz?verbose'
kubectl auth whoami
kubectl get nodes
kubectl get pods -A | head -5
```

## etcd

Please refer to [etcd.md](etcd.md) for detailed etcd troubleshooting including member health, quorum loss, disk space, clock skew, and snapshot restoration.

## Controller-Manager

### Symptoms

- Cloud controller manager specific operations fail
- Node controller stops updating node status
- Route/load balancer creation fails
- Statefulset operations stall

### Likely causes

- Controller-manager static pod not running
- kubeconfig misconfiguration
- API server unreachable
- Certificate expiry
- Resource starvation (CPU/memory)

### Diagnostic commands

```bash
# Check controller-manager pod status
kubectl -n kube-system get pods -l component=kube-controller-manager
kubectl -n kube-system logs -l component=kube-controller-manager

# Check for errors related to node controller
kubectl get nodes -o wide | grep -i "notready\|unschedulable"

# Verify API server access
kubectl get --raw='/healthz'

# Check certificate validity
ls -l /etc/kubernetes/pki/controller-manager/
```

### Expected healthy state

- Controller-manager pods: Running, 0 restarts
- Node controller: Nodes transitioning through expected states
- Cloud resource creation: Operational within SLA
- API server health: All checks passing

### Remediation

- Restart controller-manager: delete static pod manifest, kubelet recreates
- Fix kubeconfig if misconfigured
- Rotate expired certificates
- Increase resource limits if starved
- Debug specific cloud provider API rate limits

### Risks

- Restarting controller-manager causes temporary loss of node management operations
- Certificate rotation can break controller-to-API-server authentication
- Increasing resource limits may not help if the issue is a memory leak

### Verification

```bash
kubectl get nodes -o wide
kubectl get --raw='/healthz'
kubectl get pods -A -l component=kube-controller-manager
```

## Scheduler

### Symptoms

- Pods not scheduled onto available nodes
- Scheduler pod crash-looping
- Node affinity/anti-affinity not working
- Pods stuck in Pending state

### Likely causes

- Scheduler static pod not running
- API server unreachable from scheduler
- Predicate/ priority plugins failing
- Resource distribution imbalance
- Node label/node selector mismatch

### Diagnostic commands

```bash
# Check scheduler pod status
kubectl -n kube-system get pods -l component=kube-scheduler
kubectl -n kube-system logs -l component=kube-scheduler

# Check pending pods and reasons
kubectl get pods -A --field-selector=status.phase=Pending --sort-by=.metadata.creationTimestamp

# Describe a pending pod for detailed reasons
kubectl describe pod <pending-pod> -n <namespace>

# Verify API server access
kubectl get --raw='/healthz'

# Check scheduler policy config
ls -l /etc/kubernetes/scheduler/
```

### Expected healthy state

- Scheduler pods: Running, 0 restarts
- Pending pods: 0 (or expected number from topology spread)
- All nodes receive pods according to scheduling logic
- API server health: All checks passing

### Remediation

- Restart scheduler: delete static pod manifest, kubelet recreates
- Fix kubeconfig if misconfigured
- Debug and disable problematic predicates/priorities
- Rebalance resource distribution across nodes
- Verify node labels and pod affinity/anti-affinity rules

### Risks

- Restarting scheduler can cause a brief period of no new pod scheduling
- Disabling predicates may allow pods to be scheduled on unsuitable nodes
- Resource rebalancing may take time to propagate

### Verification

```bash
kubectl get pods -A --field-selector=status.phase=Pending | wc -l
kubectl get --raw='/healthz'
kubectl get pods -A -l component=kube-scheduler
```

## Diagnostic Commands Summary

### Cluster health checks

```bash
# Overall cluster readiness
kubectl get --raw='/readyz?verbose'

# API server health
kubectl get --raw='/healthz'

# etcd health (from a control-plane node)
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster

# Node status
kubectl get nodes -o wide

# Control-plane component status
kubectl -n kube-system get pods -l component=kube-apiserver,kube-controller-manager,kube-scheduler
```

### Logs collection

```bash
# All control-plane component logs
for component in kube-apiserver kube-controller-manager kube-scheduler; do
  kubectl -n kube-system logs -l component=$component
done
```

### etcd specific

```bash
# Member list
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  member list -w table

# Endpoint health
ETCDCTL_API=3 etcdctl --endpoints=... endpoint health --cluster

# Alarm list
ETCDCTL_API=3 etcdctl --endpoints=... alarm list
```

### Certificate inspection

```bash
# API server certificate
kubectl get -n kube-system secret <apiserver-cert-secret> -o yaml

# etcd certificates
openssl x509 -enddate -noout -in /etc/kubernetes/pki/etcd/*.crt

# Controller manager certificates
ls -l /etc/kubernetes/pki/controller-manager/
```
