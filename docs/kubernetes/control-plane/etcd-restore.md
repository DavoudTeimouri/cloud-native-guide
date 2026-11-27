# etcd Restore

## A. Purpose and scope

Document etcd restore procedure: snapshot restore, quorum recovery, member replacement, validation.

etcd stores all Kubernetes cluster state. Restoring etcd recovers the cluster to the point of the last snapshot.

Cross-references `kubernetes/control-plane/index.md` §Backup, `kubernetes/control-plane/etcd-backup.md`, `lifecycle/disaster-recovery/index.md` §etcd quorum lost, `lifecycle/backup/backup-and-dr.md` §etcd.

## B. Prerequisites

| Prerequisite | Source |
|--------------|--------|
| etcd snapshot available | `kubernetes/control-plane/etcd-backup.md` |
| etcd binary on the node | Installed by Kubespray |
| etcd certificates | /etc/kubernetes/pki/etcd/ |
| etcd stopped on the target node | Static pod removed |

## C. Restore procedure

### 1. Stop etcd on the affected member

```bash
# Delete the static pod manifest to stop etcd
rm /etc/kubernetes/manifests/etcd.yaml

# Wait for the pod to terminate
sleep 30

# Verify etcd is stopped
kubectl -n kube-system get pods -l component=etcd --field-selector spec.nodeName=<node>
```

### 2. Back up existing data directory

```bash
# Move existing data directory aside
mv /var/lib/etcd/member /var/lib/etcd/member.backup-$(date +%F)
```

### 3. Restore from snapshot

```bash
# Copy snapshot to the node
cp /backups/etcd/snapshot-<date>.db /var/lib/etcd/snapshot-<date>.db

# Restore
etcdctl snapshot restore snapshot-<date>.db \
  --data-dir /var/lib/etcd/restored

# Replace the data directory
mv /var/lib/etcd/member /var/lib/etcd/member.old
mv /var/lib/etcd/restored/member /var/lib/etcd/member
```

### 4. Restart etcd

```bash
# Recreate the static pod manifest
kubectl -n kube-system rollout restart daemonset/etcd
# or manually recreate the static pod manifest

# Wait for etcd to start
sleep 30
```

### 5. Verify restore

```bash
# Check etcd endpoint health
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster

# Check etcd members
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  member list

# Check cluster API
kubectl get --raw='/readyz?verbose'
```

All etcd members must report `healthy`.

## D. Quorum recovery

If etcd quorum is lost (less than majority of members available):

1. Identify the member with the most recent data
2. Restore etcd on that member from snapshot
3. Start etcd on that member first (single-member cluster temporarily)
4. Add remaining members one at a time
5. Verify quorum is restored

```bash
# Add a member back to the cluster
etcdctl member add <new-member> \
  --peer-urls=https://<new-member-ip>:2380 \
  --member-zone=<zone>
```

## E. Member replacement

To replace a failed etcd member:

1. Remove the failed member from the cluster
2. Provision a new host with the same IP
3. Restore etcd from snapshot on the new host
4. Add the new host as an etcd member
5. Verify cluster health

## F. Cross-references

- `kubernetes/control-plane/etcd-backup.md` — etcd snapshot procedure
- `kubernetes/control-plane/index.md` §Backup — etcd backup in control plane context
- `kubernetes/control-plane/index.md` §Failure scenarios — etcd quorum loss
- `lifecycle/disaster-recovery/index.md` §etcd quorum lost — restore from snapshot
- `lifecycle/backup/backup-and-dr.md` §etcd — etcd backup RPO/RTO
