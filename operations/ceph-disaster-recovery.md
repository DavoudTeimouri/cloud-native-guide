# Section 6: Ceph & Rook-Ceph Recovery

## Guiding Principles

- **Non-destructive recovery first** — Use safe read-only verification before any write or OSD replacement. Never recommend destructive Ceph commands as routine recovery.
- **Distinguish protection mechanisms** — replication, erasure coding, snapshots, clones, backups, async replication, and DR are not interchangeable. Each has distinct recovery pathways and risk profiles.
- **Backup ≠ DR** — A Ceph snapshot or RGW versioning copy protects against accidental modification, not cluster loss. Off-site copies and CRUSH map backups are required for disaster recovery.
- **Verify before act** — All recovery commands must be validated against the current cluster state (`ceph -s`, `ceph osd tree`, `ceph mon dump`) before execution.
- **Data-loss-risk operations** — Clearly identified. These require specialist review, stakeholder sign-off, and a tested rollback path.

---

## 6.1 MON Quorum & Recovery

| Scenario | Preconditions | Recovery Procedure | Validation | Data-loss Risk |
|---|---|---|---|---|
| **Single MON loss** (3-MON cluster) | 2 of 3 MONs running; cluster has quorum | `ceph mon remove <id>` on the removed mon; restart the MON service on a surviving host with proper placement | `ceph health OK`; `ceph mon dump` shows 3 mons; `ceph quorum_status` shows quorum active | None if quorum preserved |
| **Two MON losses** (3-MON cluster) | 1 of 3 MONs running; quorum lost | **Do not attempt partial recovery**. Requires restoring from a `monmap` backup saved alongside etcd/cluster backups. Restore the monmap from the most recent backup, then start remaining MONs. | `ceph mon dump` shows all expected mons; quorum active; cluster HEALTH_OK | **High** — data accessibility depends on etcd/OSD map consistency; full cluster restore may be required |
| **All MONs down** | No MONs responding; `ceph -s` stalled | Restore monmap and keyring from off-site backup: <br>`ceph-mon --restore-monmap <backup-file>` <br>Start one MON, verify it joins, then start remaining mons one at a time. | `ceph quorum_status` shows quorum; `ceph health OK`; all daemons running | **Medium** — monmap restore uses the last saved map; any OSD/CRUSH changes since the backup are lost unless also restored |
| **Rock-Ceph MON loss** | Rook-Ceph, 3 MONs deployed | `kubectl -n rook-ceph patch cephcluster/rook-ceph -p '{"spec":{"mon":{"count":3}}}'` after restoring the monmap, or use `rookadm` to re-add the MON pod. | `kubectl -n rook-ceph get pods` shows rook-ceph-mon running; `ceph -s` shows quorum | Low — Rook operator re-creates MON CRDs; data preserved in OSD map |

> ** Specialist review required **: Any MON loss below quorum (i.e., < 2 of 3 MONs active, or < 3 of 5 MONs active) requires infrastructure specialist sign-off and a documented rollback to the last known-good monmap backup.

---

## 6.2 OSD Failure & Replacement

| Scenario | Preconditions | Recovery Procedure | Validation | Data-loss Risk |
|---|---|---|---|---|
| **Single OSD failure** (3x replicated pool) | OSD down but device intact; cluster in DEGRADED state | `ceph osd out <osd-id>` (if not already out) <br>Replace the physical disk <br>`ceph osd in <osd-id>` — triggers automatic backfill | `ceph pg map <pg>` shows backfill in progress <br>`ceph -s` shows PGs recovering, no `HEALTH_WARN` after backfill completes | None — 3x replication tolerates one OSD loss; data redundancy preserved |
| **OSD with failing device** | SMART errors, I/O errors, device unresponsive | `ceph osd out <osd-id>` <br>Replace disk <br>If using LVM: `ceph orch device ls` → identify device <br>`cephadm shell -- ceph orch apply osd <host> --replace <osd-id>` <br>Or manually: create new OSD, `ceph osd in`, then `ceph osd out <old-osd-id>` | `ceph osd tree` shows new OSD active <br>`ceph -s` shows HEALTH_OK, all PGs active+clean | None if replacement follows procedure; risk if `ceph osd out` skipped — data rebalancing may not complete |
| **Multiple OSD failures** (≥ 2 OSDs) | In a 3x pool: 2 OSDs lost → data loss imminent; in a 4x pool: 2 lost → tolerable | Prioritize disk replacement <br>`ceph osd out <osd-id>` for each failed OSD <br>Replace disks <br>`ceph osd in <osd-id>` for each replaced OSD <br>Monitor backfill complete; if PGs cannot recover, specialist review required | `ceph pg status` shows all PGs active+clean <br>`ceph -s` shows HEALTH_OK | **High** — if > pool_replication_size OSDs lost, data is permanently lost. 3x pool: max 1 OSD loss. 4x pool: max 2 OSD losses. |
| **OSD full** (near-full flag) | OSD `near-full` or `full` flag set; PGs stuck in recovery | `ceph osd out <osd-id>` <br>Add replacement OSD <br>`ceph osd in <osd-id>` <br>If no hardware: rebalance pools via `ceph osd pool set <pool> size <N>` (reduce size temporarily) | `ceph -s` shows `used` < `max_osd_usage` <br>PGs return to active+clean | Medium — reducing pool size may temporarily reduce data redundancy; requires specialist review |

> ** Specialist review required **: OSD replacement on production clusters without a tested backup of the monmap/OSD map. Also required when reducing pool size below the original replication level.

---

## 6.3 PG Degraded & Inconsistent Recovery

| Scenario | Preconditions | Recovery Procedure | Validation | Data-loss Risk |
|---|---|---|---|---|
| **PG stuck in `degraded`** | PG not active+clean for > 30m; backfill not progressing | Identify the missing OSD: `ceph pg map <pg>` <br>`ceph osd dump` <br>Ensure the missing OSD is `out` or `down` <br>`ceph osd in <osd-id>` to trigger backfill | `ceph pg <pg> query` shows `active+clean` after backfill <br>`ceph -s` shows all PGs `active+clean` | None if backfill completes; risk if underlying device failure |
| **PG stuck in `inconsistent`** | PG reports inconsistent state (bitten flag); checksum mismatch detected | `ceph pg <pg> inconsistent-recover` — **requires specialist review** <br>May require restoring from a Ceph snapshot or RGW versioned copy <br>If data corruption is confirmed, restore from backup | `ceph pg <pg> query` shows consistent <br>`rados -p <pool> snap ls` to identify good snapshot | **Medium** — `inconsistent-recover` may discard local modifications; verify with specialist before running |
| **PG backfill stalled** | Backfill rate < 1 MB/s for > 15m; cluster `HEALTH_WARN` | Check OSD status: `ceph osd status` <br>Check device health: `smartctl -a /dev/<device>` <br>Check network bandwidth between OSDs <br>If device is failing, replace per Section 6.2 | `ceph -s` shows backfill progressing <br>`ceph pg <pg> backfill_status` shows 100% | None if device is healthy; risk if backfill is interrupted by further OSD loss |
| **PG out of memory** | PG recovery OOM; OSD OOM killed | Restart OSD pod/service <br>`ceph osd out <osd-id>` <br>`ceph osd in <osd-id>` to trigger re-recovery | `ceph -s` shows PGs recovering <br>`kubectl -n rook-ceph rollout status pod/<osd-pod>` | None after restart; risk if OOM has structural cause (e.g., large PG size) |

> ** Specialist review required **: `ceph pg inconsistent-recover` is a destructive operation that may discard recent writes. Must have a recent Ceph snapshot or off-site backup available. Requires stakeholder sign-off.

---

## 6.4 Pool + CRUSH Map Backup & Protection

| Protection Mechanism | What It Protects | Recovery Target | Commands / Procedure | Risk |
|---|---|---|---|---|
| **CRUSH map export** | Failure domain topology, pool CRUSH rules, device mapping | Full cluster rebuild from scratch | `ceph osd getcrushmap > /backup/crushmap-$(date +%F).monmap` <br>`crushtool -z <cwd>` to inspect | Low — export is read-only; reimport requires matching hardware topology |
| **Pool configuration backup** | Pool settings (replication size, min/max objects, CRUSH rules) | Recreate pool after cluster loss | `ceos pool export <pool-name> > /backup/pool-<name>-$(date +%F).json` <br>`ceph osd pool create <name> <pg-num> <pgp-num> <replicated|erasure_coded> <size> <min_size>` | Low — pool config is small; re-creation is deterministic if PG numbers match |
| **RGW bucket versioning** | Object overwrite protection; ransomware recovery | Restore deleted/overwritten objects | Via RGW console or `rgw` CLI; no Ceph CLI needed | Low — versioning is additive; no data loss if versions preserved |
| **RBD snapshot export** | Point-in-time block device image | Restore RBD image to prior state | `rbd snapshot create <pool>/<image>@<snapname>` <br>`rbd export <pool>/<image>@<snapname> <file>` <br>`rbd import <pool>/<image> <file>` | Low — snapshot is copy-on-write; export is read |
| **CephFS snapshot export** | Point-in-time filesystem tree | Restore directory structure | `ceph fs snapshot create cephfs <snapname>` <br>`ceph fs snapshot ruok` <br>`ceph fs dump` to inspect | Low — snapshot is CoW; export via `tar` or `rsync` from snapshot mount |
| **Off-site CRUSH/pool backup** | Cluster-level recovery after total loss | Rebuild cluster from scratch with correct topology | Store `crushmap`, `monmap`, `osd map`, and pool configs on separate physical media or separate RGW bucket with lifecycle retention ≥ 90 days | **Critical** — without off-site CRUSH map, cluster cannot be rebuilt with identical failure domains; may result in incorrect data placement |

> ** Specialist review required **: Off-site backup of the monmap+crushmap+osdmap is a **non-negotiable** recovery artifact. Its integrity must be verified quarterly. Storing it on the same Ceph cluster is circular and insufficient.

---

## 6.5 Config + Keyring Protection

| Artifact | Location | Backup Procedure | Restore Procedure | Risk |
|---|---|---|---|---|
| **Monmap + MON keyring** | `/var/lib/ceph/mon/ceph-<id>/keyring` / `/var/lib/ceph/mon/ceph-<id>/monmap` | `ceph-mon --dump-monmap > /backup/monmap-$(date +%F).txt` <br>`ceph-auth dump mon <id> > /backup/monkeyring-$(date +%F).keyring` | `ceph-mon --create-mon -i <id> --monmap <file> --keyring <file>` <br>Then `systemctl start ceph-mon <id>` | **High** — monmap/keyring mismatch can prevent cluster join; verify etcd/OSD map consistency after restore |
| **OSD keyring** | `/var/lib/ceph/osd/ceph-<id>/keyring` | `ceph-auth dump osd <id> > /backup/osdkeyring-$(date +%F).keyring` | `ceph-osd -i <id> --keyring <file>` <br>or re-deploy via cephadm | Low — OSD keyring is specific to that OSD; re-deploy is safer |
| **MDS keyring + dentree** | `/var/lib/ceph/mds/ceph-<id>/keyring` | `ceph-mds --dump-keyring > /backup/mdskeyring-$(date +%F).keyring` | `ceph-mds -i <id> --keyring <file>` <br>or re-deploy via cephadm | Low — MDS state is volatile; metadata lost on restore is expected if not also snapshotted |
| **RGW keyring + Swift certs** | `/etc/ceph/ceph.client.rgw.<zone>.keyring` / `/etc/ceph/<zone>.crt` / `./<zone>.key` | `cp /etc/ceph/ceph.client.rgw.*.keyring /backup/` <br>`cp /etc/ceph/*.crt /etc/ceph/*.key /backup/` | `cp /backup/ceph.client.rgw.*.keyring /etc/ceph/` <br>`systemctl restart ceph-rgw.target` | Low — certs may expire; verify rotation after restore |
| **CephX client secrets** (for CSI) | External Secrets / Vault | Store CSI provisioner secrets in External Secrets Operator with auto-rotation | Rotate via `ceph auth get-key ring` and re-wrap in External Secrets; do not hardcode in K8s manifests | Medium — lost CSI access if secrets not rotated; requires External Secrets access |

> ** Specialist review required **: Any monmap/keyring restore requires the infrastructure specialist to verify the etcd cluster state and OSD map are consistent with the restored monmap. Do not restore monmap over a cluster with newer state without a full etcd restore procedure.

---

## 6.6 RBD Backup & Recovery

| Operation | Mechanism | Command | Recovery Use Case | Risk |
|---|---|---|---|---|
| **Create RBD snapshot** | Copy-on-write snapshot | `rbd snapshot create rbd/vol1@$(date +%Y%m%d-%H%M%S)` | Quick rollback to prior state; protects against accidental `rm -rf` or corrupt write | Low — snapshot is CoW; negligible storage overhead until modification |
| **RBD snapshot rollback** | Revert image to snapshot state | `rbd snapshot rollback rbd/vol1@<snapname>` | Recover from accidental corruption or application error | **Medium** — all writes after snapshot are lost; application data may be inconsistent |
| **Export RBD to file** | Export snapshot to object storage or local file | `rbd export rbd/vol1@<snapname> /tmp/vol1-export.tar` <br>Then `aws s3 cp /tmp/vol1-export.tar s3://backups/rbd/` | Disaster recovery off-cluster; migrate to different Ceph cluster | Low — export is file-level; verify checksum after import |
| **Import RBD from exported file** | Re-import from exported image | `rbd import /tmp/vol1-export.tar rbd/vol1-restored` | Recover RBD image to different cluster or after total Ceph loss | **Medium** — depends on exported image consistency; verify `rbd info` after import |
| **Clone from snapshot** | Create writable clone from snapshot | `rbd clone rbd/vol1@<snapname> rbd/vol1-clone` | Instant copy for testing or temporary recovery; no data copy | Low — clone shares underlying data; if base snapshot is lost, clone is invalid |
| **Resize RBD image** | Increase image size | `rbd resize rbd/vol1 --size 50G` | Add capacity before backfill or recovery | Low — online operation; requires filesystem resize afterward (`xfs_growfs` or `resize2fs`) |

> ** Specialist review required **: `rbd snapshot rollback` is a disruptive operation that loses all data written after the snapshot. Must have a verified application-consistent backup (Velero + CSI snapshot or RBD snapshot + application dump) before rolling back.

---

## 6.7 CephFS Data & Metadata Recovery

| Operation | Mechanism | Command | Recovery Use Case | Risk |
|---|---|---|---|---|
| **Create CephFS snapshot** | CoW snapshot of metadata + data | `ceph fs snapshot create cephfs <snapname>` | Protect against accidental file deletion or rmdir | Low — CoW snapshot; minimal overhead |
| **CephFS snapshot rollback** | Rollback metadata AND data to snapshot state | `ceph fs snapshot rmdir cephfs <snapname>` (must be empty first) <br>Or `ceph fs snapshot delete cephfs <snapname>` after `ceph fs snapshot trim` | Recover from accidental directory deletion or filesystem corruption | **High** — removes **all** data changed after snapshot; any application data written after snapshot is lost permanently |
| **CephFS directory/figure restore from snapshot** | Export snapshot directory to local tree | `mkdir /tmp/restore <br>ceph fs dump > /tmp/cephfs-tree <br>` or use `rgw` to export via S3 gateway | Restore specific directory structure after deletion | Low — snapshot preserves state at point-in-time; verify content after export |
| **Metadata server failover** | MDS failover to standby | `ceph mds faildomain <active> <standby>` <br>`ceph mds stat` shows active/standby | Recover from MDS crash; no data loss if standby was syncing | Low — standby MDS has near-current metadata; brief service interruption during failover |
| **Recover MDS after total loss** | Restart MDS with recovered dentree | `ceph mds recover <id>` <br>or `systemctl restart ceph-mds.target` | MDS process crashed; metadata may be stale if journal not flushed | **Medium** — if MDS died with unflushed journal, some metadata may be lost; verify `ceph fs stat` after recovery |

> ** Specialist review required **: `ceph fs snapshot rmdir` / `ceph fs snapshot rm` on a non-empty snapshot or without prior trim is destructive. Always verify the snapshot is empty (`ceph fs snapshot ls cephfs`) and that no active clients have the snapshot mounted before removing.

---

## 6.8 RGW Object Data & Metadata Recovery

| Operation | Mechanism | Command | Recovery Use Case | Risk |
|---|---|---|---|---|
| **Enable RGW versioning** | Protect objects against overwrite/delete | Via RGW bucket lifecycle config or console | Recover objects deleted or overwritten by mistake | Low — versions are retained per bucket lifecycle (default 30d, configurable) |
| **RGW bucket restore from version** | List and restore a prior version | Via RGW API or console; no Ceph CLI | Recover from `rm -rf` or accidental overwrite | Low — versioning is additive; select the correct version to restore |
| **Ceph snapshot of RGW bucket data** | Export RGW bucket data using `rados` | `rados -p <rgw> export <bucket> <dest-dir>` <br>using the snapshot ID from `ceph fs snapshot` or `ceph osd pool snapshot` | Recover bucket after cluster loss or RGW deletion | **Medium** — export is hot; requires available OSDs and CRUSH map; may take hours for large buckets |
| **RGW object delete + recover** | `rados rm` with versioning enabled | Via RGW console: restore prior version | User accidentally deleted an object | Low — versions preserved; select correct version |
| **Cross-cluster RGW replication** | Async replication to remote RGW | Configure replication group in Ceph; `ceph rgw replication enable <bucket>` | Disaster recovery to off-site cluster | **High** — async replication may lag; data written after last replication point is lost. RPO must be defined and accepted. |
| **Off-site RGW backup via rados copy** | Copy RGW data to remote Ceph cluster | `rados copy <src-pool> <dst-pool> <bucket>` <br>Scheduled via cron | Mirror bucket to separate site for DR | **Medium** — depends on network bandwidth; RPO defined by sync frequency; data since last sync is lost if site fails |

> ** Specialist review required **: Cross-cluster RGW replication requires defined RPO/RTO. Asynchronous replication means data since the last successful replication is lost if the primary site fails. Always document the RPO and have a validated off-site backup separate from replication.

---

## 6.9 Rook-Ceph Operator + K8s Resource Recovery

| Scenario | Preconditions | Recovery Procedure | Validation | Data-loss Risk |
|---|---|---|---|---|
| **Rook-Ceph operator lost** | Operator pod terminated; CRDs still present | `kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/common.yaml` <br>`kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/operator.yaml` <br>Verify: `kubectl -n rook-ceph get pods` shows rook-ceph-operator running | `ceph -s` shows cluster healthy; Rook CRDs are restored | Low — operator is stateless; CRDs and Ceph data preserved in K8s etcd |
| **CephCluster CR lost** | CephCluster resource deleted; cluster still running | Restore from backup: <br>`kubectl get cephcluster/rook-ceph -o yaml > /backup/cephcluster-backup.yaml` <br>Apply: `kubectl apply -f /backup/cephcluster-backup.yaml` <br>Or re-create with same spec | `kubectl -n rook-ceph get cephcluster -o yaml` shows restored spec; `ceph -s` shows daemons matching spec | Low — CR spec is small; data preserved in OSD mon maps |
| **OSD pod crashed** | OSD pod in `CrashLoopBackOff` or `Error` | `kubectl -n rook-ceph delete osd <id>` <br>`rookadm` or manual: mark device lost, add new device <br>`ceph orch device ls` on the node <br>Replace disk, then: `ceph osd in <new-osd-id>` | `kubectl -n rook-ceph get pods` shows new OSD pod Running <br>`ceph -s` shows new OSD `up` and `in` | Low — Rook operator handles OSD creation; data rebalances automatically |
| **MON pod crashed** (Rook) | `rook-ceph-mon` pod not running | `kubectl -n rook-ceph rollout restart deployment/rook-ceph-mon` <br>Or: `kubectl delete pod -n rook-ceph -l app=rook-ceph-mon` <br>New pod auto-creates from CRD | `kubectl -n rook-ceph get pods` shows mon running; `ceph quorum_status` shows quorum | Low — MON data preserved in etcd (K8s) and OSD map |
| **RGW pod crashed** (Rook) | `rook-ceph-rgw` pod not running | `kubectl -n rook-ceph rollout restart deployment/rook-ceph-rgw` <br>Verify: `rados -p <pool> ls` and RGW API responds | RGW API responds; bucket listings work | Low — RGW data preserved in Ceph OSDs; restart is stateless |
| **CSI driver lost** | RBD/CephFS PVCs cannot be provisioned | `kubectl apply -f https://github.com/rook/rook/releases/download/<VERSION>/csi/rbd.yaml` <br>or `csi/cephfs.yaml` <br>Verify: `kubectl get storageclass` shows ceph-rbd / cephfs | CSI pods running; PV provisioning works | Low — CSI driver is stateless; pools and data preserved in Ceph |

> ** Specialist review required **: Any CephCluster CR re-creation after loss requires verification that the monmap/osdmap are consistent with the existing OSDs. Do not re-create the CR if the OSD map has changed since the CR was last applied — this may result in incorrect CRUSH placement and data unavailability.

---

## 6.10 CSI / PVC Recovery

| Scenario | Mechanism | Command | Validation | Data-loss Risk |
|---|---|---|---|---|
| **PVC lost after cluster restart** | PVC references a VolumeSnapshot | `kubectl get pvc <name> -o yaml` <br>Check `dataSource` points to existing snapshot | If snapshot exists in CSI driver, PVC binds automatically <br>If snapshot lost, restore from Ceph snapshot or RGW backup | **Medium** — depends on whether the CSI snapshot survived cluster restart; CSI snapshots stored in Ceph may be lost if OSDs are down |
| **PVC bound to new cluster** | Restore from Velero backup + CSI snapshot | `velero restore create --from-backup <name> --include-namespaces <ns>` <br>PVCs are restored from volume snapshots | All PVCs bound; pods start; application data matches pre-snapshot checksum | Low — depends on Velero backup integrity and CSI snapshot availability in target cluster |
| **CSI snapshot not available** | Volume snapshot expired or purged | Restore from Ceph RBD/CephFS snapshot: <br>`rbd snapshot create <pool>/<image>@<snapname>` <br>Create PVC from snapshot (driver-specific) | PVC created; application starts from snapshot state | **Medium** — CSI snapshot may not be available if driver version incompatible; fallback to RBD snapshot export/import |
| **PVC stuck in Terminating** | PVC not releasing; orphaned | `kubectl patch pvc <name> -p '{"metadata": {"finalizers": null}}'` <br>**Only if absolutely required** | PVC deleted; underlying RBD image may still exist in Ceph | **Medium** — removing finalizer without unmounting may leave orphaned data; use with caution and only after application stop |
| **PVC resized after recovery** | Expand volume after restore | `kubectl edit pvc <name>` → change `requests.storage` <br>Then: `ceph osd pool set <pool> size <new-size>` or let CSI driver handle | PVC expands; filesystem expanded with `xfs_growfs` or `resize2fs` | Low — online resize; verify filesystem after resize |

> ** Specialist review required **: PVC finalizer removal is a dangerous operation that may leave orphaned resources. Only use after confirming the application is stopped and the underlying Ceph OSD/RBD image is quiescent. CSI driver version must support the snapshot API in the target cluster.

---

## 6.11 Cross-Cluster / Off-Site Disaster Recovery

| Recovery Type | RPO | RTO | Procedure | Validation |
|---|---|---|---|---|
| **Cluster loss (total)** | Depends on backup frequency (typically ≤ 1h for Velero + CSI snapshots; ≤ 24h for off-site RGW replication) | 2–24 hours depending on cluster size and restoration complexity | 1. Provision new K8s cluster <br>2. Install Velero with supported CSI driver <br>3. Restore etcd from latest off-site snapshot <br>4. Restore K8s objects from Velero backup <br>5. Restore PVCs from volume snapshots (if off-site snapshots available) <br>6. Validate application data integrity | `kubectl get pods -A` shows all expected pods Running <br>`ceph -s` shows cluster HEALTH_OK <br>Application smoke tests pass; row counts / checksums match |
| **Single-node failure** | N/A (no data loss) | < 30 minutes | Drain node; migrate pods; replace OSD/MON as per Sections 6.2–6.9 | `ceph -s` shows HEALTH_OK; all PGs active+clean; no client-visible errors |
| **RGW cross-cluster replication failover** | Defined RPO (e.g., ≤ 1 hour async lag) | < 1 hour (promote remote cluster) | 1. Verify remote RGW cluster healthy <br>2. Promote remote bucket: `ceph rgw replication promote <bucket>` <br>3. Update DNS / endpoint config to point to remote cluster <br>4. Validate object accessibility | Remote bucket listings work; object GET/PUT successful; RPO met (data loss ≤ accepted threshold) |
| **CRUSH map / topology mismatch** | N/A | Specialist review required | 1. Import CRUSH map from off-site backup: `ceph osd setcrushmap <backup-file>` <br>2. Rebalance pools: `ceph osd rebalance <ratio>` <br>3. Verify data placement | `ceph osd tree` shows correct topology; data distribution matches expected failure domains; no `HEALTH_WARN` |

> ** Critical **: Cross-cluster DR is the **only** mechanism that protects against total site loss. Snapshots and replication within a single cluster do not protect against fire, power loss, or catastrophic infrastructure failure at one location. Off-site backups must be on physically separate infrastructure or a different cloud provider region.

> ** Specialist review required **: Any cross-cluster DR exercise requires infrastructure specialist sign-off, documented RPO/RTO acceptance, and a rollback plan to re-sync or re-import data to the primary cluster. Do not promote cross-cluster replication as a routine operation without verified RPO compliance.

---

## 6.12 Summary: Protection Mechanism Quick-Reference

| Mechanism | Protects Against | Does NOT Protect Against | Typical RPO | Typical RTO |
|---|---|---|---|---|
| **Replication (3x)** | Disk/node failure | Cluster loss, ransomware, logical corruption | 0 (synchronous) | Minutes (backfill) |
| **Erasure coding (4+2)** | Disk failure (space savings) | Node failure (read-degrade path), cluster loss | N/A (not for DR) | Hours (rebuild) |
| **RBD/CephFS snapshot** | Accidental modification, point-in-time rollback | Cluster loss, disk failure (snapshot may be on same failed OSD) | Minutes to hours (snapshot frequency) | Minutes (rollback) |
| **RGW versioning** | Object overwrite/delete | Cluster loss, bucket deletion without versioning enabled | Configurable (days) | Minutes (version restore) |
| **Ceph RGW replication (async)** | Site-level disaster | Data lag (RPO); immediate corruption propagates async | Defined by sync interval (hours) | Minutes (failover) |
| **Off-site Ceph backup (mon+osd+pool export)** | Total site loss | Must be restored with matching hardware/topology | Depends on backup frequency | 2–24 hours (full rebuild) |
| **Velero + CSI snapshot** | K8s object + volume loss after cluster restart | Data written after snapshot; app consistency depends on quiescence | Minutes to hours (schedule) | 10–30 minutes (restore) |
| **Application-native dump (pg_dump, mysqldump)** | Database logical corruption | Cluster loss, filesystem corruption | Configurable (daily/continuous) | Minutes to hours (import) |

---

**Infra Maintainer**: Platform Team  
**Section**: 6 — Ceph & Rook-Ceph Recovery  
**Status**: DRAFT | **Owner**: Infrastructure Maintainer  
**Last reviewed**: 2026-11-25  
**Review cycle**: Quarterly (verify off-site backup integrity, review RPO/RTO assumptions)  
**Do NOT execute** any Ceph recovery commands against a live cluster without specialist sign-off and a tested rollback path. These procedures are documented for reference and drill purposes only.

---