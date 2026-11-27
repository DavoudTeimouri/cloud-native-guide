# etcd Backup Automation



## A. Scheduled Snapshots



etcd snapshots are **separate from Velero**. Velero does not back up etcd, and a cluster restore without an etcd snapshot restores workloads onto a control plane with no cluster state.



### Snapshot cadence



```bash

# Take a tiled snapshot and save it with a date-stamped filename

kubectl -n kube-system exec etcd-<node> -- etcdctl \

  --cacert=/etc/kubernetes/pki/etcd/ca.crt \

  --cert=/etc/kubernetes/pki/etcd/server.crt \

  --key=/etc/kubernetes/pki/etcd/server.key \

  snapshot save /var/lib/etcd/snapshot-$(date +%F).db

```



### Snapshot frequency



| Metric | Target | Method |

|---|---|---|

| Snapshot interval | Every 5 minutes | Cron job on control-plane nodes |

| WAL archival | Not continuous (air-gapped) | WAL retained on-node; shipped with each snapshot to off-site storage |

| RPO | ≤ 5 min | Bounded by the 5-minute snapshot interval; continuous WAL push to an external store is not possible air-gapped |



### Snapshot retention on-node



- Keep the **7 most recent** local snapshots per node

- Rotate snapshots off-node daily (push to off-site storage)

- Oldest local snapshot automatically pruned after 7



## B. Off-site Backup Storage



Each etcd snapshot must be copied to off-site storage within the same cadence. A backup on the same cluster does not survive a full region loss.



### Off-site copy



```bash

# Copy to object storage (e.g., Ceph RGW, S3, GCS)

gsutil cp /var/lib/etcd/snapshot-$(date +%F).db gs://etcd-backups/snapshot-$(date +%F).db



# Or with AWS CLI

aws s3 cp /var/lib/etcd/snapshot-$(date +%F).db s3://etcd-backups/snapshot-$(date +%F).db



# Or with mc (MinIO client)

mc cp /var/lib/etcd/snapshot-$(date +%F).db etcd-backups/snapshot-$(date +%F).db

```



### Off-site storage layout



```

etcd-backups/

├── snapshot-2026-11-20.db

├── snapshot-2026-11-21.db

├── snapshot-2026-11-22.db

├── snapshot-2026-11-23.db

├── snapshot-2026-11-24.db

├── snapshot-2026-11-25.db

├── snapshot-2026-11-26.db

└── .hashes/          # SHA256 checksums, one per line matching filenames

```



### Off-site retention policy



| Tier | Retention | Description |

|---|---|---|

| Rolling local | 7 days | 7 most recent snapshots per node |

| Archived off-site | 30 days | Copied from on-node to object storage |

| Long-term archive | 90 days | Copied to cold storage (Glacier/Deepfreeze) |

| Immutable | Indefinite | Object-lock or WORM storage for compliance |



### Off-site copy verification



After each copy, verify integrity:



```bash

# Generate SHA256 on source

sha256sum /var/lib/etcd/snapshot-$(date +%F).db > /tmp/snapshot-$(date +%F).sha256



# Verify on destination

gsutil hash -c gs://etcd-backups/snapshot-$(date +%F).db  # or aws s3api head-object --expected

```



## C. Backup Verification



A snapshot is **useless until it has been verified**. Verify **before** you need it — ideally as part of a scheduled drill.



### Check snapshot integrity



```bash

kubectl -n kube-system exec etcd-<node> -- etcdctl \

  --cacert=/etc/kubernetes/pki/etcd/ca.crt \

  --cert=/etc/kubernetes/pki/etcd/server.crt \

  --key=/etc/kubernetes/pki/etcd/server.key \

  snapshot status /var/lib/etcd/snapshot-2026-11-25.db

```



**Expected output:**



```

snapshot 2026-11-25-rev12345

endpoint http://127.0.0.1:2379

revision 12345

version 3.5.5

cluster-id 1234567890

state latest

```



**All fields must be present and `state` must be `latest`.** If `state` is `truncated` or the command fails, the snapshot is corrupted and you must fall back to an older one.



### Automated restore verification (scheduled drill)



1. Spin up a **throwaway control-plane node** (or use an existing offline node)

2. Restore the latest snapshot to its `/var/lib/etcd`

3. Start etcd and wait for it to reach `healthy` in `etcdctl endpoint health --cluster`

4. Run a **smoke query**: `kubectl get nodes` and `kubectl get pods -A` — etcd itself must be reachable

5. **Record the measured RTO** from snapshot save to verified healthy member

6. **Alert if the restore fails or exceeds the RTO budget** (30 min). A backup pipeline with no automated restore test is an incident waiting to happen.



### Verification schedule



- **Daily**: Snapshot integrity check (`etcdctl snapshot status`) — automated, no cluster impact

- **Weekly**: Full restore drill on a throwaway node — measure RTO, alert on failure

- **Monthly**: Restore to a fresh cluster, verify API server functionality end-to-end

- **Quarterly**: Cross-region restore drill — verify off-site backups are restorable



## D. Backup Retention Policies



### Retention summary



| Tier | Duration | Storage | Purge method |

|---|---|---|---|

| On-node rolling | 7 days | Local disk `/var/lib/etcd/` | `etcdctl snapshot prune --revision=<N>` or rm |

| Off-site archive | 30 days | Object storage (Ceph RGW/S3/GCS) | Remove object version |

| Long-term cold | 90 days | Cold storage (Glacier/Deepfreeze) | Delete after 90 days |

| Immutable/Compliance | Indefinite | WORM/object-lock storage | Never purge without approval |



### Purge procedure



```bash

# Prune local etcd snapshots keeping last 7 revisions

etcdctl snapshot prune --revision=$(etcdctl endpoint status --write-out=json | jq -r '.revision') --prev-n 7



# Remove off-site snapshot older than 30 days

gsutil rm gs://etcd-backups/snapshot-$(date -d '30 days ago' +%F).db



# Remove off-site snapshot older than 90 days

aws s3 rm s3://etcd-backups/snapshot-$(date -d '90 days ago' +%F).db

```



### Retention enforcement



- **Automated**: Cron job runs daily at 02:00 UTC to prune local snapshots and remove off-site objects older than 30 days

- **Manual review**: Monthly audit of retention compliance; any deviations flagged to the DBRE on-call

- **Immutable backup**: If object storage supports object-lock, enable it so no actor (including root) can delete backups within the retention window without explicit override



## E. Automated Restore Drill Procedures



### Daily integrity check (no-cluster-impact)



```bash

# Run on each control-plane node

kubectl -n kube-system exec etcd-<node> -- etcdctl \

  --cacert=/etc/kubernetes/pki/etcd/ca.crt \

  --cert=/etc/kubernetes/pki/etcd/server.crt \

  --key=/etc/kubernetes/pki/etcd/server.key \

  snapshot status /var/lib/etcd/snapshot-$(date -1 day +%F).db > /tmp/daily-snapshot-status-$(date +%F).txt



# Check that all snapshots from the last 7 days have `state latest`

if grep -q "state latest" /tmp/daily-snapshot-status-*.txt; then

  echo "All daily snapshots valid"

else

  echo "WARNING: Some snapshots are truncated or corrupted"

  # Alert via existing on-call channel

fi

```



### Weekly restore drill (measured RTO)



1. **Select a snapshot** from 7 days ago (oldest still retained locally)

2. **Spin up a throwaway control-plane node** (or use an existing node in a disconnected state)

3. **Clear the data directory** on the throwaway node: `rm -rf /var/lib/etcd/*`

4. **Restore the snapshot**:

   ```bash

   kubectl -n kube-system exec etcd-<node> -- etcdctl \

     --cacert=/etc/kubernetes/pki/etcd/ca.crt \

     --cert=/etc/kubernetes/pki/etcd/server.crt \

     --key=/etc/kubernetes/pki/etcd/server.key \

     snapshot restore /var/lib/etcd/snapshot-2026-11-19.db \

     --data-dir /var/lib/etcd

   ```

5. **Start etcd**: `kubectl -n kube-system start etcd-<node>`

6. **Wait for healthy quorum**:

   ```bash

   kubectl -n kube-system exec etcd-<node> -- etcdctl member list

   kubectl -n kube-system exec etcd-<node> -- etcdctl endpoint health --cluster

   ```

7. **Record the measured RTO** from snapshot save timestamp to `etcdctl endpoint health --cluster` returning healthy

8. **Run smoke verification**: `kubectl get nodes` and `kubectl get pods -A`

9. **Alert if RTO > 30 min** or restore fails — log the full output for post-drill review

10. **Reset the node** or snapshot it for future drills



### Monthly full-restore drill



1. Select a snapshot from 30 days ago

2. Restore to a **completely fresh** control-plane node (not a reused throwaway)

3. Verify the full API server is serving: `kubectl get nodes`, `kubectl get pods -A`, `kubectl get nodes -o wide`

4. Record RTO and compare against the 30-minute budget

5. If RTO exceeds budget, document the gap and plan infrastructure changes



### Cross-region restore drill (quarterly)



1. Select the most recent off-site snapshot

2. Provision a control-plane node in the disaster-recovery region

3. Copy the off-site snapshot to the DR node's local storage

4. Restore etcd from the snapshot

5. Verify API server functionality from the DR region

6. Test that workloads can start with reduced capacity (the goal is etcd recovery, not full app recovery)

7. Record RTO and verify it meets the target; document any gaps



### Drill reporting



After every restore drill, update this file with:



- Snapshot filename used

- Measured RTO (minutes:seconds)

- Success/failure status

- Any failures and root causes

- Actions to bring RTO within budget



Append to the drill log section at the bottom of this file.
