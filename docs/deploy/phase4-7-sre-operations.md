# Phase 4-7 SRE Operational Guides

*Site Reliability Engineering operational procedures for the cloud-native platform, covering Observability (Phase 4), Scaling & Expansion (Phase 5), Maintenance (Phase 6), and Troubleshooting (Phase 7). All procedures are validated against the reference documentation in `docs/monitoring/`, `docs/lifecycle/upgrades/`, `docs/troubleshooting/`, and `docs/kubernetes/`.*

---

## 4. Observability

### 4.1 Prometheus Operator Helm Install

| Item | Value |
|---|---|
| Chart | `kube-prometheus-stack` from `harbor.internal/charts/` |
| Namespace | `monitoring` |
| Release | `kube-prometheus-stack` |
| Key values | See `monitoring/prometheus.md` §E installation values.yaml |

**Install via Argo CD** — The stack is deployed as an Argo CD Application targeting the `mgmt-argocd` namespace (`docs/monitoring/prometheus.md` §A). The Git source points to the `obs-monitoring` GitLab project, path `kube-prometheus-stack`.

**Helm install (manual, outside Argo CD):**

```bash
helm upgrade --install kube-prometheus-stack harbor.internal/charts/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f values.yaml
```

**Post-install verification** (from `monitoring/prometheus.md` §F):

```bash
kubectl -n monitoring get pods
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
# Expect every job to report health: "up"
```

---

### 4.2 Node Exporter DaemonSet

- **Purpose**: Export node-level metrics (CPU, memory, disk, network) for Prometheus scraping.
- **Deployed via** the `kube-prometheus-stack` Helm chart values (see `monitoring/prometheus.md` §E).
- **ServiceMonitor** auto-created by the Helm chart; no manual scrape config needed.
- **Verification**:

```bash
kubectl -n monitoring get daemonset node-exporter -o wide
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="node-exporter") | .health'
# All targets should report health: "up"
```

---

### 4.3 kube-state-metrics

- **Purpose**: Export K8s object state (deployments, pods, nodes, etc.) as Prometheus metrics.
- **Deployed** as part of the `kube-prometheus-stack` (Helm `kubeStateMetrics.enabled: true`).
- **ServiceMonitor** auto-generated; metrics under job `kube-state-metrics`.
- **Verification**:

```bash
kubectl -n monitoring get pods -l app.kubernetes.io/name=kube-state-metrics
curl -s http://localhost:9090/api/v1/query?query=kube_deployment_status_replicas | python3 -m json.tool
# Should return a numeric value, not empty
```

---

### 4.4 cAdvisor

- **Purpose**: Container resource usage and analysis.
- **Deployed** via the `kube-prometheus-stack` Helm chart (`cAdvisor.enabled: true`); runs as a DaemonSet on each node.
- **ServiceMonitor** auto-created.
- **Verification**:

```bash
kubectl -n monitoring get pods -l k8s-app=cadvisor
curl -s http://localhost:9090/api/v1/query?query=container_memory_usage_bytes | python3 -m json.tool
# Should return metric families, not empty result
```

---

### 4.5 Grafana Dashboard Provisioning

- **Purpose**: Dashboards applied as code via Argo CD, not manually edited in the UI.
- **Dashboard JSON files** stored in the `obs-monitoring` GitLab project under `dashboards/` and provisioned by the `mgmt-grafana` Argo CD Application (`docs/monitoring/grafana-dashboard-provisioning.md`).
- **Provisioning files** declare which dashboards load on Grafana startup (`docs/monitoring/grafana-dashboard-provisioning.md` §4).
- **Validation workflow** (from `docs/monitoring/grafana-dashboard-provisioning.md` §5):

```bash
# 1. Edit a dashboard JSON file
vim monitoring/provisioning/dashboards/node-metrics.json

# 2. Commit and push
git add monitoring/provisioning/dashboards/node-metrics.json
git commit -m "Update node metrics dashboard: add CPU panel"
git push origin main

# 3. Wait for Argo CD sync
kubectl -n argocd wait application mgmt-grafana --for=condition=Healthy --timeout=300s

# 4. Verify provisioning
kubectl -n monitoring get grafanadashboard node-metrics -o jsonpath='{.metadata.name}'

# 5. Syntax validation
python3 scripts/check_links.py monitoring/grafana-dashboard-provisioning.md
```

**Related references**: `docs/monitoring/prometheus.md` §G (dashboard provisioning), `docs/monitoring/grafana-dashboard-provisioning.md` (full workflow).

---

### 4.6 Loki + Promtail Log Aggregation

- **Purpose**: Centralized log storage and search across all clusters.
- **Loki** deployed via the `loki` Helm chart within the `monitoring` namespace, backed by object storage (Ceph RBD or S3).
- **Promtail** DaemonSet collects container logs (`{cluster, namespace, pod} label set`), ships to Loki via Loki push API.
- **Grafana** queries Loki using the Loki data source; dashboards provisioned as code.

**Install Loki Helm chart** (values adapted from `monitoring/prometheus.md` architecture):

```bash
helm upgrade --install loki grafana/loki \
  --namespace monitoring \
  --create-namespace \
  -f loki-values.yaml
```

**Install Promtail DaemonSet** (inline in the kube-prometheus-stack values or separate):

```yaml
# loki-values.yaml excerpt
promtail:
  enabled: true
  config:
    clients:
      - url: http://loki:3100/loki/api/v1/push
    scrape_configs:
      - job_name: system
        static_configs:
          - targets:
              - "127.0.0.1"
        pipeline_stages:
          - labelmap: kubernetes_labels
            regex: "^(namespace|pod)(_.+)?$"
            action: keep
```

**Verification**:

```bash
# Check Loki is up
kubectl -n monitoring get pods -l app=loki
# Check Promtail pods
kubectl -n monitoring get pods -l app=promtail
# Test Loki query via port-forward
kubectl -n monitoring port-forward svc/loki 3100:3100 &
curl -s "http://localhost:3100/loki/api/v1/query?query={job=\"promtail\"} | json"
```

---

### 4.7 Alertmanager Routing to PagerDuty/Slack

- **Purpose**: Route alerts from Prometheus to the correct receivers based on severity.
- **Configuration** stored in Git, applied by Argo CD (`docs/monitoring/alertmanager-configuration.md`).
- **Receivers**: `pagerduty-critical` (PagerDuty), `slack-critical`, `slack-warning`, `slack-info` (from `docs/monitoring/alertmanager-configuration.md` §C).
- **Routing rules** (from `docs/monitoring/alertmanager-configuration.md` §D):

```yaml
route:
  receiver: 'slack-info'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 24h
  routes:
  - match:
      severity: 'critical'
    receiver: 'pagerduty-critical'
    continue: true
  - match:
      severity: 'warning'
    receiver: 'slack-warning'
  - match:
      severity: 'info'
    receiver: 'slack-info'
```

**PagerDuty receiver** (from `docs/monitoring/alertmanager-configuration.md` §C):

```yaml
receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '{{ .Chart.Secrets.PagerDutyKey }}'
    description: '{{ .CommonAnnotations.summary }}'
    severity: critical
    client: 'alertmanager'
    client_url: 'https://example.com'
```

**Slack receivers** (from `docs/monitoring/alertmanager-configuration.md` §C):

```yaml
receivers:
- name: 'slack-critical'
  slack_configs:
  - channel: '#critical-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookCritical }}'
    send_resolved: true
    title: '{{ .CommonLabels.alertname }} — {{ .Status }}'
- name: 'slack-warning'
  slack_configs:
  - channel: '#warnings-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookWarning }}'
    send_resolved: true
- name: 'slack-info'
  slack_configs:
  - channel: '#info-alerts'
    api_url: '{{ .Chart.Secrets.SlackWebhookInfo }}'
    send_resolved: true
```

**Verification** (from `docs/monitoring/alertmanager-configuration.md` §H):

```bash
amtool validate config alertmanager.yml
kubectl -n monitoring get svc alertmanager
amtool route alerts --config=alertmanager.yml < /dev/null
# Check firing alerts
kubectl -n monitoring get prometheusrules -o yaml | grep -A5 state: firing
```

---

### 4.8 Alert Rules

**Required alert coverage** (from `docs/monitoring/prometheus-alert-rules.md` §H and §F):

| Category | Alert Name | PromQL Expression | Condition |
|---|---|---|---|
| **Availability** | `APIServerDown` | `up{job="apiserver"} == 0` | API server not reachable |
| **Availability** | `NodeNotReady` | `kube_node_status_condition{condition="Ready",status="true"} == 0` | Node not ready |
| **Availability** | `etcdNoLeader` | `etcd_server_has_leader == 0` | etcd has no leader |
| **Availability** | `TargetDown` | `up == 0` for 10m | Scrape target down |
| **Capacity** | `NodeMemoryPressure` | `kube_node_status_condition{condition="MemoryPressure",status="true"} == 1` | Node memory pressure |
| **Capacity** | `PVCNearFull` | `kubelet_volume_stats_available_bytes / kubelet_volume_stats_capacity_bytes < 0.15` | PVC near full |
| **Capacity** | `DiskWillFillIn4Hours` | node-exporter filesystem rule | Disk will fill in 4 hours |
| **Capacity** | `PrometheusTSDBCompactionsFailing` | `rate(prometheus_tsdb_compactions_failed_total[3h]) > 0` | TSDB compactions failing |
| **Storage** | `CephHealthError` | `ceph_health_status == 1` | Ceph non-healthy |
| **Storage** | `CephOSDDown` | `ceph_osd_up == 0` | OSD down |
| **Storage** | `CephPoolNearFull` | `ceph_pool_bytes_used / ceph_pool_bytes_total > 0.85` | Pool > 85% used |
| **Storage** | `CephPGDegraded` | `ceph_pg_degraded > 0` | PGs degraded |
| **Certificates** | `CertificateExpiringSoon` | `probe_ssl_earliest_cert_expiry - time() < 14*24*3600` | Cert expiring in 14 days |
| **Certificates** | `CertificateExpiringIn7Days` | same with 7 days, page | Cert expiring in 7 days |
| **Backup** | `VeleroBackupFailed` | `velero_backup_status_backup_success == 0` | Backup failed |
| **Backup** | `NoRecentBackup` | `time() - velero_backup_last_success_timestamp > 86400*2` | No backup in 2 days |
| **Authentication** | `VaultAuthFailureSpike` | `rate(vault_route_auth_login[5m])` with failure labels | Auth failure spike |
| **Authentication** | `KeycloakAuthFailureSpike` | `rate(keycloak_authentication_failed[5m])` with failure labels | Auth failure spike |
| **GPU** | `DCGM GPU errors` | `DCGM_FI_DEV_GPU_XID_ERRORS` | GPU XID errors |
| **GPU** | `GPU memory pressure` | `DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_FREE + USED > 0.95` | GPU memory > 95% |
| **GPU** | `GPU temperature` | `DCGM_FI_DEV_GPU_TEMP > 85` | GPU temp > 85°C |
| **CNI** | `CNIFlowErrors` | `rate(cni_flow_errors_total[5m]) > 0` | CNI flow errors |
| **Prometheus** | `ScrapeFailure` | `up == 0` for 1m | Scrape failure |

**Inhibition rules** (from `docs/monitoring/prometheus-alert-rules.md` §I and `docs/monitoring/alertmanager-configuration.md` §E):

```yaml
inhibit_rules:
- source_match:
    severity: 'critical'
    alertname: 'ClusterDown'
  target_match:
    severity: 'warning'
    alertname: 'NodeCPUUsageHigh'
  equal: ['cluster']
- source_match:
    severity: 'critical'
    alertname: 'ClusterDown'
  target_match:
    severity: 'warning'
    alertname: 'MemoryUsageHigh'
  equal: ['cluster']
- source_match:
    severity: 'warning'
    alertname: 'NodeCPUUsageHigh'
  target_match:
    severity: 'info'
    alertname: 'DiskUsageHigh'
  equal: ['cluster']
```

**PrometheusRule example** (node pressure, from `docs/monitoring/prometheus-alert-rules.md` §F):

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-pressure-rules
  namespace: monitoring
spec:
  groups:
  - name: node-pressure
    interval: 30s
    rules:
    - alert: NodeMemoryPressure
      expr: |
        100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100) > 85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage on {{ $labels.instance }}"
        description: "Memory usage has been above 85% for 10 minutes. Value: {{ $value }}%"
    - alert: NodeDiskPressure
      expr: |
        node_filesystem_avail_bytes{mountpoint="/"} < 20% * node_filesystem_size_bytes{mountpoint="/"}
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Disk pressure on {{ $labels.instance }}"
        description: "Available disk is below 20% for 10 minutes. Value: {{ $value }}%"
    - alert: CNIFlowErrors
      expr: rate(cni_flow_errors_total[5m]) > 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "CNI flow errors detected"
        description: "CNI flow errors have been detected for 1 minute."
    - alert: VaultAuthFailureSpike
      expr: rate(vault_route_auth_login{failure="true"}[5m]) > 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Vault auth failure spike"
        description: "Vault authentication failures spiking."
    - alert: KeycloakAuthFailureSpike
      expr: rate(keycloak_authentication_failed{failure="true"}[5m]) > 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Keycloak auth failure spike"
        description: "Keycloak authentication failures spiking."
    - alert: PrometheusScrapeFailure
      expr: up{job="prometheus"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Prometheus scrape failure"
        description: "Prometheus cannot scrape targets."
```

**Validation** (from `docs/monitoring/prometheus-alert-rules.md` §G):

```bash
# Validate rules in CI
promtool check rules /path/to/prometheus-rules.yml

# Verify alerts are loaded
kubectl -n monitoring get prometheusrules

# Test a specific alert expression
curl -s http://localhost:9090/api/v1/query?query='up{job="node-exporter"}'
```

---

### 4.9 Validation Commands Summary

| Component | Command | Expected |
|---|---|---|
| **Prometheus targets** | `curl -s http://localhost:9090/api/v1/targets \| jq '.data.activeTargets[] \{job: .labels.job, health: .health\}'` | All jobs `health: "up"` |
| **Grafana health** | `kubectl -n argocd wait application mgmt-grafana --for=condition=Healthy --timeout=300s` | Application Healthy |
| **Grafana datasource** | `curl -s http://prometheus.monitoring.svc:9090/api/v1/query?query=up \| python3 -m json.tool` | JSON with metric values |
| **Loki ready** | `kubectl -n monitoring get pods -l app=loki` | Loki pod Running, 0 restarts |
| **Alertmanager config** | `amtool validate config alertmanager.yml` | Config is valid |
| **Prometheus rules** | `promtool check rules /path/to/rules.yml` | Rules pass validation |
| **ServiceMonitors** | `kubectl get servicemonitor -A` | All SMs listed, no errors |

---

## 5. Scaling & Expansion

### 5.1 Add Worker Node

| Step | Command / Action |
|---|---|
| **1. Add to inventory** | Add entry to `inventory/<cluster>/hosts.ini` under `[k8s-node]`: `k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23` |
| **2. Add OS and container runtime** | OS from internal mirror (Oracle Linux or Ubuntu); containerd 2.3.7 from internal repository; SSH access; NTP synchronized |
| **3. Run Kubespray** | `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3` |
| **4. Verify** | `kubectl get nodes k8s-w-3` <br> `kubectl get pods -o wide --field-selector spec.nodeName=k8s-w-3` |

**IPAM** — The Kubespray deployment uses built-in IP address management; no manual IP allocation needed. New node receives an IP from the defined subnet.

---

### 5.2 Add Control-Plane Node

| Step | Command / Action |
|---|---|
| **1. Add to inventory** | Add under `[control-plane]` and `[etcd]`: <br> `k8s-cp-4 ansible_host=10.20.0.14 ip=10.20.0.14` |
| **2. Add OS and container runtime** | Same as worker, plus etcd data directory on local SSD/NVMe |
| **3. Run Kubespray (one at a time)** | `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4` |
| **4. Verify** | `kubectl get nodes k8s-cp-4` <br> `kubectl -n kube-system get pods -l component=etcd --field-selector spec.nodeName=k8s-cp-4` <br> `kubectl -n kube-system exec etcd-k8s-cp-4 -- etcdctl endpoint health --cluster` |

**One control-plane node at a time** — never add all control-plane nodes simultaneously during a rebuild (see `docs/kubernetes/control-plane/node-lifecycle.md` §C, `docs/lifecycle/upgrades/kubernetes.md` §D).

---

### 5.3 Add GPU Node

| Step | Command / Action |
|---|---|
| **1. Create gpu-node group** | Add to inventory: `[gpu-node]` with appropriate hardware labels |
| **2. NVIDIA driver DaemonSet** | Deploy via Helm or manifest; ensure driver version matches GPU hardware |
| **3. NVIDIA labels** | Node labeled with `nvidia.com/gpu.count` and `nvidia.com/gpu.type` |
| **4. Test nvidia-smi** | `kubectl get nodes -l nvidia.com/gpu.count=1` <br> `kubectl exec -it <gpu-pod> -- nvidia-smi` |
| **5. Verify GPU workload scheduling** | Deploy a test pod with `nvidia.com/gpu` toleration; run `cuda_vectorAdd` |

**NVIDIA labels** (from `docs/gpu-ai/drivers/compatibility-matrix.md`):

```ini
[k8s-node]
k8s-gpu-1 ansible_host=10.20.0.31 ip=10.20.0.31

# After Kubespray deploy, add labels via taint/toleration or node-labels in group_vars
```

**nvidia-smi test**:

```bash
# Verify GPU is visible from a pod
kubectl run nvidia-test --rm -it --restart=Never --image=nvidia/cuda -- \
  nvidia-smi
# Should display GPU information
```

---

### 5.4 Add Ceph OSD

| Step | Command / Action |
|---|---|
| **1. Capacity headroom** | Ensure remaining cluster capacity > 30% before adding OSD (prevent OSD near-full) |
| **2. OSD provisioning** | ```bash <br> # Example: create OSD on /dev/sdb <br>ceph osd create /dev/sdb <br># Or via Ansible role in kubespray ceph role <br>``` |
| **3. CRUSH placement** | ```bash <br>ceph osd crush add-bucket osd.<id> host=<rack-name> <br>ceph osd crush move osd.<id> host=<rack-name> <br># Place on correct failure domain <br>``` |

**Capacity headroom guideline**: never let cluster exceed 85% overall; add OSD when `ceph_pool_bytes_used / ceph_pool_bytes_total > 0.85` triggers `CephPoolNearFull` alert.

---

### 5.5 Decision Matrix: Adding Nodes vs. Adding Components

| Decision | When to Add Node | When to Add Component | Risks / Mitigations |
|---|---|---|---|
| **Add worker node** | CPU/memory saturation > 80% sustained; pod pending due to insufficient resources | Scale up existing node (if resources allow) | **Risk**: Cluster disruption during Kubespray run <br> **Mitigate**: Add one at a time; verify node Ready before draining old |
| **Add control-plane node** | etcd quorum lost; API server availability < 3 of n nodes; want HA expansion | Add etcd member to existing quorum (if < 3 control-plane) | **Risk**: etcd quorum loss during add <br> **Mitigate**: Add one at a time; maintain 3+ control-plane for quorum |
| **Add GPU node** | GPU-accelerated workloads pending; no GPU capacity | Increase GPU node count; repurpose existing node | **Risk**: Driver version mismatch <br> **Mitigate**: Verify nvidia-smi test; match driver to hardware |
| **Add Ceph OSD** | OSD near full (>85%); PG recovery stuck; pool near full alert | Increase pool size; add cache tier | **Risk**: OSD full before provisioning <br> **Mitigate**: Monitor headroom; add OSD proactively when usage > 70% |
| **Add Loki node** | Log volume growing; query latency increasing | Add Promtail replicas; increase Loki storage | **Risk**: Imbalanced sharding <br> **Mitigate**: Add with same label set; verify Loki receives traffic |

**General rule**: If the issue is resource-scarcity (CPU, memory, disk, GPUs), add a node. If the issue is a specific service capacity (Ceph pool, Loki storage, database), add a component to the existing infrastructure first.

---

## 6. Maintenance

### 6.1 OS Patching

| OS | Patching Method | Notes |
|---|---|---|
| **Oracle Linux 9 (OL9)** | `dnf upgrade --refresh` <br> Or `leapp upgrade` for in-place major version leap | OL9 uses `leapp` for supported upgrades; dnf for minor/security patches <br> Reboot required; kubelet will re-register automatically |
| **Ubuntu 22.04 LTS** | `do-release-upgrade` for major version <br> `apt-get update && apt-get upgrade -y` for point releases | `do-release-upgrade` handles kernel, system packages; may require reboot <br> Verify `uname -a` after reboot |

**Procedure (OL9, dnf)**:

```bash
# On each node, one at a time
sudo dnf clean all
sudo dnf upgrade --refresh -y
sudo reboot
# Verify after reboot
uname -r
kubectl get nodes
```

**Procedure (Ubuntu, do-release-upgrade)**:

```bash
sudo apt-get update
sudo apt-get install -y update-manager-core
sudo do-release-upgrade -d
# Follow prompts; reboot when complete
```

---

### 6.2 Kernel Updates

- **OL9**: `dnf install kernel-<new>; grub2-set-default <new>; reboot`
- **Ubuntu**: `apt-get install linux-image-<new>; grub-set-default <new>; reboot`
- **Post-update verification**: `kubectl get nodes` all Ready; `kubectl get pods -o wide` no restarts; check `dmesg` for errors.

**Safety**: Always update one node at a time; drain the node before kernel update if running critical workloads.

---

### 6.3 Certificate Rotation

**Procedure: intermediate CA + leaf cert re-issuance**

| Step | Action |
|---|---|
| **1. Rotate intermediate CA** | Generate new intermediate CA key/cert; sign existing leaf certs if possible; distribute new CA trust bundle to all nodes |
| **2. Leaf cert re-issuance** | For each leaf cert (API server, kubelet, user, service): <br> `kubectl certificate approve <csr>;` <br> Or via cert-manager: `kubectl cert-manager renew <certname>` |
| **3. Restart kube-apiserver** | With new cert in place; verify `kubectl get nodes` still works |
| **4. Verify** | `openssl s_client -connect <api-host>:6443 -servername <api-host>` <br> Check cert expiry: `kubectl get secret <secret> -o jsonpath='{.data.tls\.crt}' \| base64 -d \| openssl x509 -noout -dates` |

**Automation**: cert-manager with external CA (Vault PKI) handles renewal automatically. For manual rotation, document in `docs/kubernetes/control-plane/cert-rotation.md`.

---

### 6.4 kubespray Upgrades

Refer to `docs/lifecycle/upgrades/kubernetes.md` and `docs/lifecycle/upgrades/kubespray.md` for the full procedure. High-level summary:

1. **Pre-upgrade**: Take etcd snapshot (`docs/lifecycle/upgrades/kubernetes.md` §F)
2. **Upgrade control-plane nodes one at a time** (Section E of kubernetes.md)
3. **Upgrade worker nodes one at a time** (drain, run cluster.yml --limit, uncordon)
4. **Post-upgrade verification** (Section G of kubernetes.md)
5. **Update kubespray/VERSION and group vars** in Git
6. **Rollback** if needed (restore etcd snapshot, revert group vars, re-run Kubespray)

**Never upgrade all control-plane nodes simultaneously** — this loses etcd quorum.

---

### 6.5 Health Checks

| Check | Command | Frequency |
|---|---|---|
| **Node status** | `kubectl get nodes -o wide` | Every shift |
| **Kubelet status** | `systemctl status kubelet` | Every shift |
| **Disk usage** | `ssh node "df -h /var/lib/kubelet/pods"` | Hourly |
| **Memory pressure** | `kubectl top node` | Every 4h |
| **Certificate expiry** | `openssl x509 -noout -dates -enddate <cert>` | Daily |
| **API server ready** | `kubectl get --raw='/readyz?verbose'` | Every 30m |

---

## 7. Troubleshooting Matrix

| Issue | Symptoms | Diagnostic Commands | Root-Cause | Safe Remediation | Verification | Rollback |
|---|---|---|---|---|---|---|
| **Node NotReady** | `kubectl get nodes` shows `NotReady`; pods not scheduled; kubelet logs show errors | `kubectl describe node <node>` <br> `kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'` <br> `journalctl -u kubelet -f` | kubelet service down; node network isolation; host hardware failure | 1. `kubectl cordon <node>` <br> 2. `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` <br> 3. Restart kubelet: `systemctl restart kubelet` <br> 4. If hardware failed, replace node (see §5.1) | `kubectl get nodes <node>` shows `Ready` <br> All pods rescheduled to other nodes | If node cannot be recovered: remove from inventory (§5.1 E), add replacement |
| **kubelet failure** | Node NotReady; `kubectl get nodes` hangs; kubelet logs show `failed to run Kubelet` | `systemctl status kubelet` <br> `journalctl -u kubelet --no-pager -n 50` <br> `ps aux \| grep kubelet` | kubelet config corruption; cert issues; disk full on node | 1. Check kubelet config `/etc/kubernetes/kubelet.conf` <br> 2. Renew certs if expired (§6.3) <br> 3. `systemctl restart kubelet` <br> 4. If repeated failure, `kubectl reset node` then re-add | kubelet Running; node Ready | If kubelet won't start: rebuild node (Terraform + Ansible) |
| **container runtime failure** | Pods CrashLoopBackoff; `crictl pods -a` shows runtime error; containerd logs show error | `crictl ps -a` <br> `journalctl -u containerd -f` <br> `systemctl status containerd` | containerd crash; corrupted snapshot; missing storage driver | 1. `systemctl restart containerd` <br> 2. Check storage pool: `lsblk` <br> 3. If corrupted, restore from backup <br> 4. Reboot node if needed | All pods Running; `crictl ps -a` shows correct state | If runtime persistent failure: reinstall node OS, re-run Kubespray |
| **CNI failure** | Pods `ContainerCreating`; `cilium status` not Ready; `kubectl get pods -n kube-system -l k8s-app=cilium` shows NotReady | `cilium status --verbose` <br> `cilium connectivity test` <br> `ip route get <pod-ip>` | MTU mismatch; missing route; IPtables stale; NetworkPolicy default-deny | 1. `cilium agent reload` <br> 2. Fix MTU: set in Cilium values `ipv4.mtu: 1450` <br> 3. Add missing routes (BGP or static) <br> 4. Check NetworkPolicy rules; add allow rule if needed | `cilium status`: Ready <br> `cilium connectivity test`: all pass <br> Pods IP reachable | Re-apply CNI manifest; if cluster-wide, rebuild CNI |
| **DNS problems** | Pods cannot resolve `kubernetes.default.svc.cluster.local`; `nslookup` timeout; CoreDNS pods Restarting | `kubectl run nettest --rm -it --restart=Never --image=busybox -- nslookup kubernetes.default.svc.cluster.local` <br> `kubectl -n kube-system get pods -l k8s-app=kube-dns` <br> `kubectl -n kube-system logs -l k8s-app=kube-dns` | CoreDNS misconfigured; NetworkPolicy blocking DNS; kube-proxy issues | 1. `kubectl restart deployment -n kube-system kube-dns` <br> 2. Check NetworkPolicy egress rules; add DNS allowance (UDP 53) <br> 3. `crictl pull` to verify external DNS <br> 4. If kube-proxy down, restart: `systemctl restart kube-proxy` | Pods can resolve cluster DNS | If CoreDNS persistent: redeploy CoreDNS with corrected config |
| **certificate problems** | `kubectl get secrets` shows `X509: certificate has expired`; apiserver logs `X509: certificate signed by unknown authority`; users cannot auth | `openssl x509 -noout -dates -enddate <cert>` <br> `kubectl describe secret <secret>` <br> `kubectl get certificate,clusterissuer` | Leaf cert expired; intermediate CA rotated without re-issuing; cert-manager not renewing | 1. Renew certs via cert-manager: `kubectl cert-manager renew <cert>` <br> 2. If manual: generate new CSR, sign with CA, distribute <br> 3. Restart apiserver <br> 4. Verify: `openssl s_client -connect <api>:6443` | All certs valid (not expired) <br> `kubectl auth can-i --list` works | If cert rotation fails: revert to previous cert from backup; restart services |
| **disk pressure** | Node NotReady; kubelet logs `disk pressure`: `eviction-hard: ["imagefs.available<=15%","nodefs.available<=10%"]`; `kubectl describe node` shows `condition: true` | `ssh node "df -h"` <br> `kubectl top nodes` <br> `kubelet volume_stats` | Node filesystem near full; log rotation not working | 1. `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` <br> 2. Clean up logs: `journalctl --vacuum-time=2d` <br> 3. Delete unused pods/RS <br> 4. Add disk or new node | Node Ready; disk < 80% | If disk cannot be freed: add new node (§5.1), drain workloads |
| **memory pressure** | Node NotReady; kubelet evicting pods; `kubectl top nodes` shows memory > 90% | `kubectl top nodes` <br> `ssh node "free -m"` <br> `journalctl -u kubelet -o json` | OOM on node; memory leak; too many pods scheduled | 1. `kubectl drain <node> --ignore-daemonsets` <br> 2. Reduce pod density; add new node (§5.1) <br> 3. Check pod resource requests/limits <br> 4. Restart kubelet if stuck | Node Ready; memory < 80% | If persistent: add node; rebalance workloads |
| **PID pressure** | Pods terminated; `kubectl get pods` shows `OOMKilled`; `dmesg` shows `PID limit reached` | `kubectl top pods --all-namespaces` <br> `ssh node "cat /proc/sys/kernel/pid_max"` <br> `journalctl -u kubelet -k` | Too many processes; container PID limit too low | 1. Increase `pod.spec.containers[].securityContext.capabilities.drop` <br> 2. Adjust kubelet `--pod-max-pids` <br> 3. Restructure workloads to reduce parallelism <br> 4. Add node if chronic | Pods run without OOMKill | If chronic: add node; tune PID limits |
| **network connectivity** | Pods cannot reach service IP; `curl <svc>` times out; `cilium connectivity test` fails | `cilium status` <br> `cilium endpoint list` <br> `ip a` on node <br> `ping <service-cluster-ip>` | CNI misconfigured; route missing; MTU mismatch; kube-proxy down | 1. `cilium agent reload` <br> 2. Fix MTU in Cilium values <br> 3. Add missing routes (BGP/static) <br> 4. `systemctl restart kube-proxy` <br> 5. If all else, rebuild CNI | `cilium connectivity test` all pass <br> Pods can reach services | Re-apply CNI; if cluster-wide, rebuild from scratch |
| **stuck terminating pods** | Pod `Terminating` state for > hour; `kubectl get pods` shows `Terminating`; cannot delete | `kubectl get pods -o wide` <br> `kubectl get pods <pod> -o jsonpath='{.status.terminationMessage}'` <br> `kubectl delete pod <pod> --grace-period=0 --force` | Pod has finalizer; waiting for graceful shutdown; PDB blocking | 1. `kubectl patch pod <pod> -p '{"metadata":{"finalizers":[]}}' --type=merge` <br> 2. `kubectl delete pod <pod> --grace-period=0 --force` <br> 3. If DaemonSet, ensure new pod starts before old terminates | Pod deleted; no stuck Terminating | If critical pod stuck: may need `kubectl replace pod ...` or drain node |
| **scheduling failures** | Pod pending `0/n nodes`; `kubectl describe pod <pod> -o json` shows ` Unschedulable` | `kubectl describe pod <pod> -o yaml` <br> `kubectl get nodes -o jsonpath='{.items[*].status.allocatable}'` <br> `kubectl describe node <node>` | Insufficient resources; taints/no matching toleration; affinity mismatch | 1. Add node (§5.1) <br> 2. Remove or adjust taint <br> 3. Fix affinity/selector rules <br> 4. Increase resource requests/limits | Pod scheduled; `Ready` nodes increased | If no nodes available: add node or increase capacity |
| **node registration failures** | New node not showing in `kubectl get nodes`; `kubelet` logs `failed to register node`: `the node ... already exists` | `kubectl get nodes` <br> `kubectl get nodes <new-node> --ignore-not-found` <br> `journalctl -u kubelet -k` | kubelet config mismatch; node name conflict; API server unresponsive | 1. Verify kubelet config: `--node-labels`, `--hostname-override` <br> 2. If name conflict: `kubectl delete node <old>` <br> 3. Re-join: `kubectl reset node <name>` then re-add node <br> 4. Ensure API server reachable from new node | Node appears in `kubectl get nodes` <br> Node status Ready | If still not registering: rebuild node OS, reinstall containerd+kubelet |

---

## Kubernetes Node Lifecycle Procedures

### Add Worker

| Step | Command / Action |
|---|---|
| **1. Cordon** (prevent new scheduling) | `kubectl cordon k8s-w-3` |
| **2. Drain** (evict pods safely) | `kubectl drain k8s-w-3 --ignore-daemonsets --delete-emptydir-data --force` <br> *Verify DaemonSet pods will reschedule; PDBs allow eviction* |
| **3. PeDB/stateful workload check** | - **DaemonSet**: pods will self-recover on other nodes <br> - **StatefulWorkloads**: ensure PVCs are not node-local; verify CRUD backup <br> - **Static pods**: drain may not affect them; handle manually |
| **4. API removal** | If node was added via Kubespray and you want to remove the API object: <br> `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3` (post-removal) |
| **5. Inventory update** | Remove node from `[k8s-node]` in `inventory/<cluster>/hosts.ini` |
| **6. Run Kubespray remove** | `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3` |
| **7. Verify** | `kubectl get nodes | grep k8s-w-3` should return nothing <br> `kubectl get pods -o wide --field-selector spec.nodeName=k8s-w-3` should return nothing |
| **8. Decommissioning** | Physically decommission or re-image the host; wipe disks if sensitive data |
| **9. Validation** | `kubectl get nodes` all Ready <br> `kubectl get pods -o wide` no pod on removed node |

**Remove worker** detailed procedure (cross-reference `docs/kubernetes/node-lifecycle.md` §E and `docs/kubernetes/control-plane/node-lifecycle.md` §F):

1. **Drain the node** as above, with `--ignore-daemonsets --delete-emptydir-data --force`
2. **PDB assessment**: `kubectl get poddisruptionbudgets -A` — ensure PDBs allow eviction count
3. **Remove from inventory**: edit `inventory/<cluster>/hosts.ini`, delete the `[k8s-node]` line
4. **Run Kubespray removal playbook**: `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3`
5. **Verify removal**: node gone from `kubectl get nodes`
6. **DaemonSet considerations**: DaemonSet pods auto-replicate to remaining nodes; no manual intervention needed
7. **Static-pod considerations**: if node runs static pods (e.g., kubelet-managed), manually stop or migrate them before drain
8. **Local storage**: if pods use `hostPath` or local PV, data is lost on removal; migrate to networked PV first
9. **Stateful workloads**: ensure StatefulSet PVCs are not node-specific; use `persistent-volume-reclaim-policy: Retain` and manually migrate data
10. **API object removal**: after Kubespray removes the node, verify no `Node` object remains; `kubectl get node <name>` should error or show `Removed`
11. **Inventory update**: ensure Ansible inventory reflects only existing nodes
12. **Decommissioning**: power off or re-image host; document in asset management

**Validation**: `kubectl get nodes` — all nodes listed and Ready; `kubectl get pods -o wide` — no pods on removed node name.

---

### Remove Worker

| Step | Command / Action |
|---|---|
| **1. Workload inventory** | List all workloads on node: `kubectl get pods -o wide --field-selector spec.nodeName=k8s-w-3` |
| **2. PDB assessment** | `kubectl get poddisruptionbudgets -A` — verify PDBs allow eviction |
| **3. Cordon** | `kubectl cordon k8s-w-3` |
| **4. Drain** | `kubectl drain k8s-w-3 --ignore-daemonsets --delete-emptydir-data --force` |
| **5. DaemonSet considerations** | DaemonSet pods will self-replicate; no action needed |
| **6. Static-pod considerations** | Stop/migrate static pods manually before drain |
| **7. Local storage** | Migrate any `hostPath` or local PV data to networked PV |
| **8. Stateful workloads** | Migrate StatefulSet data to new nodes; verify PVCs detach/attach cleanly |
| **9. API object removal** | After Kubespray removal, verify `kubectl get node k8s-w-3` is gone |
| **10. Inventory update** | Remove `[k8s-node]` entry from `inventory/<cluster>/hosts.ini` |
| **11. Run Kubespray** | `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-3` |
| **12. Validation** | `kubectl get nodes | grep k8s-w-3` returns nothing <br> `kubectl get pods -o wide` — no pods on removed node |

---

### Replace Control-Plane

| Step | Command / Action |
|---|---|
| **1. Quorum/availability check** | Ensure existing control-plane nodes have quorum (3 of 3 or 2 of 3) before starting; if 2 of 3 available, can add 1 at a time |
| **2. etcd topology** | stacked etcd (on control-plane nodes) vs external etcd; procedure differs |
| **3. API server availability** | Ensure API server reachable; have `kubectl` access to remaining nodes |
| **4. Cert/endpoint implications** | New control-plane node will receive new API server cert; update LB membership accordingly |
| **5. LB membership** | Update load balancer (HAProxy, F5, KeepAlived) to include new node VIP; remove old node after replacement |
| **6. Safe replacement order** | Replace one control-plane node at a time; never remove more than 1 unless external etcd with 3+ members |
| **7. etcd member removal/replacement** | ```bash <br># Remove old member <br>kubectl -n kube-system exec etcd-<old> -- etcdctl member remove <old-id> --overwrite <new-id> <br># Add new member <br>kubectl -n kube-system exec etcd-<new> -- etcdctl member add <new-id> <br># Update CRUD <br>``` |
| **8. Inventory consistency** | Update `inventory/<cluster>/hosts.ini`: update `[control-plane]` and `[etcd]` groups; ensure new node has same group vars |
| **9. Recovery/rollback** | If replacement fails: restore etcd from pre-replacement snapshot (`docs/lifecycle/backup/backup-and-dr.md`) and re-join old node or re-run replacement sequence |

**Detailed replace control-plane procedure**:

1. **Add new control-plane node to inventory** (see §5.2 step 1).
2. **Run Kubespray to join node**: `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-new`
3. **Verify etcd quorum**: `kubectl -n kube-system exec etcd-k8s-cp-new -- etcdctl endpoint health --cluster`
4. **Migrate API LB**: update load balancer config to include new node's VIP; keep old node in LB but in drain mode
5. **Rotate API server certs** if needed (§6.3); restart kube-apiserver on new node
6. **Remove old control-plane node**: 
   - `kubectl drain k8s-cp-old --ignore-daemonsets --delete-emptydir-data --force`
   - `kubectl -n kube-system exec etcd-<old> -- etcdctl member remove <old-id> --overwrite <new-id>`
   - Remove old node from inventory and run Kubespray removal
7. **Verify cluster health**: all nodes Ready; API server responding; etcd quorum healthy
8. **Validation**: `kubectl get nodes` — shows new node, old node removed; `kubectl get --raw='/readyz?verbose'` — all healthy

** stacked vs external etcd**:

- **Stacked etcd** (control-plane nodes run etcd): replacement procedure as above; must maintain quorum at all times (3 of 3, or 2 of 3 during rolling replace).
- **External etcd** (separate etcd cluster): control-plane node replacement is simpler; etcd topology independent. Just ensure external etcd has 3 members minimum for quorum; remove/replace control-plane nodes one at a time without touching etcd members.

---

## References

- `docs/monitoring/prometheus.md` — Prometheus and Alertmanager architecture, installation, and validation
- `docs/monitoring/grafana-dashboard-provisioning.md` — Grafana dashboard provisioning as code
- `docs/monitoring/alertmanager-configuration.md` — Alertmanager receiver, routing, and silencing
- `docs/monitoring/prometheus-alert-rules.md` — Prometheus alerting rules, recording rules, and notification routing
- `docs/monitoring/victoria-metrics.md` — VictoriaMetrics long-term storage (optional)
- `docs/lifecycle/upgrades/kubernetes.md` — Kubernetes minor-version upgrade procedure
- `docs/lifecycle/upgrades/kubespray.md` — Kubespray-specific upgrade procedure
- `docs/kubernetes/node-lifecycle.md` — Node add/remove/replace procedures
- `docs/kubernetes/control-plane/node-lifecycle.md` — Control-plane node lifecycle
- `docs/troubleshooting/prometheus.md` — Prometheus troubleshooting runbook
- `docs/troubleshooting/cni.md` — CNI and network policy troubleshooting
- `docs/troubleshooting/cert-manager.md` — cert-manager certificate issuance troubleshooting
- `docs/gpu-ai/drivers/compatibility-matrix.md` — GPU node and driver compatibility
- `docs/ceph/ceph-monitoring.md` — Ceph OSD and pool monitoring

---