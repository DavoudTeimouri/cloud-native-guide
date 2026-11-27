# Rancher Validation and Troubleshooting

## A. Cluster Health Checks

### Rancher Server Health

```bash
# Check Rancher pods status
kubectl -n cattle-system get pods

# Verify Rancher API endpoint
curl -k https://rancher.internal/v3/health

# Check Rancher API via CLI
curl -sk -u "$RANCHER_TOKEN:$RANCHER_TOKEN" \
  https://rancher.internal/v3/clusters | jq '.data[] | {name, state}'
```

**Expected:** `state: "active"` for all clusters, healthy pod counts matching the deployment replicas.

### Management Cluster Node Health

```bash
# kubespray-built management cluster node status
kubectl get nodes -o wide

# Verify etcd endpoints are responsive
kubectl -n cattle-system exec deployment/rancher -- curl -sk https://127.0.0.1:2379/health
```

### etcd Cluster Health

```bash
# etcd snapshot and health check
kubectl -n cattle-system exec -it $(kubectl -n cattle-system get pods -l app=etcd -o jsonpath='{.items[0].metadata.name}') -- etcdctl endpoint health

# etcd snapshot management
kubectl -n cattle-system exec -it $(kubectl -n cattle-system get pods -l app=etcd -o jsonpath='{.items[0].metadata.name}') -- etcdctl snapshot save /tmp/etcd-snapshot.db --cluster-id=<cluster-id>

# Verify etcd backup integrity
etcdctl snapshot restore /tmp/etcd-snapshot.db --with-revision=<revision>
etcdctl snapshot status /tmp/etcd-snapshot.db
```

## B. Application Health

### Workload and Cluster Health

```bash
# Check all cluster resources
kubectl get management-cluster -A

# Application cluster status via Rancher API
curl -sk -u "$RANCHER_TOKEN:$RANCHER_TOKEN" \
  https://rancher.internal/v3/clusters | jq '.data[] | {name, state, nodes}'

# Fleet application health
kubectl -n fleet-default get applications -A

# Check fleet pipeline status
kubectl -n cattle-fleet-system get pipelines -A
```

### Keycloak OIDC Health

```bash
# Keycloak pod status
kubectl -n keycloak get pods

# Keycloak health check
curl -k https://keycloak.internal/realms/platform/status

# Rancher OIDC configuration validation
kubectl -n cattle-system describe secret rancher-oidc-config 2>/dev/null || echo "OIDC config not found via secret"
```

## C. etcd Backup Validation

### Automated Backup Workflow

```bash
# Trigger etcd backup
BACKUP_DIR=/backup/etcd
TIMESTAMP=$(date +%Y%m%d%H%M%S)
SNAPSHOT_NAME="etcd-backup-${TIMESTAMP}.db"

kubectl -n cattle-system exec -it $(kubectl -n cattle-system get pods -l app=etcd -o jsonpath='{.items[0].metadata.name}') \
  -- etcdctl snapshot save ${BACKUP_DIR}/${SNAPSHOT_NAME} --data-dir=/var/lib/etcd

# Validate backup against source
etcdctl snapshot restore ${BACKUP_DIR}/${SNAPSHOT_NAME} --name=restored-test --with-revision=$(etcdctl endpoint status -w table | grep revision | tail -1 | awk '{print $3}')
etcdctl snapshot status ${BACKUP_DIR}/${SNAPSHOT_NAME}

# Clean up old backups (keep last 7 days)
find ${BACKUP_DIR} -name "etcd-backup-*.db" -mtime +7 -delete
```

### Backup Verification Checklist

- [ ] etcd snapshot created successfully without errors
- [ ] Snapshot restoration test performed in isolated environment
- [ ] Restoration produces cluster with matching etcd revision
- [ ] Backup artifacts stored in immutable location
- [ ] Backup schedule documented and tested quarterly
- [ ] etcd defragmentation schedule recorded
- [ ] Backup size and retention policy reviewed monthly

## D. Troubleshooting Common Issues

### Rancher UI Not Reachable

| Symptom | Cause | Remedy |
|---|---|---|
| `curl -k https://rancher.internal/v3/health` times out | Ingress not deployed / TLS certificate expired | `kubectl -n cattle-system get ingress`, check cert-manager certificates |
| 502 Bad Gateway from ingress | Rancher pod not healthy | `kubectl -n cattle-system rollout status deployment/rancher`, restart if stuck |
| UI loads but components fail | OIDC misconfiguration | Verify Keycloak client settings, check Rancher global OIDC config |

### Cluster Registration Failures

| Symptom | Cause | Remedy |
|---|---|---|
| Agent pod stuck in `Pending` | Target cluster resources exhausted | Scale up target cluster nodes, check resource quotas |
| Registration token expired | Token TTL exceeded | Generate new token: `rancher cluster-token create <name>` |
| Cluster shows `provisioning` status | Network connectivity issues | Verify firewall rules, ensure Rancher can reach cluster API endpoint |

### Fleet GitOps Not Syncing

| Symptom | Cause | Remedy |
|---|---|---|
| Applications stuck in `Pending` | Git repository inaccessible | `helm repo update`, verify Git remote URL, check SSH keys |
| Pipeline jobs failing | Fleet controller resource issue | `kubectl -n cattle-fleet-system rollout restart deployment/fleet-controller` |
| Drift detected between Git and cluster | Manual changes outside Git | Run `kubectl apply -f fleet/cluster-baseline.yaml`, investigate drift causes |

### etcd Performance Degradation

| Symptom | Cause | Remedy |
|---|---|---|
| High etcd CPU utilization | Excessive watch pressure | Review fleet application sync frequency, reduce watch batch sizes |
| etcd member lagging | Network partition or slow disks | Check etcd member health, upgrade storage class, run etcd defrag |
| Frequent leader elections | Disk latency or split brain | Verify etcd storage performance, check for network instability |

## E. Operational Checklists

### Daily Operations

- [ ] Verify Rancher UI reachable via `curl -k https://rancher.internal/v3/health`
- [ ] Check Rancher pod status: `kubectl -n cattle-system get pods`
- [ ] Confirm cluster agents connected and visible in Rancher UI
- [ ] Review fleet application sync status
- [ ] Check for any alert notifications in Rancher

### Weekly Operations

- [ ] Validate etcd backup creation and integrity
- [ ] Review etcd snapshot retention and clean old backups
- [ ] Inspect logs for recurring warnings or errors
- [ ] Verify Keycloak OIDC token refresh functioning
- [ ] Check node resource utilization on management cluster

### Monthly Operations

- [ ] Perform etcd restoration test in staging environment
- [ ] Review and update registration token TTL settings
- [ ] Audit RBAC permissions across clusters and projects
- [ ] Update Rancher Helm chart to latest stable version
- [ ] Verify backup storage costs and retention compliance
- [ ] Test disaster recovery procedure end-to-end

### Quarterly Operations

- [ ] Full disaster recovery drill: backup → restore → validation
- [ ] Upgrade Rancher to next supported minor version
- [ ] Re-rotate all secrets (Rancher bootstrap password, OIDC client secrets)
- [ ] Review and update infrastructure as code templates
- [ ] Assess cluster sizing against current workload demands
- [ ] Security scan of container images and cluster dependencies

## F. Recovery Procedure

### Rancher Cluster Loss

1. Re-deploy Rancher on new dedicated management cluster (Kubespray + Helm)
2. Restore etcd from latest validated backup
3. Re-import all managed clusters using registration tokens
4. Re-configure Keycloak OIDC integration
5. Restore Fleet Git repositories from Git hosting backup
6. Sync applications via Argo CD and Fleet

### Single Cluster Failure

1. For application cluster: use cluster delete/re-create flow in Rancher
2. For management cluster: redeploy from infrastructure-as-code templates
3. Verify etcd data consistency post-recovery
4. Validate all cross-cluster references and fleet pipelines

---
**File**: `management-cluster/rancher/validation-and-troubleshooting.md`
**Created**: 2026-11-26
**DevOps Automator**: infrastructure automation and Rancher operations specialist

[Previous step](../../kubespray/kubespray-deployment.md) | [Next step](../../network-matrix/external-load-balancer.md)