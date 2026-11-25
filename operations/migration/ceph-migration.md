# Ceph Migration

### Purpose
Migrate Ceph to newer major version with rebalance.

### Prerequisites
- Ceph cluster HEALTH_OK
- Backup Ceph RBD snapshots
- New Ceph version compatible with Rook version
- Maintenance window scheduled

### Execution
```bash
# Upgrade via cephadm (if using cephadm)
cephadm upgrade --image harbor.internal/ceph/ceph:21.2.0

# If using Rook-Ceph
# 1. Upgrade Rook operator first
helm upgrade rook-ceph rook-release/rook-ceph \
  --namespace rook-ceph \
  --version 1.21.0

# 2. Update Ceph version in CephCluster CR
kubectl patch cephcluster rook-ceph -n rook-ceph \
  --type merge -p '{"spec":{"cephVersion":{"image":"ceph/ceph:v21.2.0"}}}'

# Monitor
ceph -s
ceph osd pool ls
```

### Validation
- `ceph -s` reports HEALTH_OK
- All PGs active+clean
- No data loss
- All OSDs up and in