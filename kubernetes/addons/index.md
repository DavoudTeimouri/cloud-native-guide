# Kubernetes Add-ons

Optional add-ons deployed on top of the Kubespray cluster. Each add-on is installed via Helm chart from the internal Helm repository, with values air-gapped to internal registries.

## Add-ons in this platform

| Add-on | Chart | Purpose |
|--------|-------|---------|
| cert-manager | jetstack/cert-manager | Certificate issuance and management (Let's Encrypt, internal CA, Vault PKI) |
| External DNS | kubernetes-sigs/external-dns | DNS records for Services and Ingresses |
| Descheduler | kubernetes-sigs/descheduler | Evict pods to rebalance the cluster |
| VPA | kubernetes/autoscaler | Vertical Pod Autoscaler recommendations |
| Metrics Server | kubernetes-sigs/metrics-server | Resource metrics for HPA and VPA |
| Trivy Operator | aquasecurity/trivy-operator | Vulnerability and config scans as CRDs |
| OpenTelemetry Operator | open-telemetry/opentelemetry-operator | Collector, instrumentation, traces |

## Symptom: Add-on pod CrashLoopBackOff

**Likely cause:** Image not mirrored to the internal registry, or values point to `docker.io` / `quay.io` instead of the internal registry.

**Fix:** Update `image.repository` in the Helm values to `registry.internal:5000/<image>`, then `helm upgrade --install`.

**Self-check:** `kubectl get pods -n <addon-ns>` shows all pods `Running`.

**Ponytail:** Scope ceiling — add-on install and image mirroring only. Add add-on lifecycle, upgrades, and multi-environment promotion when those patterns are used.
