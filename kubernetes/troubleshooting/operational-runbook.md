# Kubernetes Operational Troubleshooting Runbook

## Overview

This runbook documents Kubernetes operational troubleshooting procedures for control plane diagnostics, node issues, etcd quorum loss, API server failures, scheduler issues, and a diagnostic command reference. Follow the universal first-response sequence before proceeding to component-specific procedures.

---

## Universal First-Response Sequence

Run this before any component-specific procedure. It eliminates most misdiagnoses.

```bash
# 1. Is the problem in my session or in the system?
date; timedatectl  # skew?

# 2. Is the target reachable at all?
ping -c 3 <target-ip>        # layer 3
nc -zv <target> <port>       # layer 4
curl -vk https://<target>    # layer 5/7

# 3. Is the service actually running?
systemctl status <unit> --no-pager
kubectl get pods -A | grep -v Running
kubectl get events -A --sort-by=.lastTimestamp | tail -30

# 4. Is it the cluster, or the workload?
kubectl get --raw='/readyz?verbose'
kubectl describe node <node>
```

---

## Universal Rules

1. **Root cause before remediation.** Restarting a component hides the symptom and loses the evidence. Collect the evidence first.
2. **One change at a time.** Each change is a new hypothesis.
3. **Check the version matrix.** Most "impossible" failures are a version incompatibility.
4. **Check the network matrix.** Most "the service is down" reports are a firewall rule.
5. **Preserve the evidence.** Copy logs before restarting anything.
6. **Never run a destructive command without explicit authorization.**
7. **Record the resolution** in the relevant runbook, with the command that actually fixed it.

---

## Diagnostic Commands by Layer

| Layer | Command | Healthy state |
|---|---|---|
| Name resolution | `dig +short <name>` | The expected IP |
| Reverse | `dig -x <ip>` | The expected hostname |
| Time | `chronyc tracking` | Leap status normal, offset < 100 ms |
| Reachability | `ping -c3 <ip>` | 0% loss |
| Port | `nc -zv <ip> <port>` | Connection succeeded |
| TLS | `openssl s_client -connect <ip>:443 -servername <name>` | Verify return code 0, correct chain |
| Service | `systemctl is-active <unit>` | active |
| Container | `kubectl get pod -o wide` | Running, 0 restarts |
| Events | `kubectl describe pod` | No recent warnings |
| Logs | `kubectl logs <pod> --previous` | The previous container's output (for crash loops) |
| Cluster | `kubectl get --raw='/readyz?verbose'` | All checks ok |
| Storage | `kubectl get pvc` | Bound |
| Admission | `kubectl get validatingwebhookconfigurations` | Expected configs present |

---

## When to Escalate

Escalate to a second engineer when:

- The evidence contradicts the runbook (the runbook is then wrong and must be corrected).
- A destructive action is required and the authorization is ambiguous.
- The failure spans two components and the boundary is unclear.
- The same symptom returns after a documented remediation.

---

## Control Plane Diagnostics

### Symptoms

- `kubectl` commands fail with "connection refused" or "timeout"
- `kubectl get --raw='/readyz?verbose'` returns failures
- Control plane pods crash-looping
- etcd quorum loss detected

### Likely causes

- API server static pod not created by kubelet
- etcd unreachable from control plane
- Certificate expired or wrong
- Scheduler not scheduling
- Controller-manager not running
- Cloud provider integration issues

### Diagnostic commands

```bash
# Check control plane pod status
kubectl -n kube-system get pods -l component=kube-apiserver
kubectl -n kube-system get pods -l component=kube-scheduler
kubectl -n kube-system get pods -l component=controller-manager

# Check API server reachability
kubectl get --raw='/readyz?verbose'
kubectl get --raw='/healthz'

# Check etcd member health
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster

# Check scheduler status
kubectl -n kube-system logs -l component=kube-scheduler | tail -20

# Check controller-manager status
kubectl -n kube-system logs -l component=controller-manager | tail -20
```

### Expected healthy state

- All control plane pods: Running, 0 restarts
- `kubectl get --raw='/readyz?verbose'` returns all checks ok
- etcd endpoint health: all endpoints healthy
- Scheduler: accepting and scheduling pods
- Controller-manager: all controllers healthy

### Remediation

- Restart control plane components: delete static pod manifest, kubelet recreates
- Fix etcd connectivity (see etcd quorum loss section below)
- Rotate expired control plane certificates
- Verify cloud provider credentials and connectivity
- Check kubelet logs for control plane registration issues

### Risks

- Deleting API server pod makes cluster temporarily unreachable
- Restarting control plane components can cause brief availability outage
- Certificate rotation can break existing client connections

### Verification

```bash
kubectl get --raw='/readyz?verbose'
kubectl get nodes
kubectl get pods -A | head -10
```

---

## Node Issues

### Symptoms

- Node not ready or ReportingStatus="False"
- Kubelet not communicating with API server
- High resource usage (CPU, memory, disk)
- Container runtime failures
- Network plugin errors

### Likely causes

- kubelet service stopped or failing
- Node network configuration issues
- Container runtime (Docker/containerd) not running
- Disk pressure or memory pressure
- CNI plugin misconfiguration

### Diagnostic commands

```bash
# Check node status
kubectl get nodes <node-name>

# Check kubelet service
systemctl status kubelet --no-pager
journalctl -u kubelet -f --no-pager | tail -30

# Check container runtime
systemctl status containerd --no-pager
crictl ps -a

# Check node conditions
kubectl describe node <node-name> | grep -A 10 Conditions

# Check kubelet logs
journalctl -u kubelet --no-pager | tail -50

# Check CNI plugin status
kubectl get pods -n kube-system -l k8s-app=kube-flannel
kubectl -n kube-system logs -l k8s-app=kube-flannel

# Check disk and memory
df -h /
free -h
```

### Expected healthy state

- Node status: Ready
- Kubelet service: active
- Container runtime: running
- All node conditions: True (MemoryPressure, DiskPressure, PIDPressure, Ready)
- CNI plugins: Running, 0 restarts

### Remediation

- Restart kubelet: `systemctl restart kubelet`
- Restart container runtime: `systemctl restart containerd`
- Address resource pressure: delete pods, expand disk
- Reapply CNI configuration if misconfigured
- Rejoin node to cluster if disconnected

### Risks

- Restarting kubelet can cause pod evictions on the node
- Rejoining a node can cause IP conflicts
- Expanding disk requires careful partitioning

### Verification

```bash
kubectl get nodes <node-name>
kubectl describe node <node-name> | grep -A 10 Conditions
```

---

## etcd Quorum Loss

### Symptoms

- API server errors: `etcd cluster is unhealthy`
- `kubectl` commands timeout or fail
- Unable to create/update/delete resources
- Cluster operates in read-only mode

### Likely causes

- Lost etcd members (reboot, network partition)
- etcd disk full
- etcd configuration drift
- Unexpected member removal

### Diagnostic commands

```bash
# Check etcd member health
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster

# Check etcd member list
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list

# Check etcd quorum
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  quorum status

# etcd endpoint status
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint status -w table

# Check etcd logs
journalctl -u etcd --no-pager | tail -30
```

### Expected healthy state

- All etcd members: healthy
- Quorum: achieved (majority of members responding)
- Member count: matches control-plane inventory
- Disk usage: below threshold (typically < 80%)

### Remediation

**Step 1:** Identify lost members
```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list
```

**Step 2:** Add replacement member (if available)
```bash
etcdctl member add <member-name> \
  --peer-urls=https://<member-ip>:2380 \
  --member-zone=<zone> \
  --member-site=<site> \
  --member-role=learner \
  --initial-advertise-peer-urls=https://<member-ip>:2380
```

**Step 3:** Remove lost member
```bash
etcdctl member remove <member-id>
```

**Step 4:** Re-run Kubespray to redeploy etcd without the lost member
```bash
# Update inventory to exclude removed member
# Re-run Kubespray to redeploy etcd
```

**Step 5:** Verify quorum after remediation
```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster
```

### Risks

- Deleting a member without replacement loses quorum permanently
- etcd data loss if not enough members remain
- Certificate issues if member IPs change

### Verification

```bash
kubectl get --raw='/readyz?verbose'
kubectl get nodes
kubectl get pods -A
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster
```

---

## API Server Failures

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
kubectl -n kube-system secret <apiserver-cert-secret> -o yaml

# Check admission webhooks
kubectl get validatingwebhookconfiguration
kubectl get mutatingwebhookconfiguration

# Test authentication
kubectl auth whoami
kubectl auth can-i create pods

# Check API server audit log
kubectl get --raw='/api/v1/namespaces/kube-system/configmaps/kube-apiserver-audit-settings' -o yaml
```

### Expected healthy state

- API server pods: Running, 0 restarts
- `kubectl get --raw='/readyz?verbose'` returns all checks ok
- `kubectl auth whoami` returns authenticated user
- etcd endpoint health: all endpoints healthy
- Admission webhooks: configured and responding

### Remediation

- Restart API server: delete static pod manifest, kubelet recreates
- Fix etcd connectivity (see etcd quorum loss section)
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

---

## Scheduler Issues

### Symptoms

- Pods not scheduled to nodes
- Scheduler pod crash-looping
- Pods stuck in Pending state
- Node affinity/anti-affinity not respected
- Taints not being handled correctly

### Likely causes

- Scheduler not running or unhealthy
- All nodes have taints that prevent pod scheduling
- Insufficient resources (CPU, memory) on nodes
- Node selectors don't match pod requirements
- Pod disruption budgets blocking scheduling
- Volume provisioning failures

### Diagnostic commands

```bash
# Check scheduler pod status
kubectl -n kube-system get pods -l component=kube-scheduler
kubectl -n kube-system logs -l component=kube-scheduler | tail -20

# Check pending pods and reasons
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl describe pod <pending-pod-name> -n <namespace> | grep -A 20 "Warning.*Scheduled\|Warning.*Taint"

# Check node conditions and resources
kubectl get nodes -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for node in data['items']:
    name = node['metadata']['name']
    conditions = [c['type'] + ': ' + c['status'] for c in node['status']['conditions']]
    addresses = [a['address'] for a in node['status']['addresses']]
    print(f'{name}: conditions={conditions} addresses={addresses}')
"

# Check taints
kubectl get nodes -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for node in data['items']:
    name = node['metadata']['name']
    taints = node['status'].get('taints', [])
    print(f'{name}: taints={taints}')
"

# Check resource limits
kubectl get nodes -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for node in data['items']:
    name = node['metadata']['name']
    cpu = node['status']['capacity'].get('cpu', 'N/A')
    memory = node['status']['capacity'].get('memory', 'N/A')
    print(f'{name}: cpu={cpu} memory={memory}')
"
```

### Expected healthy state

- Scheduler pod: Running, 0 restarts
- No pods stuck in Pending indefinitely
- Nodes have appropriate resources for scheduled pods
- Taints are intentionally applied and documented
- Pods schedule to appropriate nodes based on requirements

### Remediation

- Restart scheduler: delete scheduler static pod manifest, kubelet recreates
- Remove unintended taints from nodes: `kubectl taint nodes <node-name> <key>:<effect>-`
- Add more nodes or increase resource limits
- Fix pod resource requests/limits to match available resources
- Review and adjust pod disruption budgets
- Ensure volume plugins are functioning for persistent volumes

### Risks

- Removing taints can cause pods to schedule to inappropriate nodes
- Restarting scheduler can cause brief scheduling disruption
- Adding nodes requires network and storage integration

### Verification

```bash
kubectl get pods -A --field-selector=status.phase=Pending | head -5
kubectl get nodes -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for node in data['items']:
    name = node['metadata']['name']
    taints = node['status'].get('taints', [])
    print(f'{name}: taints={taints}')
"
kubectl get pods -A -o wide | grep -v Running | head -10
```

---

## Diagnostic Command Reference

### Core kubectl commands

| Purpose | Command | Example |
|---|---|---|
| Check all pods | `kubectl get pods -A` | `kubectl get pods -A` |
| Describe resource | `kubectl describe <resource> <name>` | `kubectl describe pod my-pod -n default` |
| Check events | `kubectl get events -A --sort-by=.lastTimestamp` | `kubectl get events -A --sort-by=.lastTimestamp` |
| Ready check | `kubectl get --raw='/readyz?verbose'` | `kubectl get --raw='/readyz?verbose'` |
| Health check | `kubectl get --raw='/healthz'` | `kubectl get --raw='/healthz'` |
| API server introspection | `kubectl get --raw='/apis/'` | `kubectl get --raw='/apis/'` |
| Node status | `kubectl get nodes` | `kubectl get nodes` |
| Node conditions | `kubectl describe node <name>` | `kubectl describe node master-1` |
| Logs (current) | `kubectl logs <pod>` | `kubectl logs my-pod` |
| Logs (previous) | `kubectl logs <pod> --previous` | `kubectl logs my-pod --previous` |
| Exec into container | `kubectl exec <pod> -c <container>` | `kubectl exec my-pod -c my-container -- sh` |
| Port forward | `kubectl port-forward <pod> <local>:<remote>` | `kubectl port-forward my-pod 8080:80` |

### etcd commands (via exec)

| Purpose | Command | Example |
|---|---|---|
| Member health | `etcdctl endpoint health --cluster` | `etcdctl endpoint health --cluster` |
| Member list | `etcdctl member list` | `etcdctl member list` |
| Quorum status | `etcdctl quorum status` | `etcdctl quorum status` |
| Snapshot save | `etcdctl snapshot save /path/to/snap.db` | `etcdctl snapshot save /tmp/snap-$(date +%F).db` |
| Snapshot status | `etcdctl snapshot status /path/to/snap.db` | `etcdctl snapshot status /tmp/snap-$(date +%F).db` |
| Defragmentation | `etcdctl defrag` | `etcdctl defrag --rev 12345` |
| Member add | `etcdctl member add <name> --peer-urls=...` | `etcdctl member add new-mem --peer-urls=https://10.0.0.1:2380` |
| Member remove | `etcdctl member remove <id>` | `etcdctl member remove df2e8a12` |

### System commands

| Purpose | Command | Example |
|---|---|---|
| Time sync check | `timedatectl` | `timedatectl` |
| Network reachability | `ping -c 3 <ip>` | `ping -c 3 10.0.0.1` |
| Port check | `nc -zv <ip> <port>` | `nc -zv 10.0.0.1 6443` |
| DNS resolution | `dig +short <name>` | `dig +short api.example.com` |
| TLS check | `openssl s_client -connect <ip>:443 -servername <name>` | `openssl s_client -connect 10.0.0.1:443 -servername api.example.com` |
| Kubelet status | `systemctl status kubelet --no-pager` | `systemctl status kubelet --no-pager` |
| Container runtime | `systemctl status containerd --no-pager` | `systemctl status containerd --no-pager` |
| Crictl list pods | `crictl ps -a` | `crictl ps -a` |

### Log locations

| Component | Log path |
|---|---|
| API server | `/var/log/pods/kube-system/kube-apiserver-*` |
| Scheduler | `/var/log/pods/kube-system/kube-scheduler-*` |
| Controller-manager | `/var/log/pods/kube-system/kube-controller-manager-*` |
| Kubelet | `/var/log/kubelet.log` or journalctl |
| etcd | `/var/log/etcd.log` or journalctl |
| Container runtime | `/var/log/containers/` or journalctl |

---

## Related Runbooks

- `kubernetes/control-plane/etcd-operations.md` — etcd backup, restore, snapshot management
- `kubernetes/control-plane/etcd-backup.md` — Snapshot and backup procedure
- `kubernetes/control-plane/etcd-restore.md` — Restore procedure
- `kubernetes/control-plane/certificate-management.md` — Certificate generation and rotation
- `troubleshooting/etcd.md` — etcd-specific troubleshooting
- `troubleshooting/apiserver.md` — API server troubleshooting
- `lifecycle/backup/backup-and-dr.md` — Backup policy, RPO/RTO, retention
- `architecture/03-failure-domains.md` — Control-plane node placement

---

*This runbook is maintained as part of the cloud-native-guide. Last updated: $(date +%Y-%m-%d). For questions or updates, open an issue or submit a pull request.*
