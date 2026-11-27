# 10 · Ceph, Rook-Ceph, Storage Appliances

## Purpose and scope
Ceph/Rook/storage appliance upgrades; expansion, upgrade, troubleshooting.

## Steps
1. Check version compatibility matrix
2. Backup storage data (RBD snapshots, RGW objects)
3. Upgrade Ceph one OSD/MON/MGR at a time
4. Upgrade Rook operator/CRDs
5. Verify cluster healthy

## Implementation
```bash
# Ceph upgrade via cephadm
cephadm upgrade --ceph-version <new-version>

# Rook-Ceph upgrade via Helm
helm upgrade rook-ceph rook-ceph/rook-ceph --version <new-version> -n rook-ceph

# Verify
ceph -s
ceph osd stat
ceph pg stat
```

## Validation
- ceph -s: HEALTH_OK
- All OSDs up/in; PGs active+clean
- Rook operator Running

## Related
- [07 · Software-Defined Storage (7.4 Independent Ceph)](../07-software-defined-storage/7.4-independent-ceph.md)
- [07 · Software-Defined Storage (7.5 Rook-Ceph)](../07-software-defined-storage/7.4-independent-ceph.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
