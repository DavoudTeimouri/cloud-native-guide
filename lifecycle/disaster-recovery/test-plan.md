# Disaster Recovery Test Plan

## A. Purpose and scope

Document disaster recovery test plan: drill scenarios, success criteria, evidence collection, sign-off.

Cross-references `lifecycle/disaster-recovery/index.md`, `lifecycle/disaster-recovery/full-site-rebuild.md`, `lifecycle/backup/backup-and-dr.md`.

## B. Drill scenarios

| Scenario | Description | Frequency |
|----------|-------------|-----------|
| etcd quorum loss | Restore etcd from snapshot after quorum loss | Quarterly |
| Control plane failure | Rebuild control plane on new nodes | Semi-annually |
| Full site loss | Full site rebuild from backups | Annually |
| Storage failure | Ceph OSD loss and recovery | Quarterly |
| Application cluster loss | Restore application clusters from Velero | Semi-annually |
| Identity failure | Restore Keycloak from backup | Semi-annually |

## C. Success criteria

| Criterion | Threshold |
|-----------|-----------|
| RPO met | Data loss within RPO for all components |
| RTO met | Recovery time within RTO for all components |
| All pods running | 100% of critical workloads Running |
| All PVCs bound | 100% of PVCs Bound |
| Argo CD healthy | All applications Healthy |
| Vault unsealed | Vault unsealed and accessible |

## D. Evidence collection

```bash
# Capture etcd health
kubectl -n kube-system get pods -l component=etcd > evidence/etcd-status.txt

# Capture node status
kubectl get nodes > evidence/node-status.txt

# Capture Argo CD applications
argocd app list > evidence/argocd-apps.txt

# Capture PVC status
kubectl get pvc -A > evidence/pvc-status.txt

# Capture Ceph health
ceph health > evidence/ceph-health.txt
```

## E. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Disaster Recovery Lead | | | |
| Platform Engineering Lead | | | |
| Security Lead | | | |
| Operations Lead | | | |

## F. Cross-references

- `lifecycle/disaster-recovery/index.md` — Disaster recovery index
- `lifecycle/disaster-recovery/full-site-rebuild.md` — Full site rebuild
- `lifecycle/backup/backup-and-dr.md` — Backup architecture
