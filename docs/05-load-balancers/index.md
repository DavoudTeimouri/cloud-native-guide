# Load Balancers

Highly available load balancing architectures: Active/Active preferred, HAProxy/NGINX/other enterprise solutions, Keepalived VIP management, management-cluster and application-cluster LBs, native and container-based deployment.

## Purpose
Document load balancing for the Cloud-Native stack, including management-cluster LBs (K8s API, Rancher, Argo CD, monitoring), application-cluster LBs, deployment methods (native and Docker Compose), HA, health checks, TLS, and failover testing.

## Subsections

| Subsection | Covers |
|---|---|
| [Architecture](5.1-architecture.md) | HA load balancing; Active/Active vs Active/Standby VIP; HAProxy, NGINX, Keepalived VIP management/failover |
| [Management Cluster Load Balancers](5.2-mgmt-cluster-lbs.md) | At least two LB nodes for mgmt clusters; K8s API, Rancher, Argo CD, monitoring, Grafana, Prometheus |
| [Application Cluster Load Balancers](5.3-app-cluster-lbs.md) | Optional dedicated LB pairs per app cluster; when dedicated vs shared is justified |
| [Deployment Methods](5.4-deployment-methods.md) | Native and container-based deployment; Docker Compose preferred for container examples |
| [Configuration & Operations](5.5-configuration-operations.md) | HA config, health checks, TLS, backend config, timeouts, connection limits, observability, failover testing, backup, troubleshooting, upgrades |

## Cross-references
- LB nodes prepared in [Components (2.9 Load Balancer Nodes)](../02-components/2.9-lb-nodes.md).
- Port/firewall requirements from [shared network matrix](../shared/network-matrix/).
- LBs expose management/monitoring services from [Kubernetes (6.13 Monitoring & Logging)](../06-kubernetes-infrastructure/6.13-monitoring-and-logging.md).
