# VPA (Vertical Pod Autoscaler)

VPA recommends or applies CPU/memory requests based on observed usage.

## Symptom: VPA recommendations not shown

**Likely cause:** VPA not deployed, or the target Deployment has no resource requests set.

**Fix:**
```bash
kubectl get vpa -A
kubectl describe vpa <name> -n <ns>
```

**Self-check:** `kubectl describe vpa <name>` shows `recommendation` with CPU/memory values.

**Ponytail:** Scope ceiling — VPA install and recommendation verification. Add Auto mode (with pod restarts), HPA coexistence, and exclusion rules when those patterns are used.
