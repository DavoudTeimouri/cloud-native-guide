# Ceph Deployment

### Purpose
Deploy Ceph storage via cephadm on dedicated hosts.

### Prerequisites
- Phase 5 hardened OS on storage nodes
- Storage VLAN configured
- Phase 2 repos for Ceph packages/images

### Execution
```bash
# Bootstrap first MON
cephadm bootstrap --mon-ip 10.40.0.11 \
  --registry-url harbor.internal:5000 \
  --registry-username admin \
  --registry-password $HARBOR_PASSWORD \
  --initial-dashboard-user admin \
  --initial-dashboard-password $CEPH_DASHBOARD_PASSWORD

# Add remaining MONs
ceph orch host add ceph-st-2 10.40.0.12
ceph orch host add ceph-st-3 10.40.0.13
ceph orch apply mon 3

# Add OSDs
ceph orch daemon add osd ceph-st-1:/dev/nvme0n1
ceph orch daemon add osd ceph-st-2:/dev/nvme0n1
ceph orch daemon add osd ceph-st-3:/dev/nvme0n1

# Enable services
ceph orch apply mgr 3
ceph orch apply mds cephfs 2
ceph orch apply rgw rgw 2 --placement="2 ceph-st-1 ceph-st-2 ceph-st-3"

# Create pools
ceph osd pool create replicapool 64 64 replicated
ceph osd pool application enable replicapool rbd
ceph osd pool create cephfs_metadata 32 32 replicated
ceph osd pool create cephfs_data 64 64 replicated
ceph fs new cephfs cephfs_metadata cephfs_data

# Enable RBD mirroring (optional)
ceph mgr module enable rbddashboard
```

### Validation
- `ceph -s` reports HEALTH_OK
- 3 MON quorum survives one MON loss
- OSD failure triggers automatic rebalance
- RBD + CephFS + RGW functional test passes
- Ceph exporter feeds Prometheus
