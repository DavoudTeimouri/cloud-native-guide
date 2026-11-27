# Rancher Cluster Lifecycle

## A. Purpose and scope

Document cluster lifecycle: registration, upgrade, decommission, backup, restore via Rancher API.

Cross-references `management-cluster/rancher/rancher.md`, `management-cluster/rancher/fleet-integration.md`, `lifecycle/disaster-recovery/management-cluster.md`.

## B. Cluster registration

New downstream clusters register with Rancher via cluster registration token:

```bash
# Generate registration token
rancher cluster-token create <cluster-name>

# Join cluster nodes
curl -sLf https://ranchermirror.internal/rancher/v3/cluster-registration-token | \
  bash -s -- --etcd --controlplane --worker
```

## C. Cluster upgrade

Upgrades follow Fleet or Rancher's built-in upgrade mechanism:

```bash
# Fleet-based upgrade (preferred)
kubectl apply -f fleet/cluster-upgrade.yaml

# Rancher API upgrade
rancher cluster upgrade <cluster-id> --kubernetes-version v1.36.5
```

## D. Cluster decommission

```bash
# Delete workloads
kubectl delete namespace -l cluster=<name>

# Drain and delete cluster via Rancher API
rancher cluster delete <cluster-id>

# Verify deletion
rancher cluster list | grep <name>
```

## E. Backup and restore

Management cluster backup follows `lifecycle/disaster-recovery/management-cluster.md`. Downstream clusters are backed up via Velero:

```bash
# Backup downstream cluster
velero backup create <cluster-name>-backup --include-namespaces all

# Restore downstream cluster
velero restore create --from-backup <cluster-name>-backup
```

## F. Cross-references

- `management-cluster/rancher/rancher.md` — Rancher deployment
- `management-cluster/rancher/fleet-integration.md` — Fleet integration
- `lifecycle/disaster-recovery/management-cluster.md` — Management cluster recovery
