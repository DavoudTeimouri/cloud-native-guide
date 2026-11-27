# TEST-PẢHÈN VÀ BI-RIƯ

*Illustrative only. No actual failure injection is performed.*

## TEST-PẢHÈN VÀ BI-RIƯ-1. Scenarios

13 scenarios: Worker unavailable, Control-plane unavailable, LB failure, DNS failure, Ceph OSD degradation, Ceph MON quorum risk, PVC mount failure, CNI agent failure, Monitoring component failure, Vault/OpenBao unavailable, Keycloak unavailable, Argo CD unavailable.

Each scenario: Preconditions, simulated failure method, expected impact, detection mechanism, alerts, recovery procedure, data validation, success criteria, abort conditions.

Classification: Static/documentation-only, lab-safe, staging-only, production-sensitive requiring approval.

---

### 12.1 Worker Unavailable
- **Preconditions**: Ephemeral or staging cluster with at least 2 worker nodes; a test workload deployed on one node.
- **Failure Simulation Method**: Drain the node (`kubectl drain <node> --ignore-daemonsets --delete-emptynodes`) or simulate node loss via ephemeral cluster stop. No `kubectl delete` on production.
- **Expected Service Impact**: Pods rescheduled to remaining node(s). DaemonSets affected recover on other nodes. Brief pod disruption window (< 30s on healthy cluster).
- **Detection Mechanism**: `kubectl get pods` shows pod `Terminating` then `Running` on new node; events `Scheduled`, `Warning` (if resource quotas hit).
- **Expected Alerts**: None unless resource quotas exceeded or DaemonSet pod disruption budget blocks rescheduling.
- **Recovery Procedure**: Node returns; pods auto-recover. No manual intervention required if Drain was used with `--delete-emptynodes=false`.
- **Data Integrity Validation**: No data loss for ephemeral workloads; persistent volumes detach/reattach cleanly.
- **Success Criteria**: All pods running on new node within 60s; no crash loops; events confirm reschedule.
- **Abort Conditions**: Production cluster; node is a control-plane node; drain would violate PodDisruptionBudget with no available alternatives.
- **Classification**: lab-safe (ephemeral), staging-only (staging cluster).

### 12.2 Control-Plane Unavailable
- **Preconditions**: Ephemeral or staging cluster with etcd running; no production access.
- **Failure Simulation Method**: etcd member snapshot/stop in ephemeral cluster; or simulate API server downtime via firewall rules on isolated network.
- **Expected Service Impact**: API server becomes unreachable; `kubectl` commands timeout; workloads continue running if already running (no new scaling or updates).
- **Detection Mechanism**: `kubectl auth can-i` timeout; API server health endpoint returns 503 or connection refused.
- **Expected Alerts**: `APIServerDown` or equivalent alert if self-monitoring is active.
- **Recovery Procedure**: Restart etcd member; restore API server. etcd snapshot may be required if member lost.
- **Data Integrity Validation**: etcd WAL integrity checked via `etcdctl endpoint status`; no corrupt members.
- **Success Criteria**: API server returns 200 on health endpoint; `kubectl` commands complete; workloads unaffected.
- **Abort Conditions**: Production cluster without SRE approval; etcd data directory on shared storage at risk.
- **Classification**: lab-safe (ephemeral), staging-only (staging), production-sensitive approval-required.

### 12.3 LB Failure
- **Preconditions**: Staging cluster with a LoadBalancer service; optional external DNS entry (placeholder).
- **Failure Simulation Method**: Stop the LoadBalancer controller pod; delete the LB service; or simulate network partition on isolated network.
- **Expected Service Impact**: External traffic to LoadBalancer services drops; internal cluster traffic unaffected.
- **Detection Mechanism**: `curl` against LB external IP returns timeout or 503; `kubectl get svc` shows `<pending>` or `<none>`.
- **Expected Alerts**: `LoadBalancerFailure` if self-monitoring active; may fire on traffic timeouts.
- **Recovery Procedure**: Restart LB controller; recreate LB service; verify external IP re-assignment.
- **Data Integrity Validation**: No in-cluster data affected; only external connectivity.
- **Success Criteria**: LB external IP reachable; `curl` returns expected response; service ingress stable.
- **Abort Conditions**: Production cluster; LB production IP release without change-management approval.
- **Classification**: staging-only, production-sensitive approval-required.

### 12.4 DNS Failure
- **Preconditions**: Staging cluster with external DNS entries (placeholder records); `corededns` or external DNS controller running.
- **Failure Simulation Method**: Pause the DNS controller pod; remove placeholder DNS records; or use `/etc/hosts` override on test nodes to return NXDOMAIN.
- **Expected Service Impact**: Workloads relying on DNS for service discovery fail to resolve; internal cluster DNS (`kubernetes.dns`) unaffected.
- **Detection Mechanism**: `dig <service>.<ns>.svc.cluster.local` returns SERVFAIL or timeout; application logs show DNS resolution failure.
- **Expected Alerts**: `DNSServerFailure` if self-monitoring active.
- **Recovery Procedure**: Resume DNS controller; re-create placeholder records; flush DNS cache on test nodes.
- **Data Integrity Validation**: No data corruption; only resolution failure.
- **Success Criteria**: DNS resolution returns A/AAAA records within timeout; workloads using DNS recover automatically.
- **Abort Conditions**: Production cluster; DNS changes without change-management approval.
- **Classification**: staging-only, production-sensitive approval-required.

### 12.5 Registry Unavailable
- **Preconditions**: Staging cluster with image puller pods; local registry (placeholder) or mirror configured.
- **Failure Simulation Method**: Stop registry container; revoke registry credentials; simulate network timeout to registry endpoint.
- **Expected Service Impact**: New pod deployments fail with `ImagePullBackOff`; running workloads unaffected if images already present locally.
- **Detection Mechanism**: `kubectl describe pod` shows `ImagePullBackOff`; events `Failed to pull image`.
- **Expected Alerts**: `RegistryUnavailable` if self-monitoring active.
- **Recovery Procedure**: Restart registry; verify registry health endpoint; re-authenticate if credentials rotated.
- **Data Integrity Validation**: No container data affected; only new deployments blocked.
- **Success Criteria**: Pods schedule and start after registry recovery; image pull successful.
- **Abort Conditions**: Production registry on shared storage; production deployment pipeline blocked.
- **Classification**: staging-only, production-sensitive approval-required.

### 12.6 Ceph OSD Degradation
- **Preconditions**: Staging cluster with Ceph CSI or RBD; OSDs configured; no production Ceph cluster accessed.
- **Failure Simulation Method**: Detach a simulated OSD device; fill OSD disk (controlled); simulate OSD out via Ceph commands in isolated environment.
- **Expected Service Impact**: PVCs hosted on affected OSD become read-only or error; new PVCs cannot be provisioned on that OSD.
- **Detection Mechanism**: `ceph osd status` shows OSD out/degraded; `kubectl get pvc` shows bound PVCs in error state.
- **Expected Alerts**: `CephOSDDegradation` if self-monitoring active.
- **Recovery Procedure**: Re-add OSD; reclaim disk space; verify OSD in cluster map.
- **Data Integrity Validation**: Ceph health flag `HEALTH_OK` or `HEALTH_WARN` only; no `HEALTH_ERR` data corruption.
- **Success Criteria**: OSD rejoins cluster; health returns to OK; PVCs recover read-write.
- **Abort Conditions**: Production Ceph on shared storage; OSD removal without Ceph administrative approval.
- **Classification**: staging-only, production-sensitive approval-required.

### 12.7 Ceph MON Quorum Risk
- **Preconditions**: Staging cluster with Ceph MON quorum (3 nodes); quorum configuration documented.
- **Failure Simulation Method**: Stop one MON node in ephemeral cluster; observe quorum status; do NOT stop 2+ MONs (would lose quorum).
- **Expected Service Impact**: If 1 MON lost: quorum maintained, Ceph continues operating. If 2+ lost: quorum lost, Ceph services pause.
- **Detection Mechanism**: `ceph mon status` shows quorum; `ceph health` reports quorum status.
- **Expected Alerts**: `CephMONQuorumRisk` if projected below 3 MONs; actual `CephQuorumLost` if quorum lost.
- **Recovery Procedure**: Restart stopped MON; verify quorum re-established; check MON keyring integrity.
- **Data Integrity Validation**: No data corruption; quorum is pure availability feature. Data remains accessible with >= 3 MONs.
- **Success Criteria**: `ceph mon status` shows quorum=1 of 3 (or appropriate); `ceph health` HEALTH_OK.
- **Abort Conditions**: Production Ceph; stopping MONs without full quorum backup and administrative approval.
- **Classification**: lab-safe (ephemeral with 3 MONs), staging-only, production-sensitive approval-required.

### 12.8 PVC Mount Failure
- **Preconditions**: Staging cluster with a workload using a persistent volume claim; provisioner configured (placeholder).
- **Failure Simulation Method**: Delete the underlying PV in ephemeral cluster; detach the volume node; simulate storage exhaustion.
- **Expected Service Impact**: Pod restarts in `Pending` or `ContainerCreating`; events `PersistentVolumeClaimFailed`, `VolumeDetachFailed`.
- **Detection Mechanism**: `kubectl describe pod` shows `Restarting`; `kubectl get pvc` shows bound PVC no longer attached.
- **Expected Alerts**: `PVCPMountFailure` if self-monitoring active.
- **Recovery Procedure**: Restore PV; reclaim storage; verify volume re-attach.
- **Data Integrity Validation**: No data loss if PV is not deleted; only mount path unavailable.
- **Success Criteria**: Pod reaches `Running` state; application can read/write to mount path.
- **Abort Conditions**: Production storage with real data; PV deletion without backup and approval.
- **Classification**: staging-only, production-sensitive approval-required.

### 12.9 CNI Agent Failure
- **Preconditions**: Ephemeral or staging cluster with a pod requiring new network attachment; CNI plugin configured (e.g., Calico, Cilium).
- **Failure Simulation Method**: Restart the CNI DaemonSet pod; simulate network policy block; simulate IP exhaustion.
- **Expected Service Impact**: New pods fail to get IP addresses; existing pods lose connectivity if IP re-assignment required.
- **Detection Mechanism**: `kubectl get pods` shows `Pending` with `No such device` or `IP not assigned`; `ip addr` shows no interface IP.
- **Expected Alerts**: `CNIAgentFailure` if self-monitoring active.
- **Recovery Procedure**: Restart CNI DaemonSet; verify CNI plugin status; check network attachment definition.
- **Data Integrity Validation**: No IP conflicts; existing pod IPs preserved.
- **Success Criteria**: New pods receive IPs; existing pods retain connectivity.
- **Abort Conditions**: Production cluster; CNI restart without change-management window.
- **Classification**: lab-safe (ephemeral), staging-only.

### 12.10 Monitoring Component Failure
- **Preconditions**: Staging cluster with monitoring stack (Prometheus, Alertmanager, Grafana, Loki) running; one component marked for failure test.
- **Failure Simulation Method**: Restart Prometheus server; stop Alertmanager; stop Loki; or simulate disk full on Prometheus storage.
- **Expected Service Impact**: Gaps in metric collection; alerts not fired; logs not visible; dashboards show no data.
- **Detection Mechanism**: Component health endpoints return 503 or stop responding; self-alerts fire on component crash.
- **Expected Alerts**: `PrometheusDown`, `AlertmanagerDown`, `LokiDown` depending on component.
- **Recovery Procedure**: Restart component; verify data directory integrity; check compaction/retention.
- **Data Integrity Validation**: No user data lost; only visibility gap during outage.
- **Success Criteria**: Component healthy; metrics/alerts/logs flowing again; dashboards rendering.
- **Abort Conditions**: Production monitoring stack restart without SRE approval and rollback plan.
- **Classification**: staging-only, production-sensitive approval-required.
  **Important**: Monitoring component failure creates a visibility gap — alerts may not fire and metrics may not be collected, but the monitored workloads continue running. This is distinct from a service outage; the applications themselves are unaffected.

### 12.11 Vault/OpenBao Unavailable
- **Preconditions**: Staging cluster with workloads using Vault/OpenBao for secrets; secret engine configured.
- **Failure Simulation Method**: Stop Vault pod; seal Vault; simulate network partition to Vault endpoint.
- **Expected Service Impact**: Applications fail to fetch secrets at startup; cached secrets remain available if TTL not expired. New requests fail until Vault recovers.
- **Detection Mechanism**: Application logs secret fetch failures; `vault status` returns sealed or timeout.
- **Expected Alerts**: `VaultUnavailable` if self-monitoring active.
- **Recovery Procedure**: Unseal Vault (if sealed); restart pod; verify seal status; rotate leases if expired.
- **Data Integrity Validation**: No secret data lost; leases may expire, requiring re-authentication.
- **Success Criteria**: Vault unsealed; secrets reachable; applications fetch secrets successfully.
- **Abort Conditions**: Production Vault without approved unseal keys and rollback plan.
- **Classification**: staging-only, production-sensitive approval-required.

### 12.12 Keycloak Unavailable
- **Preconditions**: Staging cluster with workloads using Keycloak for authentication/authorization; realm configured.
- **Failure Simulation Method**: Stop Keycloak pod; simulate database connection loss; simulate network partition.
- **Expected Service Impact**: Users cannot authenticate; workloads reject requests with `401` or `login failed`. Cached sessions may remain valid per session TTL.
- **Detection Mechanism**: Authentication endpoint returns 503 or 401; Keycloak admin UI shows instance down.
- **Expected Alerts**: `KeycloakUnavailable` if self-monitoring active.
- **Recovery Procedure**: Restart Keycloak; verify database connectivity; check startup logs for errors; re-create admin credentials if rotated.
- **Data Integrity Validation**: No user data lost; sessions may expire, requiring re-login.
- **Success Criteria**: Keycloak running; authentication endpoint returns 200; users can log in.
- **Abort Conditions**: Production Keycloak without approved restart plan and database backup.
- **Classification**: staging-only, production-sensitive approval-required.

### 12.13 Argo CD Unavailable
- **Preconditions**: Staging cluster with Argo CD deployed; applications synced to desired state.
- **Failure Simulation Method**: Stop Argo CD server; delete Argo CD application set; simulate etcd data loss (not on production).
- **Expected Service Impact**: No new application deployments via Argo CD; existing running applications unaffected if already deployed. UI unavailable.
- **Detection Mechanism**: Argo CD UI returns 503; `argocd app sync` commands timeout; API returns error.
- **Expected Alerts**: `ArgoCDUnavailable` if self-monitoring active.
- **Recovery Procedure**: Restart Argo CD server; verify etcd data; re-authenticate if session expired; re-sync applications.
- **Data Integrity Validation**: No application manifest data lost if etcd intact; only UI/API access interrupted.
- **Success Criteria**: Argo CD server running; API responsive; applications in desired state.
- **Abort Conditions**: Production Argo CD without approved restart plan and etcd backup.
- **Classification**: staging-only, production-sensitive approval-required.

## Failure Simulation Methods (Do Not Use on Production/Shared Clusters)

| Method | Description | Safe Environment |
|--------|-------------|------------------|
| **Pod restart** | `kubectl rollout restart` or kill -9 on pod PID | Ephemeral, staging |
| **Node drain** | `kubectl drain` with `--ignore-daemonsets` | Ephemeral, staging |
| **etcd member stop** | `etcdctl member stop` on isolated etcd | Ephemeral (etcd embedded) |
| **Firewall/iptables** | Block egress/traffic to target service | Ephemeral, staging (network namespace) |
| **DNS pause** | Pause DNS controller pod; add NXDOMAIN override | Staging |
| **Registry timeout** | Block registry endpoint via iptables | Staging |
| **Ceph OSD detach** | Controlled OSD disk fill or remove | Staging (disks local to node) |
| **MON stop** | Stop one of 3 MON VMs/instances | Lab (3-MON setup) |
| **Component restart** | `systemctl restart <service>` or Kubernetes RestartPolicy | Staging |

> **Absolute constraint**: No actual failure injection on production or shared clusters. All methods above are for lab-safe or staging-only use. Classification columns indicate appropriate environment per scenario.

## Success Criteria Summary

Each scenario above defines success criteria as the minimum verifiable state that proves the system recovered or degraded gracefully. Success is never "no failure occurred" — it is "the system handled the failure as designed."

**Abort conditions** exist for every scenario that involves production or shared infrastructure. If any abort condition is triggered, stop the test, document the result, and request approval before proceeding.

*This document is part of the SRE integration-testing workstream for Task 004-P11.7. All example values are illustrative/placeholders. No actual failure injection is performed. Environment classifications ensure tests run in safe domains only.