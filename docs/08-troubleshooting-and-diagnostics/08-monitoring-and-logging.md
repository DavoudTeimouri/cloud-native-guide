# 08 · Monitoring and Logging

## Symptoms
- Prometheus targets down
- Grafana dashboard empty or error
- Alertmanager not sending alerts
- Loki not receiving logs
- Fluent Bit not shipping logs

## Possible causes
- Prometheus scrape config wrong or target unreachable
- Grafana datasource misconfigured
- Alertmanager not running or receiver misconfigured
- Loki not reachable or Fluent Bit not configured
- Firewall blocking metrics/logs ports

## Diagnostic commands
```bash
# Prometheus
kubectl get pods -n monitoring -l app=prometheus
curl -vk http://prometheus.monitoring.svc:9090/api/v1/targets

# Grafana
kubectl get pods -n monitoring -l app=grafana
curl -vk http://grafana.monitoring.svc:3000/api/health

# Alertmanager
kubectl get pods -n monitoring -l app=alertmanager
curl -vk http://alertmanager.monitoring.svc:9093/api/v2/status

# Loki/Fluent Bit
kubectl get pods -n logging -l app=loki
kubectl get pods -n logging -l app=fluent-bit
```

## Expected output
- Prometheus: targets healthy
- Grafana: api/health returns 200
- Alertmanager: status healthy
- Loki: ready; Fluent Bit shipping

## Investigation procedure
1. Check monitoring/logging pods running
2. Test Prometheus targets endpoint
3. Test Grafana health API
4. Test Alertmanager status API
5. Check Fluent Bit logs for shipping errors

## Resolution
- Restart failed monitoring component
- Fix scrape config or datasource
- Fix Alertmanager receiver config
- Fix Fluent Bit output config (Loki endpoint)

## Verification
- Prometheus targets healthy; Grafana healthy; Alertmanager healthy; Loki receiving logs

## Prevention
- Monitor Prometheus/Grafana/Alertmanager health; alert on crash
- Monitor scrape target health; alert on target down
- Monitor Loki ingestion rate; alert on drop to zero

## Related
- [06 · Kubernetes Infrastructure (6.13 Monitoring and Logging)](../06-kubernetes-infrastructure/6.13-monitoring-and-logging.md)
- [07 · Software-Defined Storage (7.6 Monitoring and Logging)](../07-software-defined-storage/7.6-monitoring-and-logging.md)
