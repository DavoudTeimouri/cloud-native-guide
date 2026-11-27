# Monitoring Architecture

*Illustrative only — not production-committed configuration. Marked as such where indicated.*

## Overview

This document describes the component-level monitoring and observability architecture for the platform. It defines what is monitored, how, and the expected failure conditions. **Optional components are explicitly identified alongside required ones.**

## Monitoring Stack Components

| Component | Required | Purpose | Scrape Method | Notes |
|---|---|---|---|---|
| `kube-prometheus-stack` | ✅ Required | Full-stack Prometheus + Grafana + Alertmanager via Helm | `ServiceMonitor` CRs | Default deployment; includes base node, API, and cluster metrics |
| `kube-prometheus-stack.thanos` | Optional | Long-term retention via Thanos | `ServiceMonitor` + object storage | Adds `thanos-query` and `thanos-sidecar`; recommended for >15d retention |
| `vault-exporter` | Optional | Vault secret and seal status | `ServiceMonitor` with selector `app=vault-exporter` | Metrics: `vault_sealed`, `vault_auth_failures_total` |
| `keycloak-exporter` | Optional | Keycloak authentication and session metrics | `ServiceMonitor` with selector `app=keycloak-exporter` | Metrics: `keycloak_auths_total`, `keycloak_sessions_active` |
| `harbor-exporter` | Optional | Harbor registry health and pull metrics | `ServiceMonitor` with selector `app=harbor-exporter` | Metrics: `harbor_image_pull_success_total`, `harbor_image_pull_failure_total` |
| `ceph-exporter` | Optional | Ceph storage cluster health | `ServiceMonitor` with selector `app=ceph-exporter` | Metrics: `ceph_health_status`, `ceph_pg_degraded` |
| `node-exporter` | ✅ Required | Node-level hardware metrics (CPU, memory, disk) | `ServiceMonitor` auto-discovered via kubernetes_sd | Standard Prometheus exporter |
| `pod-exporter` | ✅ Required | Pod resource usage metrics | `ServiceMonitor` auto-discovered | summarizes container CPU/memory limits |
| `alertmanager` | ✅ Required | Notification routing and inhibition | Built into kube-prometheus-stack | Routes: critical→pager, warning→Jira, info→dashboard only |

## Component Groups (A–H)

The following groups define the monitoring scope per component cluster. Each group maps to a set of recording rules, alert rules, and Grafana dashboards.

| Group | Components | Included Metrics | Default Dashboard |
|---|---|---|---|
| **Group A** | Control plane, API server, etcd | `apiserver_request_latency_seconds_bucket`, `etcd_disk_wal_fsync_duration_seconds_bucket` | API server & etcd overview |
| **Group B** | CNI, networking, Cilium | `hubble_observability_flow_dropped_total`, `cni_network_policy_drop_total` | Network policy & flow health |
| **Group C** | Storage (Ceph, PVC, RGW) | `ceph_health_status`, `ceph_pg_degraded`, `kube_pod_status_pending{reason="VolumeBoundPending"}` | Storage health & I/O latency |
| **Group D** | Ingress, L7 load balancing | `nginx_ingress_controller_requests_total{status="5xx"}`, `tls_handshake_failure_total` | Ingress & TLS health |
| **Group E** | Secrets, authentication | `vault_sealed`, `vault_route_auth_login{failure="true"}`, `keycloak_auths_total` | Auth & secrets status |
| **Group F** | Registry, image pipeline | `harbor_image_pull_success_total`, `harbor_image_pull_attempt_total{result="failed"}` | Registry metrics & pull success |
| **Group G** | Workload scheduling, lifecycle | `kube_pod_status_pending`, `container_crash_looping_total`, `velero_backup_success_total` | Scheduling & backup health |
| **Group H** | GitOps, CI/CD | `argocd_app_status_synced`, `argocd_app_reconcile_failure_total`, `prometheus_up` | GitOps & pipeline health |

## Expected Results + Failure Conditions

Each group has defined success metrics and explicit failure conditions. When any metric crosses its threshold, the associated alert fires and the runbook is invoked.

### Group A — Control Plane

- **Success**: `apiserver_request_latency_seconds_bucket{pct="99"} < 0.5s` over 30d; `etcd_disk_wal_fsync_duration_seconds_bucket{pct="99"} < 5s`
- **Failure**: `up{job="apiserver"} == 0` → `APIServerDown` critical alert; `etcd_leader_changes_total` spike > 1/hour

### Group B — Networking

- **Success**: `hubble_observability_flow_dropped_total` < 1% of `hubble_observability_flow_total`; no new `cni_network_policy_drop_total` events
- **Failure**: `hubble_observability_flow_dropped_total` increase → `CNIConnectivityLoss` critical alert; BPF program load failures

### Group C — Storage

- **Success**: `ceph_health_status == 0`; `ceph_pg_degraded == 0`; PVC bound rate > 99.9% over 30d
- **Failure**: `ceph_pg_degraded > 0` → `CephPoolDegraded` warning alert; PVC provisioning failures → `PVCPending` warning

### Group D — Ingress / TLS

- **Success**: Ingress 5xx rate < 0.1%; `tls_handshake_failure_total == 0`; no certificate expiry within 30d
- **Failure**: `nginx_ingress_controller_requests_total{status="5xx"} > 0` → `Ingress5xxSurge` critical alert; `tls_handshake_failure_total` increase

### Group E — Secrets / Auth

- **Success**: `vault_sealed == 0`; `vault_route_auth_login{failure="true"} == 0`; no secret rotation failures
- **Failure**: `vault_sealed == 1` → `VaultSealed` critical alert; auth login failures → `VaultAuthenticationFailure` warning

### Group F — Registry

- **Success**: `harbor_image_pull_success_total / harbor_image_pull_attempt_total > 99.9%`; p95 pull latency < 30s
- **Failure**: `harbor_image_pull_attempt_total{result="failed"} > 0` → `RegistryPullFailed` critical alert; TLS certificate expiry

### Group G — Workload Lifecycle

- **Success**: `kube_pod_status_pending{reason!="Unschedulable"} < 0.5%`; `container_crash_looping_total` stable or decreasing
- **Failure**: Pods `Pending` indefinitely → runbook investigation; `container_crash_looping_total` increase → `CrashLoopBackOff` diagnostics

### Group H — GitOps / CI-CD

- **Success**: `argocd_app_status_synced == 1` for all applications; `prometheus_up == 1` for all scrape jobs
- **Failure**: `argocd_app_status_synced == 0` → `ArgoCDOutOfSync` warning alert; `prometheus_up == 0` per job → monitoring coverage gap

## Upstream References

- Prometheus operator docs: <https://prometheus-operator.dev>
- Grafana dashboard best practices: <https://grafana.com/docs/grafana/latest/dashboards/>
- Alertmanager documentation: <https://prometheus.io/docs/alertmanaging/>
- kube-prometheus-stack chart: <https://github.com/prometheus-operator/kube-prometheus-stack>