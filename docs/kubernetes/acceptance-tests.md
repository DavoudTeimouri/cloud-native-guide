# Cluster Acceptance Tests

This document defines the cluster acceptance tests for Kubernetes deployment validation.
Each test section corresponds to a critical cluster component that must be verified
before a deployment is considered production-ready.

## Control-plane Health

Ensure the control-plane components are healthy and responsive.

### API Server

- **SLI**: `curl -k https://<apiserver>:6443/healthz` returns `ok`
- **Command**: `curl -k https://<apiserver>:6443/healthz`
- **Reference**: `kubernetes/control-plane/index.md` § Validation

### Controller Manager

- **SLI**: `kubectl -n kube-system get pods -l tier=controller-manager`
- **Command**: `kubectl -n kube-system get pods -l tier=controller-manager --field-selector=status=Running`
- **Expected**: All controller-manager pods Running

### Scheduler

- **SLI**: `kubectl -n kube-system get pods -l tier=scheduler`
- **Command**: `kubectl -n kube-system get pods -l tier=scheduler --field-selector=status=Running`
- **Expected**: All scheduler pods Running

**Cross-references**: `kubernetes/control-plane/index.md`, `decisions/ADR-0002-*`

## etcd Quorum

Ensure the etcd cluster has healthy quorum and all members are reachable.

### etcd Member Health

- **SLI**: `etcdctl endpoint health --cluster`
- **Command**: `kubectl -n kube-system exec etcd-<node> -- etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key endpoint health --cluster`
- **Expected**: All members report `healthy`
- **Reference**: `kubernetes/control-plane/index.md` § Validation

### etcd Member List

- **SLI**: `etcdctl member list`
- **Command**: `kubectl -n kube-system exec etcd-<node> -- etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key member list`
- **Expected**: Member count matches control-plane node count
- **Reference**: `kubernetes/control-plane/index.md` § Validation

### etcd Snapshot

- **SLI**: `etcdctl snapshot status <latest>`
- **Command**: `kubectl -n kube-system exec etcd-<node> -- etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key snapshot status <latest>`
- **Expected**: Snapshot is valid and accessible
- **Reference**: `kubernetes/control-plane/index.md` § Backup

**Cross-references**: `kubernetes/control-plane/index.md`, `lifecycle/backup/backup-and-dr.md`

## Node Readiness

Ensure all nodes report Ready status and have correct resource state.

### Node Status

- **SLI**: `kubectl get nodes`
- **Command**: `kubectl get nodes --ignore-not-found`
- **Expected**: All nodes `Ready` status
- **Reference**: `kubernetes/node-lifecycle.md`

### Node Resource Availability

- **SLI**: `kubectl describe nodes <node-name> | grep -E 'Conditions|Memory|CPU'`
- **Command**: `for node in $(kubectl get nodes -o name); do kubectl describe $node | grep -E 'Conditions:|Allocated resources'; done`
- **Expected**: All nodes have `Condition=True` for Ready
- **Reference**: `kubernetes/node-lifecycle.md`

### Node Label Compliance

- **SLI**: `kubectl get nodes -l node-role.kubernetes.io/control-plane`
- **Command**: `kubectl get nodes -l node-role.kubernetes.io/control-plane --no-headers | wc -l`
- **Expected**: Control-plane nodes labeled correctly
- **Reference**: `kubernetes/control-plane/index.md` § Topology

**Cross-references**: `kubernetes/node-lifecycle.md`, `kubernetes/control-plane/index.md`

## Network Connectivity

Ensure pod networking, service resolution, and cross-node traffic flow.

### DNS Resolution

- **SLI**: `dig +short <svc>.<ns>.svc.cluster.local`
- **Command**: `kubectl run dns-test --image=busybox --restart=Never --rm -i --rm=forever --overrides='{"spec': {"namespace": "default"}}' --command -- dig +short kubernetes.default.svc.cluster.local`
- **Expected**: Correct IP resolves
- **Reference**: `kubernetes/networking/cilium.md` § Cilium CNI

### Service-to-Service Connectivity

- **SLI**: `kubectl run nettest --image=networktools --restart=Never --rm -i --rm=forever -- <command>`
- **Command**: `kubectl run nettest --image=busybox --restart=Never --rm=forever --rm=forever --overrides='{"spec": {"network": "cluster"}}' -- nslookup <svc>`
- **Expected**: Services resolve and connect
- **Reference**: `kubernetes/networking/cilium.md`

### Cross-Node Pod Traffic

- **SLI**: Pod A → pod B on different node
- **Command**: `kubectl run traffic-test --image=busybox --restart=Never --rm -i --rm=forever --rm=forever --overrides='{"spec": {"nodeSelector": {"kubernetes.io/hostname": "<node-b>"}}}' -- ping <pod-cid>`
- **Expected**: Cross-node pod traffic flows
- **Reference**: `kubernetes/networking/cilium.md`

### MTU Verification

- **SLI**: `ping -M do -s 1472 <peer>` from each node
- **Command**: `for node in $(kubectl get nodes -o name | cut -d'/' -f2); do ping -M do -s 1472 $node; done`
- **Expected**: No fragmentation, DF bit set
- **Reference**: `kubernetes/networking/cilium.md` § MTU verification

### NetworkPolicy Enforcement

- **SLI**: Deny-all policy + allowed exception
- **Command**: Apply deny-all NetworkPolicy, then test allowed/denied flows
- **Expected**: Denied flows fail, allowed flows succeed
- **Reference**: `kubernetes/networking/network-policy-examples.md`

**Cross-references**: `kubernetes/networking/cilium.md`, `kubernetes/networking/network-policy-examples.md`, `network-matrix/network-communication-matrix.md`

## Test Summary

| Test Area | Key Metric | Threshold |
|---|---|---|
| Control-plane Health | API server `healthz` | `ok` |
| etcd Quorum | Member health | All `healthy` |
| Node Readiness | Node `Ready` status | All `True` |
| Network Connectivity | DNS resolution | Correct IP |

---

**Note**: These acceptance tests must be executed against a running Kubernetes cluster.
Run the procedures documented in each section and record evidence in
`tests/acceptance/<test-id>/` per the [acceptance test framework](../tests/acceptance/README.md).