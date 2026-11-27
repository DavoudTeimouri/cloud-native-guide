# Monitoring Components

## Purpose and scope
Prometheus, Grafana, Alertmanager, Loki upgrades.

## Steps
1. Check version compatibility matrix
2. Backup configuration/rules/dashboards
3. Upgrade component one at a time
4. Verify targets/dashboards/alerts healthy

## Implementation
```bash
# Prometheus upgrade via Helm
helm upgrade prometheus prometheus-community/prometheus --version <new-version> -n monitoring

# Grafana upgrade via Helm
helm upgrade grafana grafana/grafana --version <new-version> -n monitoring

# Verify
kubectl get pods -n monitoring -l app=prometheus
kubectl get pods -n monitoring -l app=grafana
curl -vk http://prometheus.monitoring.svc:9090/-/healthy
curl -vk http://grafana.monitoring.svc:3000/api/health
```

## Validation
- All targets scraped successfully
- Dashboards load
- Alerts firing correctly

## Related
- [Kubernetes Infrastructure (6.13 Monitoring and Logging)](../06-kubernetes-infrastructure/6.13-monitoring-and-logging.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
