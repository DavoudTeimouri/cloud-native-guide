# Trivy Operator

Trivy Operator runs vulnerability and configuration scans as Kubernetes CRDs.

## Symptom: No vulnerability reports

**Likely cause:** Trivy Operator cannot reach the Trivy DB, or the image is not mirrored.

**Fix:**
```bash
kubectl get trivyoperator -A
kubectl get vulnerabilityreport -A
kubectl logs -n trivy-operator -l app.kubernetes.io/name=trivy-operator --tail=100
```

**Self-check:** `kubectl get vulnerabilityreport -A` returns reports for scanned images.

**Ponytail:** Scope ceiling — Trivy Operator install and report verification. Add air-gapped DB mirror, automated remediation, and admission control integration when those patterns are used.
