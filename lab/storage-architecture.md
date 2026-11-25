# Storage Architecture: Ceph vs Rook-Ceph (TASK 006)

## 1. Purpose
Compare Ceph deployment options for the Lab and recommend a preferred approach. All figures are planning estimates pending the infrastructure inventory.

## 2. Options compared

### Option A — Dedicated Ceph (cephadm-managed)
Ceph runs on dedicated storage nodes outside Kubernetes, managed by cephadm. Kubernetes consumes storage via the Ceph CSI driver.

| Aspect | Detail |
|---|---|
| MON/MGR/OSD placement | Dedicated storage nodes (3 MON, 2 MGR, 3+ OSD) |
| Networks | Ceph public/client + Ceph cluster/replication (separate subnets) |
| RBD/CephFS | Available; RGW optional for S3 |
| Failure domains | Rack/host-level; OSD failure tolerated via replica 3 |
| Capacity overhead | Replica 3 → usable ≈ raw/3; plus recovery/backfill headroom |
| Monitoring | ceph dashboard, Prometheus ceph exporter |
| Backup | Velero for Kubernetes volumes; Ceph native tools for RADOS |

Pros: Mature, battle-tested; clear separation of storage lifecycle from Kubernetes; storage survives Kubernetes control-plane loss; tunable failure domains.
Cons: Dedicated hardware required; more nodes to manage; storage recovery is outside Kubernetes.

### Option B — Rook-Ceph (Kubernetes-native)
Ceph runs inside Kubernetes via Rook-Ceph operator (v1.21.0), with dedicated storage worker nodes.

| Aspect | Detail |
|---|---|
| MON/MGR/OSD placement | Kubernetes pods on dedicated storage workers |
| CSI integration | Native Rook-Ceph CSI driver |
| Kubernetes dependency | Rook depends on K8s API; Ceph depends on Rook operator |
| Recovery dependency | Ceph recovery requires healthy K8s control plane + CNI + Rook operator |
| Upgrade implications | Rook and Ceph versions must be matched per Rook release notes |
| Capacity overhead | Replica 3 → usable ≈ raw/3 |

Pros: Kubernetes-native lifecycle; declarative storage; integrated with K8s storage classes.
Cons: **Do not assume Rook-Ceph is automatically simpler.** Rook adds an operator layer; a K8s control-plane outage can impair Ceph management (though existing mounts continue). Rook-Ceph upgrades require version-matched Ceph images — a common failure source.

### Option C — External Ceph with Kubernetes CSI
Independently managed Ceph cluster consumed by Kubernetes via CSI.

| Aspect | Detail |
|---|---|
| Operational model | Ceph team operates Ceph; K8s team consumes via storage classes |
| HA | Ceph HA independent of K8s HA |
| Recovery isolation | Ceph recoverable without K8s; K8s recoverable without Ceph |
| Resource consumption | Dedicated Ceph nodes + CSI pods on K8s nodes |
| Failure isolation | Best — storage and control-plane failures are isolated |

Pros: Cleanest failure isolation; storage team and K8s team operate independently.
Cons: Most nodes/resources; two systems to operate and version-match (Ceph CSI must support target K8s API version before K8s upgrade).

## 3. Important distinctions
- **Storage capacity vs usable vs raw**: raw = total disk; usable = raw after replication/erasure coding (replica 3 → usable ≈ raw/3); always reserve ~30% headroom for recovery/backfill.
- **Test-only vs production-grade storage**: local-path/hostPath is test-only (no replication, no HA). Ceph/Rook with replica 3 is production-grade candidate.
- **Management-cluster recovery dependency**: do not put critical management-cluster recovery dependencies on storage that cannot be recovered independently. If the management cluster needs Ceph-backed storage to restart, you have a bootstrap deadlock. Management cluster should use local disk or independent storage for its own etcd and control-plane.

## 4. Recommendation for the Lab
**Option A — Dedicated Ceph** (or Option B Rook-Ceph on dedicated storage workers) is preferred for the Recommended/Expanded Lab profiles, because:
- It exercises the production storage path the platform targets (Ceph primary SDS).
- It keeps storage lifecycle separate from Kubernetes bootstrap.
- It avoids the Rook-Ceph control-plane coupling risk during Lab learning.

For the Small Lab profile: use local-path/hostPath (test-only, explicitly not production-grade) and defer Ceph/Rook until storage hardware is confirmed.

Do not deploy Ceph/Rook until OSD device availability is confirmed (see `lab/infrastructure-inventory-template.md` assumption A3 and P11.8 critical blocker #4).

## 5. Open questions
1. Are dedicated storage nodes with raw/passthrough disks available?
2. What Ceph release does the team target (Tentacle 20.2.4 is the current long-lived target per `compatibility/version-matrix.md`)?
3. Is RGW (S3) needed for backup targets, or is an external object store used?
