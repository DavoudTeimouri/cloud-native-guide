# Descheduler

Descheduler evicts pods so the cluster can rebalance (e.g. after new nodes join or when node utilization is uneven).

## Symptom: Pods not evicted despite uneven utilization

**Likely cause:** Descheduler not running, or the eviction policy does not match the imbalance.

**Fix:**
```bash
kubectl get descheduler -A
kubectl describe descheduler -n <ns>
kubectl get events -n <ns> | grep -i descheduler
```

**Self-check:** Run in `DryRun: true` mode first and confirm events list evictions without actually evicting.

**Ponytail:** Scope ceiling — Descheduler install and dry-run verification. Add production eviction, profile selection, and scheduling integration when those patterns are used.
