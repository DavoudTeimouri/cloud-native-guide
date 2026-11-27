# Expanding Ceph & Storage

## Purpose and scope
Add OSDs/MON/MGR/RGW, expand pools, storage appliances.

## Steps
1. Add Ceph OSD node (hardware/VM prep, OS baseline)
2. Add OSD to Ceph cluster (cephadm or Rook)
3. Expand Ceph pool (replication/erasure coding)
4. Add storage appliance capacity
5. Verify pool health and capacity

## Implementation
```bash
# Add Ceph OSD node via cephadm
cephadm add-host <new-node>
ceph orch apply osd --all-available-devices <new-node>

# Expand pool
ceph osd pool set <pool> size 3
ceph osd pool application enable <pool> <app>

# Add Rook OSD
kubectl apply -f - <<EOF
apiVersion: ceph.rook.io/v1
kind: CephBlockPool
metadata:
  name: replicapool
  namespace: rook-ceph
spec:
  failureDomain: host
  replicated:
    size: 3
EOF
```

## Validation
- ceph -s: HEALTH_OK
- New OSD up/in; backfill complete
- Pool expanded; capacity increased

## Related
- [07 · Software-Defined Storage (7.4 Independent Ceph)](../07-software-defined-storage/7.4-independent-ceph.md)
- [07 · Software-Defined Storage (7.5 Rook-Ceph)](../07-software-defined-storage/7.4-independent-ceph.md)
- [07 · Software-Defined Storage (7.7 Maintenance and Data Protection)](../07-software-defined-storage/7.7-maintenance-and-data-protection.md)
