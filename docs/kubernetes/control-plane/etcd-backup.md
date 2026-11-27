# etcd Backup

## A. Purpose and scope

Document the etcd backup procedure: snapshot frequency, retention, off-node storage, verification, and restore procedure.

etcd stores all Kubernetes cluster state. Losing etcd means losing the entire cluster. Regular, verified backups are mandatory.

Cross-references `kubernetes/control-plane/index.md` §Backup, `lifecycle/backup/backup-and-dr.md` §etcd, `lifecycle/disaster-recovery/index.md` §etcd quorum lost.

## B. Backup frequency and retention

| Item | Value |
|------|-------|
| Snapshot frequency | Every 4 hours (configurable) |
| Retention | 7 daily snapshots, 4 weekly snapshots, 1 monthly snapshot |
| Off-node copy | Within 15 minutes of snapshot completion |
| Verification | Every snapshot verified with `etcdctl snapshot status` |

## C. Snapshot procedure

### 1. Take etcd snapshot

Run on one etcd member (control-plane node):

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd/snapshot-$(date +%F-%H%M).db
```

### 2. Verify snapshot

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  snapshot status /var/lib/etcd/snapshot-$(date +%F-%H%M).db \
  --write-out=table
```

Expected output shows `health: "true"`.

### 3. Copy off-node

```bash
kubectl -n kube-system cp etcd-<node>:/var/lib/etcd/snapshot-$(date +%F-%H%M).db \
  /backups/etcd/snapshot-$(date +%F-%H%M).db
```

Store off-node in object storage (Ceph RGW) or offline media.

## D. Restore procedure

### 1. Stop etcd on the affected member

```bash
# Delete the static pod manifest to stop etcd
rm /etc/kubernetes/manifests/etcd.yaml
# Wait for the pod to terminate
sleep 30
```

### 2. Restore from snapshot

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

### 3. Restart etcd

```bash
# Recreate the static pod manifest
cp /etc/kubernetes/manifests/etcd.yaml.bak /etc/kubernetes/manifests/etcd.yaml
# kubelet automatically picks up the change
```

### 4. Verify restore

```bash
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster

kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  member list
```

All members must report `healthy`.

## E. Retention and cleanup

```bash
# Keep 7 daily snapshots
ls -t /backups/etcd/*.db | tail -n +8 | xargs rm

# Keep 4 weekly snapshots (Sundays)
# Keep 1 monthly snapshot (1st of month)
```

## F. Automation

The snapshot procedure is automated via a CronJob or systemd timer on the Automation Management Server:

```yaml
# Example CronJob (applied by Argo CD)
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-snapshot
  namespace: kube-system
spec:
  schedule: "0 */4 * * *"  # Every 4 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: etcd-snapshot
            image: harbor.internal/platform/kubespray:v2.32.0
            command:
            - /bin/sh
            - -c
            - |
              etcdctl snapshot save /backup/snapshot-$(date +%F-%H%M).db \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key \
                --endpoints=https://127.0.0.1:2379
              etcdctl snapshot status /backup/snapshot-$(date +%F-%H%M).db
          restartPolicy: OnFailure
```

## G. Cross-references

- `kubernetes/control-plane/index.md` §Backup — etcd snapshot in control plane context
- `lifecycle/backup/backup-and-dr.md` §etcd — etcd backup in backup targets table (RPO 24h, RTO 1h)
- `lifecycle/disaster-recovery/index.md` §etcd quorum lost — restore from snapshot
- `compatibility/version-matrix.md` — etcd version 3.6.15
