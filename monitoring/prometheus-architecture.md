# Prometheus Architecture

## A. Purpose and scope

Cluster-wide monitoring system with single-node and multi-node deployments. Covers scrape pipelines, long-term storage, and high-availability patterns used across the platform.

## B. Server deployment

### Single-node deployment

- One Prometheus instance per cluster, deployed via the `kube-prometheus-stack` Helm chart.
- Resources: `500m CPU / 2Gi` requests, `2 CPU / 4Gi` limits.
- Storage: PVC with `ceph-block` storage class, `15d` retention, `80GB` size limit.
- Run `kubectl -n monitoring get pods` and `kubectl -n monitoring port-forward svc/kube-prometheus-prometheus 9090:9090` to verify.

### Multi-node / sharded deployment

- Prometheus scales by sharding targets across instances via `prometheusSpec.replicas`.
- Each replica owns a hash of the target; no central coordinator needed.
- Replicas do not share state; long-term storage is handled by Thanos sidecar.
- Use `prometheusSpec.serviceMonitorSelectorNilUsesHelmValues: false` to ensure cross-namespace ServiceMonitors are discovered.

## C. Scrape configuration

### Built-in scrape targets

| Component | Exporter | Discovery method |
|---|---|---|
| Nodes | `node-exporter` | DaemonSet, K8s node label selectors |
| Control plane | `apiserver`, `scheduler`, `controller-manager`, `etcd` | K8s service discovery |
| Cluster add-ons | `kube-state-metrics` | K8s SD |
| Ceph | `ceph-exporter` | Static config or Ceph endpoints |
| GPU | `dcgm-exporter` | ServiceMonitor with `dcgm-exporter` labels |
| Git infra | `harbor-exporter`, `nexus-exporter`, `gitlab-exporter` | Static config |

### Service Discovery

- **K8s service discovery**: Prometheus picks up `Service` objects with annotations `prometheus.io/scrape: "true"` and `prometheus.io/port` / `prometheus.io/path`.
- **ServiceMonitor (Prometheus Operator)**: Preferred method. Define `ServiceMonitor` CRs that select Services by labels; the operator generates the required `scrape_config` automatically.
- **Relabeling**: Use `metric_relabel_configs` and `source_relabel_configs` to drop/rename labels, limit cardinality (keep `pod`, `namespace`, `job` only), and drop `pod_uid`.

### Remote write / storage

- **Local storage**: Default; TSDB on local PVC. Retention configured via `prometheusSpec.retention` (e.g., `15d`) and `prometheusSpec.retentionSize` (e.g., `80GB`).
- **Remote write**: Configure `remoteWrite` in the Prometheus spec to ship metrics to Thanos sidecar or Thanos object storage.
  - Typical URL: `http://thanos-sidecar. monitoring.svc:9093/api/v1/write`
  - Compression: `snappy`
  - Write timeout: `30s`
- **Remote read**: `remoteRead` points to the Thanos query endpoint for historical queries across clusters.

### Long-term storage (Thanos)

- Thanos sidecar runs alongside Prometheus, uploading encrypted blocks to object storage (Ceph S3-compatible).
- Thanos querier provides global view across clusters.
- Verify with `thanos query` and view retention timeline in the Thanos UI.

## D. Retention

- **Short-term**: Local TSDB on PVC. Default `15d` retention, adjustable via Helm value `prometheusSpec.retention`.
- **Size cap**: `retentionSize` (e.g., `80GB`) enforces a hard limit; when exceeded, the oldest chunks are deleted.
- **Long-term**: Thanos uploads compressed blocks to object storage after compaction. Retention there is effectively unlimited, governed by object-store lifecycle policies.
- **Compaction**: Runs every `2h` by default; monitor `prometheus_tsdb_compaction_seconds_total` for failures.

## E. HA considerations

### Active-Passive (replica-based)

- Multiple Prometheus replicas via `prometheusSpec.replicas > 1`.
- Each replica scrapes a disjoint subset of targets (sharded by target hash).
- No active-active sync; if one replica fails, others continue with reduced coverage.
- Failover is manual: delete the failed pod, the operator reschedules it.

### Cross-cluster visibility

- Deploy a **canary Prometheus** in the Management Cluster that scrapes both clusters.
- Use Thanos **federation** or **query** across clusters for unified dashboards.
- Alternatively, use `prometheusSpec.remoteWrite` to forward all metrics to a central Thanos bucket.

### Alertmanager coupling

- Prometheus HA requires matching Alertmanager deployment.
- Use `alertmanagerSpec` with `replicas: 3` and `clusterName: <unique>`.
- Inhibit rules and routing configs live in Git; changes are applied by Argo CD.

## F. Validation

```bash
# Check active targets
kubectl -n monitoring port-forward svc/kube-prometheus-prometheus 9090:9090 &
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Verify retention and TSDB health
kubectl -n monitoring exec deployment/kube-prometheus-prometheus -c prometheus -- promtool check tsdb

# Long-term storage check
thanos object stats <bucket-name> | head -20

# Scrape failure troubleshooting
kubectl -n monitoring get prometheus -o jsonpath='{.items[0].status.selectorDuration}'
```
