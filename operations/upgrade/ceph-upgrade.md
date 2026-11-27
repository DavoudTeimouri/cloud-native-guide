# Ceph Upgrade

### Purpose
Upgrade Ceph version with rebalance.

### Prerequisites
- Ceph cluster HEALTH_OK
- Velero backup of Ceph resources
- New Ceph version compatible with Rook version

### Execution
```bash
# Upgrade via cephadm
cephadm upgrade --image harbor.internal/ceph/ceph:20.2.4

# Monitor rebalance
ceph -s
ceph osd pool ls

# If using Rook-Ceph, update operator first
helm upgrade rook-ceph rook-release/rook-ceph \
  --namespace rook-ceph \
  --version 1.21.0
```

### Validation
- `ceph -s` reports HEALTH_OK
- All PGs active+clean
- No data loss
