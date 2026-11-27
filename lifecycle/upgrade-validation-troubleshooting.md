# Section 12: Upgrade Validation and Troubleshooting

## Pre‑Upgrade Checklist (Run Before Any Upgrade)

| Category | Check | Command / Indicator | Expected Output |
|----------|-------|----------------------|-----------------|
| **Node Readiness** | All nodes `Ready` | `kubectl get nodes -o wide` | All nodes `Ready`, no `NotReady` |
| | Node resources available | `kubectl describe node <node>` | `Allocatable` > current usage; no `DiskPressure` or `MemoryPressure` |
| **API Server & etcd Health** | API server responding | `kubectl get --raw /healthz` | `200 OK` |
| | etcd health | `kubectl get --raw /healthz/etcd` | `healthy` |
| | etcd disk usage | `etcdctl endpoint status --write-out=table` | All endpoints healthy, no excessive disk use |
| **CNI Health** | CNI DaemonSet pods running | `kubectl get pods -n kube-system -l k8s-app=<cni>` | All pods `Running`, `Ready` |
| | CNI network configured | `kubectl get network-attachment-definitions` | Expected CNIs listed and attached |
| **CSI Health** | CSI Driver pods running | `kubectl get pods -n kube-system -l app=csi-driver` | All pods `Running`, `Ready` |
| | CSI controller/service available | `kubectl get csiversions` | Expected CSI drivers listed with versions |
| **Storage Health** | PV status | `kubectl get pv` | No `Released` or `Failed` PVs; available capacity |
| | Ceph/Rook cluster | `ceph -s` (if applicable) | `HEALTH_OK` or `HEALTH_WARN` only expected |
| **Pod Availability** | App pods running | `kubectl get pods -A` | All app pods `Running`; no `CrashLoopBackOff` |
| | PDB compliance | `kubectl get poddisruptionbudgets -A` | All pods within PDB limits; `Available` ≥ `MinAvailable` |
| **DNS & Networking** | CoreDNS running | `kubectl get pods -n kube-system -l k8s-app=kube-dns` | All CoreDNS pods `Running` |
| | Service CIDNs reachable | `kubectl get svc -A` | Expected services listed; no `ExternalName` loops |
| **Admission Policy Health** | ValidatingWebhookConfiguration status | `kubectl get validatingwebhookconfigurations` | No errors in webhook logs; all policies load |
| | MutatingWebhookConfiguration status | `kubectl get mutatingwebhookconfigurations` | Same as above |
| **Monitoring & Alert Delivery** | Prometheus scrape healthy | `curl http://prometheus:9090/api/v1/status/scrapes` | All targets `up` |
| | Alertmanager routing | `curl http://alertmanager:9093/api/v1/status` | `healthy` |
| **Logging** | Fluent Bit / Forwarder running | `kubectl get pods -n kube-system -l k8s-app=fluent-bit` | All pods `Running` |
| | Log aggregation reachable | `ls /var/log/containers/` (node check) | Log files present and recent |
| **Registry Access** | Image pullable | `crictl images` or `docker images` | Target images listed; no pull errors |
| **Identity & Secrets** | Vault / KMS reachable | `vault status` (or equivalent) | `sealed=false` or healthy response |
| | K8s secrets accessible | `kubectl get secrets -A` | Expected secrets listed |
| **GitOps Synchronization** | Argo CD app status | `argocd app sync <app>` | `Synced`; no drift detected |
| | Helm release status | `helm list -A` | All expected releases `deployed` |
| **Application‑Level Validation** | Health endpoint per app | `curl <app>/healthz` | `200 OK` or application‑specific healthy response |
| | Readiness/liveness probes | `kubectl get pods -A -o jsonpath='{.items[0].status.probes}'` | Probes configured and passing |

---

## Post‑Upgrade Checklist (Run After Upgrade)

| Category | Check | Command / Indicator | Expected Output |
|----------|-------|----------------------|-----------------|
| **Node Readiness** | All nodes `Ready` | `kubectl get nodes -o wide` | All nodes `Ready` at new version |
| | Kubelet version | `kubectl get nodes -o jsonpath='{.items[0].status.nodeInfo.kubeletVersion}'` | Matches target version |
| **API Server & etcd Health** | API server responding | `kubectl get --raw /healthz` | `200 OK` |
| | etcd healthy | `kubectl get --raw /healthz/etcd` | `healthy` |
| | etcd version | `etcdctl version` | Matches target or within supported skew |
| **CNI Health** | CNI DaemonSet pods running | `kubectl get pods -n kube-system -l k8s-app=<cni>` | All pods `Running`, `Ready` |
| | CNI version on nodes | `kubectl describe node <node> | grep -i cni` | Version matches target |
| **CSI Health** | CSI Driver pods running | `kubectl get pods -n kube-system -l app=csi-driver` | All pods `Running`, `Ready` |
| | CSI version on nodes | `kubectl describe node <node> | grep -i csi` | Version matches target |
| **Storage Health** | PV status | `kubectl get pv` | All PVs `Bound` or `Available`; no `Failed` |
| | Ceph/Rook cluster | `ceph -s` | `HEALTH_OK`; all daemons at target version |
| **Pod Availability** | App pods running | `kubectl get pods -A` | All app pods `Running`; no new `CrashLoopBackOff` |
| | PDB compliance | `kubectl get poddisruptionbudgets -A` | All pods within PDB limits |
| **DNS & Networking** | CoreDNS version | `kubectl get pods -n kube-system -l k8s-app=kube-dns -o jsonpath='{.container[0].image}'` | Matches target |
| | Network policies still applying | `kubectl get networkpolicy -A` | Expected policies listed |
| **Admission Policy Health** | ValidatingWebhookConfiguration | `kubectl get validatingwebhookconfigurations` | All policies load; no errors |
| | MutatingWebhookConfiguration | `kubectl get mutatingwebhookconfigurations` | Same |
| **Monitoring & Alert Delivery** | Prometheus targets `up` | `curl http://prometheus:9090/api/v1/status/scrapes` | All targets `up` with new version |
| | Alertmanager healthy | `curl http://alertmanager:9093/api/v1/status` | `healthy` |
| **Logging** | Fluent Bit / Forwarder running | `kubectl get pods -n kube-system -l k8s-app=fluent-bit` | All pods `Running` |
| | Logs appearing in aggregation | Check recent logs in Loki/ELK | Recent application logs present |
| **Registry Access** | Image pullable after upgrade | `crictl pull <image>:<tag>` | Pull succeeds |
| **Identity & Secrets** | Vault / KMS reachable | `vault status` | Healthy response |
| | Secrets rotated or updated | `kubectl get secrets -A` | Expected secrets present |
| **GitOps Synchronization** | Argo CD app sync | `argocd app sync <app>` | `Synced`; no drift |
| | Helm release status | `helm list -A` | All expected releases `deployed` |
| **Application‑Level Validation** | Health endpoint per app | `curl <app>/healthz` | `200 OK` |
| | Readiness/liveness probes passing | `kubectl get pods -A` | All pods pass probes |

---

## Troubleshooting Workflows

### General Pattern

1. **Symptom** — Observe the failure sign (error message, metric spike, pod failure).
2. **Diagnostic commands** — Run the minimal set of commands to reproduce / identify the root cause.
3. **Expected outputs** — Compare actual output against the expected column above.
4. **Logs / metrics** — Pull relevant logs (kubelet, kube-apiserver, etcd, component-specific) and check golden‑signal metrics.
5. **Isolation steps** — Narrow the scope: disable one variable at a time (e.g., drain a node, roll back a single component).
6. **Root‑cause analysis** — Determine if the cause is:
   - Incompatible version (skew, removed API field)
   - Missing offline artifact (image not pulled)
   - Backup/restore gap
   - PDB / quota exhaustion
   - Admission webhook blocking
7. **Safe remediation** — Apply the fix (roll back, update config, add missing RBAC, pull missing artifact).
8. **Recovery validation** — Re-run the post‑upgrade checklist to confirm the fix.

---

## Representative Failed‑Upgrade Scenarios & Decision Matrix

| Scenario | Symptoms | Decision | Rationale |
|----------|----------|----------|-----------|
| **CNI version skew** | Nodes `NotReady` after K8s upgrade; `kubectl get nodes` shows `InternalError` | **pause** | CNI does not support the new K8s API version. Roll back K8s or upgrade CNI first. |
| **CSI driver mismatch** | CSI‑backed pods fail to mount; `events` show `CSI volume not ready` | **pause** | CSI driver version incompatible with K8s. Upgrade CSI driver or revert K8s. |
| **Admission webhook block** | `kubectl create` hangs or returns `503`, validating webhook errors in logs | **pause** | Webhook misconfiguration or API version mismatch. Fix webhook config or disable temporarily. |
| **etcd data corruption** | API server returns `500`, `etcdctl` reports `db file corrupt` | **recover** | Restore from verified etcd backup; this is a disaster‑recovery path, not a simple rollback. |
| **PDB exhaustion** | Pods stuck in `Terminating`; nodes drain fails | **continue** (with manual PDB adjustment) | Raise PDB `minAvailable`/`maxUnavailable` temporarily; verify no availability impact. |
| **Monitoring alert flood** | Alertmanager receives 1000+ alerts post‑upgrade; new metric labels appear | **continue** if error budget still healthy; otherwise **pause** and investigate. | New labels are benign; adjust alert rules. If error budget consumed, defer further changes. |
| **Keycloak OIDC token mismatch** | OIDC consumers return `401`; tokens decoded show unexpected claims | **recover** | Update OIDC consumer config to match new Keycloak version; restart affected applications. |
| **Registry pull failure** | Pods `ImagePullBackOff`; `crictl pull` fails with auth error | **escalate** | Credentials expired or registry endpoint changed. Fix registry auth; if unavailable, revert to previous image tag. |
| **Argo CD sync drift** | Apps show `OutOfSync`; `argocd app sync` cannot reconcile | **pause** | Argo CD version incompatibility with K8s API. Upgrade Argo CD or pin K8s version. |

### Decision Rules

- **continue** — If the issue is cosmetic, non‑blocking, and the error budget remains within target; document and monitor.
- **pause** — If a component is blocked or a critical dependency is broken. Halt further rollout; diagnose and fix before proceeding.
- **recover** — If data loss or corruption is involved. Engage backup/restore or disaster‑recovery procedures.
- **escalate** — If the issue cannot be resolved within the change window, requires vendor support, or impacts multiple clusters. Open a ticket with the required details (timeline, affected components, diagnostic output).

---

## Recovery Validation (Post‑Fix)

After any remediation, run the full **Post‑Upgrade Checklist** (section above) on the affected component(s) and verify:

- All nodes `Ready` at the target version.
- API server and etcd healthy.
- CNI, CSI, storage, and pod availability consistent.
- PDB compliance restored.
- Monitoring and alerting normalized.
- Application health endpoints returning expected responses.
- GitOps synchronization synced.
- Change record updated with the fix and outcome.

If all checks pass, declare the recovery complete and close the change record.
