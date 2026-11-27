# Management Cluster Disaster Recovery

## A. Purpose and scope

Recovery procedure for the management cluster: Rancher, Argo CD, Keycloak, GitLab, Harbor, Vault, and the platform services that run on it.

This is step 3 of the recovery order defined in `lifecycle/disaster-recovery/index.md` — it runs after Vault and Identity are restored, before application clusters.

## B. Prerequisites

| Prerequisite | Source |
|--------------|--------|
| Vault unsealed and readable | `secrets-management/vault/recovery/restore.md` |
| Identity (Keycloak) restored | `management-cluster/keycloak/keycloak.md` |
| GitLab repository accessible | `lifecycle/backup/backup-and-dr.md` §GitLab |
| Object storage (Ceph RGW) available | `storage/ceph/cephadm-deployment.md` §Recovery |

## C. Recovery order within the management cluster

1. **Vault** — already restored (step 1 of overall order)
2. **Keycloak** — already restored (step 2 of overall order)
3. **Rancher** — restore from Velero backup, then re-register clusters
4. **Argo CD** — restore from Git + DB, then sync applications
5. **Harbor** — restore DB and registry storage
6. **Nexus** — restore task + DB
7. **Platform services** — Argo CD sync from GitLab

## D. Rancher recovery

```bash
# 1. Restore Rancher from Velero
velero restore create rancher-restore --from-backup rancher-<date>

# 2. Verify Rancher is running
kubectl -n cattle-system get deployment rancher
kubectl -n cattle-system rollout status deployment/rancher

# 3. Re-register management clusters
# Generate new cluster registration tokens in Rancher UI
# Apply the registration manifests to each managed cluster

# 4. Verify fleet is reconciling
kubectl -n cattle-fleet-system get deployment fleet-controller
```

## E. Argo CD recovery

```bash
# 1. Restore Argo CD from Velero
velero restore create argocd-restore --from-backup argocd-<date>

# 2. Verify Argo CD is running
kubectl -n argocd get deployment argocd-server
kubectl -n argocd rollout status deployment/argocd-server

# 3. Re-sync all applications from GitLab
argocd app sync <app-name>
# or sync all:
argocd app list | awk 'NR>1 {print $1}' | xargs -I {} argocd app sync {}
```

## F. Harbor recovery

```bash
# 1. Restore Harbor database
kubectl -n harbor exec deploy/harbor-core -- pg_dump -U postgres \
  -f /tmp/harbor-backup-$(date +%F).sql

# 2. Restore registry storage from object storage
# Copy registry data from RGW bucket back to Harbor PVC

# 3. Restart Harbor
kubectl -n harbor rollout restart deployment/harbor-core
kubectl -n harbor rollout restart deployment/harbor-registry
```

## G. Verification

```bash
# All management cluster pods running
kubectl get pods -A | grep -v Running | grep -v Completed

# Rancher API reachable
curl -sf https://<rancher-url>/v3/ && echo "OK"

# Argo CD reachable
curl -sf https://<argocd-url>/api/version && echo "OK"

# Harbor reachable
curl -sf https://<harbor-url>/api/v2.0/ping && echo "OK"

# Applications synced
argocd app list
```

## H. Cross-references

- `lifecycle/disaster-recovery/index.md` — Recovery order and scenario index
- `lifecycle/backup/backup-and-dr.md` — Backup mechanics and RPO/RTO
- `management-cluster/rancher/rancher.md` — Rancher deployment
- `service-mesh/evaluation.md` — Service mesh context for Argo CD
