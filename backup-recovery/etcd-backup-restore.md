# etcd Backup and Restore

## Overview

etcd is the key-value store for Kubernetes cluster state. Regular backups are essential for disaster recovery.

## Backup

### Automated Backup (CronJob)

```yaml
# etcd-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: etcd-backup
          containers:
          - name: etcd-backup
            image: harbor.internal/bitnami/etcd:3.6.15
            command:
            - /bin/bash
            - -c
            - |
              ETCDCTL_API=3 etcdctl \
                --endpoints=https://127.0.0.1:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db
              # Upload to Ceph RGW
              aws s3 cp /backup/etcd-snapshot-*.db s3://backups/etcd/ --endpoint-url https://rgw.internal
          volumeMounts:
          - name: etcd-certs
            mountPath: /etc/kubernetes/pki/etcd
            readOnly: true
          - name: backup
            mountPath: /backup
          - name: aws-credentials
            mountPath: /root/.aws
            readOnly: true
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd
          - name: backup
            emptyDir: {}
          - name: aws-credentials
            secret:
              secretName: rgw-credentials
      restartPolicy: OnFailure
```

### Manual Backup

```bash
# On control plane node
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db

# Verify
ETCDCTL_API=3 etcdctl --write-out=table snapshot status /backup/etcd-snapshot-*.db
```

### Backup Retention

| Schedule | Retention | Offsite Copy |
|---|---|---|
| Daily | 30 days | Yes (Ceph RGW) |
| Pre-change | Until next successful | Yes |

## Restore

### Prerequisites

- etcd cluster stopped
- Valid snapshot file
- etcd certificates available

### Restore Procedure

```bash
# 1. Stop etcd on all control plane nodes
systemctl stop etcd

# 2. Clear etcd data directory
rm -rf /var/lib/etcd/member

# 3. Restore from snapshot
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot restore /backup/etcd-snapshot-<timestamp>.db \
  --name=<node-name> \
  --initial-cluster=<node1>=https://<ip1>:2380,<node2>=https://<ip2>:2380,<node3>=https://<ip3>:2380 \
  --initial-cluster-token=etcd-cluster \
  --initial-advertise-peer-urls=https://<this-node-ip>:2380

# 4. Start etcd
systemctl start etcd

# 4. Verify
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health --cluster
```

### Multi-Node Restore

1. Restore on first control plane node
2. Start etcd on first node
3. Join remaining nodes:
   ```bash
   # On each remaining control plane node
   systemctl stop etcd
   rm -rf /var/lib/etcd/member
   systemctl start etcd
   ```
3. Verify cluster health:
   ```bash
   etcdctl endpoint health --cluster
   etcdctl member list
   ```

## Validation

```bash
# Check etcd health
kubectl -n kube-system exec etcd-<node> -- etcdctl endpoint health --cluster

# Check cluster state
kubectl get nodes
kubectl get pods -A

# Verify key resources
kubectl get ns,deploy,svc,pvc -A
```

## Automation

The backup CronJob runs daily at 2 AM. Manual restore is a manual process requiring coordination.

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*
