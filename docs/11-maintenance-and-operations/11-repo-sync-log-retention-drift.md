# 11 · Repo Sync, Log Retention, Config Drift

## Purpose and scope
Repository synchronization, log retention, configuration drift detection.

## Repository synchronization
- Harbor/Nexus/GitLab mirrors synced from upstream (connected) or staged (air-gapped)
- Sync schedules monitored; failures alerted
- Integrity verification: checksums, Cosign signatures, SBOM

## Log retention
- Loki/Fluent Bit: retention policies configured; old logs pruned
- Prometheus: retention period configured; remote write for long-term
- Audit logs: retained separately and longer than application logs
- Log shipping off-host immediately; redacted in collector

## Configuration drift
- Nightly drift job compares live state with Git
- Drift reported, never silently fixed (except by designated owner: Argo CD for declared state, Ansible for node state)
- Drift report older than 24 hours = incident
- Drift report names object, owner, expected value

## Implementation
```bash
# Drift detection
kubectl diff -f <manifest>
argocd app diff <application>

# Log retention check
kubectl get loki -A
kubectl get prometheus -A

# Repository sync
skopeo inspect docker://harbor.internal/
helm repo list
```

## Validation
- Repositories synced; artifacts integrity verified
- Log retention policies enforced; no unexpected log growth
- No configuration drift; drift reports current (< 24 hours)

## Related
- [03 · Repository & Registry Management (3.7 Validation & Operations)](../03-repository-registry/3.7-validation-operations.md)
- [06 · Kubernetes Infrastructure (6.14 Policies, Auditing & Deployment Governance)](../06-kubernetes-infrastructure/6.15-deployment-governance-and-auditing.md)
