# Prometheus Troubleshooting

## Symptoms

- Prometheus targets show "down" in targets page
- No metrics being scraped
- Alertmanager not receiving alerts
- Prometheus disk usage growing unbounded
- Query performance degraded

## Likely causes

- Scrape config pointing to wrong targets
- ServiceMonitor not configured correctly
- Target pods not exposing /metrics endpoint
- Prometheus storage retention too long
- Query too heavy (too many labels, too long range)

## Diagnostic commands

```bash
# Is Prometheus running?
kubectl -n monitoring get pods -l app=prometheus
kubectl -n monitoring logs -l app=prometheus

# Check targets
curl -s http://<prometheus-url>/api/v1/targets | python3 -m json.tool

# Check ServiceMonitors
kubectl get servicemonitor -A

# Check scrape config
kubectl -n monitoring get prometheus -o yaml | grep -A20 scrape_configs

# Check disk usage
kubectl -n monitoring exec <prometheus-pod> -- df -h /prometheus

# Check target health
curl -sf http://<target-ip>:<metrics-port>/metrics | head -5
```

## Expected healthy state

- Prometheus pods: Running, 0 restarts
- All targets: "up" in /api/v1/targets
- ServiceMonitors: bound to correct services
- `/metrics` endpoint returns Prometheus-format metrics
- Disk usage within retention limits

## Remediation

- Fix scrape configuration targets
- Create/fix ServiceMonitor resources
- Ensure pods expose /metrics endpoint on correct port
- Reduce retention time: `--storage.tsdb.retention.time=15d`
- Optimize queries (reduce label cardinality, shorter ranges)

## Risks

- Changing scrape config can cause temporary metric gaps
- Reducing retention loses historical data
- Heavy queries can impact Prometheus performance

## Verification

```bash
curl -s http://<prometheus-url>/api/v1/targets | python3 -c "
import json,sys
d=json.load(sys.stdin)
for t in d['data']['activeTargets']:
    print(t['discoveredLabels']['job'], t['health'])
"
kubectl get servicemonitor -A```
