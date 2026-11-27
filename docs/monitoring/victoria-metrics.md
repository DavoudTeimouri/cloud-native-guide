# Victoria Metrics Deployment Guide

Victoria Metrics is a lightweight, high-performance alternative to the Prometheus
stack for metrics collection, storage, and alerting. Use it when resource overhead
must be minimized or when Prometheus cardinality limits are a concern.

## Prerequisites

- Kubernetes cluster is deployed and healthy (Phase 1 complete).
- `kubectl` is configured to target the cluster.
- Helm 3 is installed on the operator machine.
- Storage class is available (see Phase 3 storage).
- Monitoring namespace does not yet exist.

## Step 1 — Add Helm Repository

```bash
helm repo add victoria-metrics https://victoriametrics.github.io/helm-charts/
helm repo update
```

## Step 2 — Create Monitoring Namespace

```bash
kubectl create namespace monitoring
```

## Step 3 — Deploy Victoria Metrics Operator

The operator manages Victoria Metrics components (VM Single, VM Agent, VM Insert,
VM Select, VM Alert) via custom resources.

```bash
helm install victoria-metrics-operator victoria-metrics/victoria-metrics-operator \
  --namespace monitoring \
  --create-namespace
```

Wait for the operator to be ready:

```bash
kubectl -n monitoring rollout status deployment/victoria-metrics-operator --timeout=300s
```

## Step 4 — Deploy VM Agent (Scrape Targets)

VM Agent collects metrics from nodes, pods, and services and forwards them to VM
Single or VM Insert.

```yaml
# vm-agent.yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMAgent
metadata:
  name: vm-agent
  namespace: monitoring
spec:
  image: victoriametrics/vmaction:v1.93.0
  scrapeConfigFiles:
    - key: scrape-config.yaml
      name: vm-agent-scrape-config
  serviceAccountName: vm-agent
  nodeSelector:
    kubernetes.io/os: linux
```

```bash
kubectl apply -f vm-agent.yaml
```

Create the scrape config:

```yaml
# scrape-config.yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - source_labels: [__address__]
        target_label: __address__
        regex: '(.*):10250'
        replacement: '${1}:10250'

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: 'true'
```

```bash
kubectl -n monitoring create configmap vm-agent-scrape-config \
  --from-file=scrape-config.yaml
kubectl -n monitoring label configmap vm-agent-scrape-config \
  app=victoria-metrics
```

## Step 5 — Deploy VM Single (Storage)

VM Single is the all-in-one storage component for small-to-medium clusters.

```yaml
# vm-single.yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMSingle
metadata:
  name: vm-single
  namespace: monitoring
spec:
  image: victoriametrics/vmsingle:v1.93.0
  storage:
    storageClassName: ceph-rbd
    size: 50Gi
  replicaCount: 1
```

```bash
kubectl apply -f vm-single.yaml
```

## Step 6 — Deploy VM Alert (Alerting)

```yaml
# vm-alert.yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMAlert
metadata:
  name: vm-alert
  namespace: monitoring
spec:
  image: victoriametrics/vmalert:v1.93.0
  datasources:
    - type: VictoriaMetricsSingle
      url: http://vm-single.monitoring.svc.cluster.local:8429
  ruleConfigMapSelector:
    matchLabels:
      app: vm-alert-rules
```

```bash
kubectl apply -f vm-alert.yaml
```

## Step 7 — Configure Alertmanager Integration

Create alert rules and point them at VM Alert or Alertmanager:

```yaml
# alertmanager-config.yaml
global:
  smtp_smarthost: 'localhost:25'
  smtp_from: 'alerts@internal'

route:
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 1m
  repeat_interval: 4h
  receiver: 'team-platform'

receivers:
  - name: 'team-platform'
    email_configs:
      - to: 'platform-team@internal'
```

```bash
kubectl -n monitoring create secret generic alertmanager-config \
  --from-file=alertmanager.yaml=alertmanager-config.yaml
```

## Validation Commands

```bash
# All Victoria Metrics components running
kubectl -n monitoring get pods -l app.kubernetes.io/managed-by=Helm

# VM Single is accepting writes
curl http://vm-single.monitoring.svc.cluster.local:8429/health

# VM Agent is scraping
kubectl -n monitoring logs -l app.kubernetes.io/name=vmaagent --tail=20

# Metrics are being stored
curl -s 'http://vm-single.monitoring.svc.cluster.local:8429/api/v1/query?query=up' | jq .
```

## Rollback

```bash
kubectl -n monitoring delete VMSingle vm-single
kubectl -n monitoring delete VMAgent vm-agent
kubectl -n monitoring delete VMAlert vm-alert
helm uninstall victoria-metrics-operator -n monitoring
```
