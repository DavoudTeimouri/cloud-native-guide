# OpenTelemetry Operator

OpenTelemetry Operator deploys the OTel Collector for traces, metrics, and logs.

## Symptom: No traces exported

**Likely cause:** Collector not deployed, or the exporter endpoint is unreachable.

**Fix:**
```bash
kubectl get opentelemetrycollector -A
kubectl logs -n opentelemetry -l app.kubernetes.io/component=collector --tail=100
```

**Self-check:** The OTel Collector pod is `Running` and traces appear in the backend (Tempo/Jaeger).

**Ponytail:** Scope ceiling — OTel Operator install and collector health. Add instrumentation auto-injection, trace sampling, and log routing when those patterns are used.
