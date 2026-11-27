# Troubleshooting Runbooks and Operational Checklists

## Incident Response

### Universal First-Response Sequence
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

### Severity Classification (SLO-driven)
| Severity | Error Budget Impact | Escalation Trigger |
|----------|--------------------|-------------------|
| P0 Critical | >50% budget consumed in 1h | Auto-escalate to on-call lead |
| P1 High | >50% budget consumed in 6h | Escalate after 2h if no progress |
| P2 Medium | 20-50% budget consumed | Review at next standup |
| P3 Low | <20% budget consumed | Log and track |

### Blameless Post-Incident Review Template
- **What happened**: Timeline of events
- **Impact**: Users affected, error budget consumed
- **Root cause**: Systemic failure, not human error
- **Fix**: Change that prevents recurrence
- **Action items**: Owners, deadlines, verification
- **Prevention**: Process or automation improvement

## Common Failure Modes by Domain

### DNS Resolution Failures
- **Symptoms**: `kubectl` hangs, `dig` returns no answer, `curl` fails with "no such host"
- **Likely causes**: CoreDNS not running, wrong cluster DNS, `/etc/resolv.conf` misconfig, network policy blocking port 53
- **See**: `troubleshooting/dns.md` for full runbook

### TLS/Certificate Expiry
- **Symptoms**: `curl` returns cert errors, browsers show "certificate expired", service returns 502/503
- **Likely causes**: Certificate expiry, mismatched hostname, chain incomplete, clock skew
- **See**: `troubleshooting/tls.md` for full runbook

### etcd Performance Degradation
- **Symptoms**: `kubectl` slow, API responses delayed, backup times out
- **Likely causes**: Disk pressure, WAL blooming, too many etcd members, snapshot failures
- **See**: `troubleshooting/etcd.md` for full runbook

### Kubernetes API Server Issues
- **Symptoms**: `kubectl get` timeout, pods stuck in Pending, health checks failing
- **Likely causes**: apiserver resource pressure, certificate expiry, RBAC misconfig, network policies
- **See**: `troubleshooting/apiserver.md` for full runbook

### Node Resource Pressure
- **Symptoms**: Pods scheduled but not running, OOMKilled, disk pressure errors
- **Likely causes**: Memory leak, log rotation failure, disk full, node auto-scaler not triggering
- **See**: `troubleshooting/kubespray.md` for full runbook

### Service Mesh Routing Failures
- **Symptoms**: Traffic not routed, mTLS handshake failures, retries not respecting circuit breaker
- **Likely causes**: Sidecar proxy misconfig, cert expiry in mesh, policy mismatch, pilot-agent disconnect
- **See**: `troubleshooting/service-mesh.md` for full runbook

### GPU Driver and Device Allocation Failures
- **Symptoms**: Pods pending with " insufficient nodes", devices not visible, out-of-memory on GPU
- **Likely causes**: Driver version mismatch, device plugin not running, CUDA runtime mismatch, MIG config errors
- **See**: `troubleshooting/gpu.md` for full runbook

### LLM Inference and GPU Memory Exhaustion
- **Symptoms**: Generation stalls, OOM errors, model load fails, token throughput drops
- **Likely causes**: GPU memory fragmentation, model too large for device, concurrency too high, thermal throttling
- **See**: `troubleshooting/inference.md` for full runbook

### Backup and Recovery Failures
- **Symptoms**: Backup job fails, restore takes longer than RTO, data loss detected, snapshot stuck
- **Likely causes**: Storage capacity, network timeout, encryption key rotation, incompatible client version
- **See**: `troubleshooting/backup-restore.md` for full runbook

## Diagnostic Procedures by Layer

### Layer 1: Physical/Infrastructure
| Check | Command | Healthy State |
|-------|---------|---------------|
| Node reachability | `ping -c 3 <ip>` | 0% loss |
| Port reachability | `nc -zv <ip> <port>` | Connection succeeded |
| Disk health | `df -h` | <80% usage |
| Node status | `kubectl get nodes` | Ready status |
| BIOS/time sync | `timedatectl` | NTP synchronized, offset < 100ms |

### Layer 2: Network
| Check | Command | Healthy State |
|-------|---------|---------------|
| Name resolution | `dig +short <name>` | Returns expected IP |
| Reverse DNS | `dig -x <ip>` | Returns expected hostname |
| TLS handshake | `openssl s_client -connect <ip>:443 -servername <name>` | Verify return code 0, correct chain |
| Service port | `nc -z <ip> <port>` | Connection succeeded |
| Mesh traffic | `istioctl proxy-config endpoints <pod>` | Endpoints listed |

### Layer 3: Service/Kubernetes
| Check | Command | Healthy State |
|-------|---------|---------------|
| Pod status | `kubectl get pods -o wide` | Running, 0 restarts |
| Readiness | `kubectl get --raw='/readyz?verbose'` | All checks ok |
| Events | `kubectl describe pod <pod>` | No recent warnings |
| Logs (previous) | `kubectl logs <pod> --previous` | Previous output (crash loops) |
| Service IP | `kubectl get svc <svc> -o wide` | ClusterIP assigned |
| Network policy | `kubectl get networkpolicy` | Expected rules present |

### Layer 4: Application
| Check | Command | Healthy State |
|-------|---------|---------------|
| Readiness probe | `curl -s <pod-ip>:<port>/ready` | 200 OK |
| Liveness probe | `curl -s <pod-ip>:<port>/live` | 200 OK |
| Metrics endpoint | `curl -s <pod-ip>:<port>/metrics` | Returns prometheus format |
| Health summary | `kubectl get --raw='/api/v1/namespaces/<ns>/pods/<pod>/proxy/healthz'` | 200 OK |

## Operational Checklists

### Pre-Deployment Checklist
- [ ] Error budget sufficient for risk level (see SLO framework)
- [ ] Canary deployment at 5% for 15 min, then 25% for 30 min
- [ ] Rollback plan documented and tested
- [ ] Feature flags configured for new pathways
- [ ] Monitoring alerts verified firing correctly
- [ ] Log aggregation path verified (new service shipper configured)
- [ ] Traces configured with correct service name
- [ ] Resource limits reviewed and applied
- [ ] Security context reviewed (privilege escalation check)
- [ ] Secrets mounted read-only where possible

### Post-Deployment Verification
- [ ] SLO within target after warmup period (5m for critical, 30m for high)
- [ ] Error budget consumption rate stable or decreasing
- [ ] Key metrics returned to baseline
- [ ] No new alert firings in last 10m
- [ ] Canary traffic at 100% with healthy metrics
- [ ] Rollback window closed if all checks pass

### Daily Cluster Health Checklist
- [ ] All nodes Ready: `kubectl get nodes --no-headers | grep -c Ready` equals total nodes
- [ ] No NotReady nodes: `kubectl get nodes` output shows 0/ Ready
- [ ] CoreDNS healthy: `kubectl -n kube-system get pods -l k8s-app=kube-dns` all Running
- [ ] etcd metrics within bounds: `kubectl exec -n kube-system <etcd-pod> -- etcdctl endpoint status -w table`
- [ ] API server latency < 50ms p99: `kubectl get --raw='/livez'`
- [ ] No pending pods with default QoS: `kubectl get pods --all-namespaces | grep Pending | grep -v "qos=best-effort"`
- [ ] Storage available: `kubectl get pvc --all-namespaces` all Bound
- [ ] Security scans passed: verify new images against registry scan

### Weekly Reliability Review Checklist
- [ ] Error budget burn rate analyzed over 30d window
- [ ] SLO targets reviewed for relevance (user experience alignment)
- [ ] Automation opportunities identified (toil > 4h/week)
- [ ] Chaos experiment results reviewed and incorporated
- [ ] Dependency versions checked for security advisories
- [ ] Capacity planning data reviewed (CPU/mem trends 30/60/90d)
- [ ] Runbook currency verified (all links valid, last tested < 30d ago)
- [ ] Post-incident action items closed or scheduled

### Monthly Infrastructure Review Checklist
- [ ] Node autoscaler policies reviewed and adjusted
- [ ] Storage capacity forecast and provisioning
- [ ] Certificate expiry dates checked (30/60/90d windows)
- [ ] Backup and restore time tested in staging
- [ ] Disaster recovery runbook reviewed and updated
- [ ] Cost optimization opportunities documented
- [ ] Security policy updates applied
- [ ] SLO targets adjusted based on user pattern changes

## Risks and Mitigation

| Risk | Mitigation |
|------|-----------|
| Runbook out of date | Schedule monthly currency review; auto-link check with `scripts/check_links.py` |
| Remediation makes things worse | Collect evidence before any destructive action; one change at a time |
| Escalation delay | Pre-defined escalation paths with on-call rotas; SLO-driven severity |
| Alert fatigue | Quarterly alert review; silence thresholds based on error budget |
| Common failure mode not documented | Post-incident: always add to runbook within 48h of resolution |

## Link Validation

Run the link checker to verify all internal references:

```bash
python3 scripts/check_links.py
```

Expected: 0 broken links. Any output indicates missing files or dead anchors that should be fixed.