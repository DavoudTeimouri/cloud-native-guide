# Full Site Rebuild

## A. Purpose and scope

Document the full site rebuild procedure: restore the entire platform from backups into a new environment, following the defined recovery order.

This is the most severe disaster scenario — every component must be restored in the correct dependency order.

Cross-references `lifecycle/disaster-recovery/index.md` §Recovery order and all individual runbooks.

## B. Prerequisites

| Prerequisite | Source |
|--------------|--------|
| Vault raft snapshot available | `lifecycle/backup/backup-and-dr.md` §Vault |
| Unseal keys (3 of 5 shares) | Offline storage, key holders |
| GitLab repository accessible (replicated + off-site) | `lifecycle/backup/backup-and-dr.md` §GitLab |
| Object storage (Ceph RGW) available | `storage/ceph/cephadm-deployment.md` §Recovery |
| New hardware ready (bare metal or VMs) | `automation/terraform/vsphere.md` |
| OS images mirrored to internal registry | `offline-artifacts/artifact-matrix.md` |
| Kubespray checkout mirrored internally | `kubespray/multi-version-support.md` |

## C. Rebuild order (non-negotiable)

Each step depends on the one before it. Do not skip steps.

| Step | Component | Runbook | Depends on |
|------|-----------|---------|------------|
| 1 | Vault | `secrets-management/vault/recovery/restore.md` | — |
| 2 | Identity (Keycloak) | `management-cluster/keycloak/keycloak.md` | Vault |
| 3 | Management cluster | `lifecycle/disaster-recovery/management-cluster.md` | Vault, Identity |
| 4 | Application clusters | `lifecycle/disaster-recovery/application-cluster.md` | Management cluster |
| 5 | Workload data (Ceph pools) | `storage/ceph/cephadm-deployment.md` §Recovery | Application clusters |

## D. Step-by-step procedure

### Step 1: Rebuild Vault

1. Provision new Vault hosts (Terraform + Ansible)
2. Install Vault from internal registry
3. Unseal Vault with 3 of 5 shares
4. Restore from raft snapshot
5. Verify: `vault status` shows unsealed, `vault kv list secret/platform/` works

### Step 2: Rebuild Identity (Keycloak)

1. Provision Keycloak hosts
2. Install Keycloak from internal registry
3. Configure Keycloak OIDC clients (from Vault secrets)
4. Import realm configuration from backup
5. Verify: `curl https://keycloak.internal/realms/platform/.well-known/openid-configuration` returns valid JSON

### Step 3: Rebuild Management Cluster

1. Provision management cluster nodes (3 control-plane + 3 infra workers)
2. Install OS from internal mirror
3. Deploy Kubespray cluster (release-2.32)
4. Restore Rancher from Velero backup
5. Restore Argo CD from Git + DB
6. Restore Harbor, Nexus, GitLab
7. Verify: `kubectl get nodes` shows all Ready, Rancher API reachable

### Step 4: Rebuild Application Clusters

1. Provision application cluster nodes
2. Install OS from internal mirror
3. Deploy Kubespray cluster (release-2.32)
4. Register clusters with Rancher (generate new registration tokens)
5. Restore from Velero backup
6. Reattach Ceph CSI volumes
7. Let Argo CD reconcile workloads
8. Verify: `kubectl get pods -A` shows all Running, Argo CD applications Healthy

### Step 5: Restore Workload Data

1. Verify Ceph cluster health: `ceph health` shows HEALTH_OK
2. Restore Ceph pools from backup (RBD import, CephFS snapshot restore)
3. Verify PVCs bind successfully
4. Verify application data is accessible

## E. Verification checklist

```bash
# 1. Vault
vault status | grep "Sealed.*false"
vault kv list secret/platform/

# 2. Identity
curl -sf https://keycloak.internal/realms/platform/.well-known/openid-configuration

# 3. Management cluster
kubectl get nodes
kubectl -n cattle-system get deployment rancher
kubectl -n argocd get deployment argocd-server

# 4. Application clusters
kubectl get pods -A | grep -v Running | grep -v Completed
kubectl get pvc -A | grep -v Bound
argocd app list | grep -v Healthy

# 5. Storage
ceph health
kubectl get pvc -A | grep -v Bound
```

## E. Rollback

A full site rebuild has no rollback — if the rebuild fails at any step, restore from the most recent backup and retry. Document the failure point and corrective action.

## F. Cross-references

- `lifecycle/disaster-recovery/index.md` — Recovery order (step 5)
- `lifecycle/backup/backup-and-dr.md` — Backup mechanics and RPO/RTO
- `secrets-management/vault/recovery/restore.md` — Vault recovery (step 1)
- `management-cluster/keycloak/keycloak.md` — Identity recovery (step 2)
- `lifecycle/disaster-recovery/management-cluster.md` — Management cluster recovery (step 3)
- `lifecycle/disaster-recovery/application-cluster.md` — Application cluster recovery (step 4)
- `storage/ceph/cephadm-deployment.md` §Recovery — Ceph recovery (step 5)
