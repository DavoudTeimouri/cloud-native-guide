# Section 7: Ceph and Rook-Ceph Upgrade

*Illustrative only — not production-committed configurations. No live Ceph or Rook-Ceph cluster is upgraded from this document. All examples are version-dependent and labeled as such.*

## 7.1 Standalone cephadm-managed Ceph vs Rook-Ceph

| Aspect | cephadm-managed Ceph | Rook-Ceph (Kubernetes-managed) |
|---|---|---|
| Management | cephadm on dedicated hosts | Rook operator in K8s |
| Ownership | Infrastructure/ops team | Platform team via K8s CRs |
| Upgrade tool | `cephadm upgrade` | Rook operator + cluster CR |
| CSI driver | External CSI driver | Rook CSI integration |
| Upgrade sequence | Host-by-host via cephadm | Operator first, then mons, osds, mds, rgw |

Do not mix procedures: standalone Ceph uses cephadm commands; Rook-Ceph uses Kubernetes custom resources.

## 7.2 Ceph release lifecycle and supported upgrade paths

Supported upgrades follow Ceph release series (e.g., Octopus → Pacific → Quincy → Reef → Squid). Version-skipping is NOT supported; perform intermediate release steps.

Before upgrading:

1. `ceph -s` — confirm `HEALTH_OK` and quorum.
2. `ceph osd tree` — confirm all OSDs `up`/`in`.
3. `ceph pg stat` — confirm all PGs `active+clean`.
4. `ceph osd dump` — record current CRUSH map and pool configuration.
5. Back up Ceph config and keyrings (`/etc/ceph/ceph.conf`, `ceph.client.admin.keyring`).
6. Back up MGR and MON metadata.

## 7.3 Rook-Ceph operator upgrades

1. Upgrade the Rook operator Deployment first (new operator can manage older cluster CRs).
2. Verify operator rollout: `kubectl rollout status deployment/rook-ceph-operator -n rook-ceph`.
3. Update the `CephCluster` CR spec image to the target version.
4. Rook orchestrates mon, osd, mds, rgw upgrades automatically; monitor via `ceph -s`.

## 7.4 MON quorum and OSD health

- MON quorum must be intact before any upgrade (loss of quorum = cluster unavailable).
- OSDs must be `up` and `in` before upgrading; mark failed OSDs `out` and replace before proceeding.
- Upgrade MONs first (one at a time), then OSDs.

## 7.5 PG state and recovery requirements

- All PGs must be `active+clean` before upgrading OSDs.
- During OSD upgrade, PGs enter `degraded` state; this is expected.
- Do not force OSD backfill or recovery; wait for `active+clean`.
- `ceph osd pg stat` — monitor during and after upgrade.

## 7.6 CRUSH and pool compatibility

- Do not change CRUSH rules or pool configurations during the upgrade window.
- Record pool configuration before upgrade (`ceph osd pool ls detail`).
- Verify erasure coding and replication settings are unchanged after upgrade.

## 7.7 CSI driver compatibility

The Ceph CSI driver version must match the Ceph cluster version:

```bash
# Illustrative — check CSI driver version
kubectl get daemonset csi-cephfsplugin -n rook-ceph -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl get daemonset csi-rbdplugin -n rook-ceph -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Upgrade CSI driver after Ceph cluster upgrade; verify PVC provisioning and attachment afterward.

## 7.8 RBD and CephFS workload implications

- RBD images attached to running pods: OSD upgrade may cause brief I/O pauses; verify application resilience.
- CephFS: MDS upgrade may cause metadata server failover; verify CephFS mounts after upgrade.
- Do not create/delete PVCs during the upgrade window.

## 7.9 RGW compatibility

- RGW upgrade may cause brief S3 API unavailability; verify object store clients retry.
- `ceph rgw status` — confirm RGW daemons healthy after upgrade.

## 7.10 Rolling upgrade behavior

Ceph supports rolling upgrades (one OSD/MON/MDS/RGW at a time) with `active+clean` health gates between steps. Rook-Ceph automates this via the `CephCluster` CR.

Upgrade pauses: health gates pause the upgrade automatically if PGs are not `active+clean` or OSDs are not `up`/`in`.

## 7.11 Health validation

After upgrade:

```bash
ceph -s
# Expected: HEALTH_OK, all daemons up/in

ceph osd tree
# Expected: all OSDs up, in

ceph pg stat
# Expected: all PGs active+clean

ceph osd perf
# Expected: no slow ops, balanced latency
```

## 7.12 Workload validation

- Deploy a test pod with an RBD/CephFS PVC; confirm it mounts and can read/write.
- Verify CephFS mounts and RGW bucket access from application pods.
- Confirm CSI provisioning works for new PVCs.

## 7.13 Recovery and escalation criteria

| Condition | Action |
|---|---|
| PGs stuck `degraded` after OSD upgrade | Wait; check OSD health; specialist review if unresolved > 1 hour |
| MON quorum lost | Stop upgrade; restore MON from backup; specialist review |
| OSD not `in` after replacement | Check CRUSH map; `ceph osd in <id>`; specialist review |
| CSI provisioning fails | Check CSI driver version compatibility; redeploy CSI daemonsets |

## 7.14 Irreversible and high-risk operations

- Do NOT perform in-place downgrade of Ceph (not supported).
- `ceph osd destroy` / `ceph osd rm` — destructive; specialist review only.
- `ceph osd crush reweight` during upgrade — avoid; changes data distribution.
- Restoring old Ceph data into a newer Ceph version — unsafe; version mismatch can corrupt data.

## 7.15 Backup requirements

Before any Ceph upgrade:

- Back up Ceph config and keyrings.
- Back up pool and CRUSH configuration (`ceph osd dump`).
- Back up application data stored in RBD/CephFS/RGW (see `operations/ceph-disaster-recovery.md`).
- Confirm off-site backup copies exist.

---

*SND 004-P11.6 — Ceph and Rook-Ceph Upgrade (illustrative)*
