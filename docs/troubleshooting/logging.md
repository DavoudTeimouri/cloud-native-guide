# Logging Troubleshooting

## Symptoms

- Logs not appearing in aggregation system
- Log ingestion lagging behind real-time
- Log parser errors (malformed JSON, missing fields)
- Log storage full
- Fluent Bit/Fluentd not running

## Likely causes

- Log collector not running on nodes
- Wrong log paths in configuration
- Parser regex not matching log format
- Backend storage (Elasticsearch/Loki) unreachable
- Buffer overflow (too many logs, slow backend)

## Diagnostic commands

```bash
# Is log collector running?
kubectl -n logging get pods -l app=fluent-bit
kubectl -n logging logs -l app=fluent-bit

# Check log files exist
ls -la /var/log/<app>/
ls -la /var/log/pods/

# Check parser configuration
kubectl -n logging get configmap fluent-bit-config -o yaml

# Check backend connectivity
kubectl -n logging exec <fluent-bit-pod> -- curl -sf <backend-url>/api/health

# Check buffer status
kubectl -n logging exec <fluent-bit-pod> -- fluent-bit -c /fluent-bit/etc/fluent-bit.conf -R

# Check pod logs directly
kubectl logs <pod> -n <namespace> --tail=50
```

## Expected healthy state

- Fluent Bit/Fluentd daemonset: All pods Running
- Log files present at expected paths
- Parser configuration valid (no errors on startup)
- Backend reachable and accepting logs
- No buffer overflow warnings

## Remediation

- Restart log collector: `kubectl -n logging rollout restart daemonset/fluent-bit`
- Fix log paths in configuration
- Fix parser regex to match actual log format
- Fix backend connectivity (network, authentication)
- Increase buffer size or reduce log volume

## Risks

- Restarting log collector causes brief log gap
- Wrong parser config can cause all logs to be dropped
- Increasing buffer uses more disk/memory on nodes

## Verification

```bash
kubectl -n logging get pods -l app=fluent-bit
kubectl -n logging logs -l app=fluent-bit --tail=20 | grep -i error
kubectl logs <pod> -n <namespace> --tail=10```
