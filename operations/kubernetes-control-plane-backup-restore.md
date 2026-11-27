# Section 4: K8s Control Plane Backup & Restore

## etcd Snapshot Strategy

etcd is the key-value store for all Kubernetes cluster state. Regular snapshots are the foundation of control-plane recoverability.

### Snapshot Frequency

| Trigger | Frequency | Retention | Off-site Copy |
|---|---|---|---|
| Scheduled (cron) | Every 4–6 hours | 72h (3 days) | Yes |
| Pre-change | Immediately before any control-plane change | Indefinite | Yes |
| Manual (before upgrade) | On-demand | Indefinite | Yes |

> **Note**: etcd snapshot timing should avoid compaction window minimum. Taking snapshots too frequently risks including overlapping WAL segments; too infrequently risks losing recent state. A 4–6 hour cadence is the recommended default for most clusters.

### Snapshot Commands (etcdctl v3)

```bash
# Automated snapshot (example cron job command)
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db

# Verify snapshot integrity
ETCDCTL_API=3 etcdctl \
  --write-out=table \
  snapshot status /backup/etcd-snapshot-*.db
```

### Expected Output — Verified Snapshot

```
$ ETCDCTL_API=3 etcdctl snapshot status /backup/etcd-snapshot-2026-11-25-020000.db
+----------------------+----------+-----------+-------------+
| MOD-REV              | TEMP-ID  | INDEX | DB SIZE |
+----------------------+----------+-----------+-------------+
| 1572347234567890   | 9876543210 | 1572347200 | 107374182400 |
+----------------------+----------+-----------+-------------+
```

A valid snapshot shows `MOD-REV`, `INDEX`, and `DB SIZE` all populated. If any field is missing, the snapshot is corrupt and should be discarded.

### Snapshot Encryption & Secure Storage

etcd snapshots contain unencrypted cluster state (secrets, certificates, IP addresses). At rest, protect snapshot files:

- **Encrypt snapshots at rest** using filesystem-level encryption (e.g., encrypted Ceph RGW, AWS S3 SSE, or disk encryption).
- **Off-cluster/off-site copy**: Copy every snapshot to a separate site or storage system. Use `aws s3 cp`, `gsutil cp`, or `rbd mirror` depending on backend.
- **Never store snapshots on the same etcd nodes** — a node loss also loses the snapshot.
- **Retention policy**: Keep at least 3–5 recent snapshots on-site; off-site copy should retain per policy (e.g., 30 days daily, 90 days weekly).

### Off-Cluster / Off-Site Copy Workflow

```bash
# After snapshot save, copy to off-site RGW
aws s3 cp /backup/etcd-snapshot-*.db s3://backups/etcd/ \
  --endpoint-url https://rgw.internal \
  --sse AES256
```

- Use lifecycle policies on the object store to manage retention.
- Verify the copied object exists and is readable before discarding the local copy.

## K8s PKI / Certificates

The control plane depends on TLS certificates for component communication. These must be included in any etcd backup since etcd stores the CA and server certificates.

### Certificates to Back Up

| Certificate | Stored In | Purpose |
|---|---|---|
| `ca.crt` | `/etc/kubernetes/pki/etcd/` | etcd CA for snapshot verification |
| `etcd/ca.crt` / `etcd/ca.key` | etcd data directory | TLS for etcd client communication |
| `etcd/server.crt` / `etcd/server.key` | etcd data directory | Server TLS for etcd |
| `front-proxy-ca.crt` / `front-proxy-ca.key` | `/etc/kubernetes/pki/` | Front-proxy TLS |
| `sa.key` / `sa.pub` | `/etc/kubernetes/pki/` | Service Account key pair |

### Certificate Renewal / Rotate

- Certificates have expiration dates (typically 1 year). Rotate before expiry.
- After rotation, re-backup etcd to include new certificates.
- If using cert-manager, certificate renewal is automated; still verify etcd snapshot includes the new certs.

## Control-Plane Recovery Ordering

Restoring the control plane requires a strict ordering to avoid split-brain or etcd corruption.

### Recovery Sequence

1. **Confirm etcd is stopped** on all control plane nodes.
2. **Clear existing etcd data** on the node being restored: `rm -rf /var/lib/etcd/member`.
3. **Restore etcd from snapshot** on the first control plane node:
   ```bash
   ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd-snapshot-<timestamp>.db \
     --name <node-name> \
     --initial-cluster <node1>=https://<ip1>:2380,<node2>=https://<ip2>:2380,<node3>=https://<ip3>:2380 \
     --initial-cluster-token etcd-cluster \
     --initial-advertise-peer-urls https://<this-node-ip>:2380
   ```
4. **Start etcd** on the first node: `systemctl start etcd`.
5. **Verify etcd health** on the first node before touching others:
   ```bash
   ETCDCTL_API=3 etcdctl endpoint health --cluster
   ```
6. **Join remaining control plane nodes** to the new etcd cluster (stop etcd, start etcd, verify).
7. **Restart kube-apiserver, kube-scheduler, kube-controller-manager** on all nodes.
8. **Verify cluster state**: `kubectl get nodes`, `kubectl get pods -A`.

### Warnings — Restoring etcd into Existing/Partially Recovered Cluster

| Warning | Risk |
|---|---|
| **Do NOT restore a snapshot over existing etcd data** without first stopping etcd and clearing the member directory. Overwriting live etcd state with an older snapshot can cause data loss and split-brain. | Permanent cluster state corruption; etcd may refuse to start; divergent cluster state. |
| **Do not restore etcd snapshots from a different cluster** — etcd member IDs and cluster tokens are cluster-specific. | Cross-cluster contamination; etcd member ID conflict; unpredictable behavior. |
| **Do not skip the `initial-cluster-token` check** if the cluster was recreated. | If the token mismatches, etcd will reject the new member; if it matches without intent, split-brain risk. |
| **After restore, always verify `etcdctl member list`** and confirm only the expected members are present. | Hidden stale members can cause quorum disputes. |

## Restore Prerequisites & Version Compatibility

| Prerequisite | Requirement |
|---|---|
| **etcdctl version must match etcd major version** | etcdctl v3.x works with etcd v3.x. Using etcdctl v3.5 with etcd v3.4 may fail on newer features. |
| **Snapshot format compatibility** | Snapshots taken with etcd v3.5+ are not compatible with etcd v3.4 restore. Restore on the same major version or newer. |
| **Etcd data directory must be writable** | The restore process writes to `/var/lib/etcd/member/`. Ensure permissions and sufficient disk space. |
| **API server reachable** (partial restore only) | If restoring etcd while API server is running, the API server must be able to contact the etcd cluster being restored. |
| **Backup validation** | Verify snapshot integrity (`snapshot status`) before starting restore. A corrupt snapshot yields a broken cluster. |

## Post-Restore Validation

After control-plane restore, run the following checks:

```bash
# etcd health
ETCDCTL_API=3 etcdctl endpoint health --cluster

# Cluster members
ETCDCTL_API=3 etcdctl member list -w table

# Kubernetes API accessibility
kubectl get nodes

# Core resources
kubectl get pods -A

# Control-plane components
kubectl get deployment -n kube-system etcd kube-apiserver kube-scheduler kube-controller-manager

# DNS resolution
kubectl get svc -n kube-system

# Verify etcd index consistency (optional)
ETCDCTL_API=3 etcdctl endpoint status -w table
```

All checks should pass without manual intervention. If any check fails, consult the failure scenarios below before proceeding.

## Failure Scenarios & Safe Recovery Workflow

| Failure | Symptom | Recovery Workflow |
|---|---|---|
| **Corrupt snapshot** | `snapshot status` fails; `etcdctl snapshot restore` aborts | Discard the corrupt snapshot. Use the previous snapshot in the retention window. Verify the remaining snapshots with `snapshot status`. |
| **Etcd version mismatch** | `etcdctl restore` fails with "snapshot format incompatible" | Restore on a node running the same etcd major version that created the snapshot. Upgrade etcd first, then restore. |
| **Split-brain after partial restore** | etcd member list shows unexpected members; quorum lost | Stop etcd on all nodes. Clear all member data. Restore from a single known-good snapshot on one node. Join remaining nodes in order. |
| **Disk full during restore** | Restore aborts mid-way; etcd data directory partially written | Free disk space. Retry restore. Do not resume from mid-point — re-run the full `snapshot restore`. |
| **Oldest snapshot used** | Cluster rolls back to state from several hours ago; recent resources lost | This is expected behavior. Restore a more recent snapshot from the retention window. If no recent snapshot is available, accept the data loss window and investigate why snapshots failed. |

## Safe Recovery Workflow Summary

1. **Verify snapshot integrity** with `etcdctl snapshot status` before restore.
2. **Stop etcd** on all control plane nodes.
3. **Clear etcd data** (`rm -rf /var/lib/etcd/member`) on the target node.
4. **Restore from snapshot** using `etcdctl snapshot restore` with correct `--name`, `--initial-cluster`, and `--initial-cluster-token`.
5. **Start etcd** and verify endpoint health.
6. **Join remaining nodes** one at a time.
7. **Restart control-plane components** (API server, scheduler, controller manager).
8. **Validate cluster state** with `kubectl get nodes` and `kubectl get pods -A`.
9. **Record the RTO** (restore time) and update runbook if the actual RTO differs from the target.

*Do NOT execute snapshot or restore against a live cluster. These commands are for documented reference only.*

---
*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*