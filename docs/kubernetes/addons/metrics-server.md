# Metrics Server

Metrics Server provides resource metrics (CPU/memory) for HPA and VPA.

## Symptom: HPA cannot scale (no metrics)

**Likely cause:** Metrics Server not deployed, or `kubelet` is not exposing the metrics endpoint.

**Fix:**
```bash
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -A
```

**Self-check:** `kubectl top nodes` returns metrics for all nodes.

**Ponytail:** Scope ceiling — Metrics Server install and basic verification. Add HPA integration, custom metrics, and resource quotas when those patterns are used.
