# Ceph Failure Recovery

## A. Purpose and scope

Document Ceph failure recovery procedures: MON loss, OSD loss, MGR loss, pool corruption, PG recovery, rebalancing.

Cross-references `storage/ceph/cephadm-deployment.md` §Recovery, `lifecycle/disaster-recovery/index.md` §Storage cluster degraded, `lifecycle/backup/backup-and-dr.md` §Ceph.

## B. MON loss

### Symptom
`ceph health` shows HEALTH_WARN with "mon" warnings. MON quorum lost if fewer than majority of MONs are available.

### Recovery

```bash
# Check MON status
ceph mon stat

# Check quorum status
ceph quorum_status

# If MON is down but data is intact, restart it
cephadm shell -- ceph mon enable <mon-name>

# If MON data is corrupted, deploy a new MON
cephadm shell -- ceph orch apply mon <new-host>

# Verify quorum restored
ceph quorum_status
ceph health
```

**Rule: Never remove all MONs simultaneously. Always maintain quorum (majority of MONs available).**

## C. OSD loss

### Symptom
`ceph osd stat` shows down OSDs. PGs show degraded or undersized state.

### Recovery

```bash
# Check OSD status
ceph osd stat
ceph osd tree

# Check PG status
ceph pg stat

# If OSD is temporarily down, restart it
cephadm shell -- ceph orch restart osd.<osd-id>

# If OSD is permanently lost, mark it destroyed and replace
ceph osd destroy <osd-id> --yes-i-really-mean-it
ceph osd purge <osd-id> --yes-i-really-mean-it

# Deploy new OSD
cephadm shell -- ceph orch apply osd <new-host:device>

# Verify recovery
ceph osd stat
ceph pg stat  # All PGs should be active+clean
```

**Rule: Never destroy more OSDs than the pool can tolerate. A 3-replica pool can lose 2 OSDs; a 2-replica pool can lose 1.**

## D. MGR loss

### Symptom
`ceph mgr stat` shows no active MGR. Dashboard and metrics unavailable.

### Recovery

```bash
# Check MGR status
ceph mgr stat

# If MGR is down, failover to standby
ceph mgr fail <active-mgr>

# If no standby, deploy a new MGR
cephadm shell -- ceph orch apply mgr <new-host>

# Verify
ceph mgr stat
ceph health
```

## E. Pool corruption

### Symptom
`ceph pg stat` shows PGs in inconsistent or undersized state. Data may be inaccessible.

### Recovery

```bash
# Check PG status
ceph pg stat
ceph pg dump pgs | grep -v active+clean

# For inconsistent PGs, mark them as clean (data loss possible)
ceph pg repair <pg-id>

# For undersized PGs, wait for recovery or add more OSDs
ceph pg set <pool-name> size <new-size>

# Verify
ceph pg stat  # All PGs should be active+clean
```

**Rule: `ceph pg repair` can cause data loss. Only use after verifying the data on other replicas is correct.**

## F. PG recovery and rebalancing

### Symptom
PGs are in recovering or rebalancing state. Cluster performance degraded.

### Recovery

```bash
# Check recovery status
ceph recovery status

# Check rebalancing status
ceph osd rebalance status

# Wait for recovery to complete (automatic)
# Monitor progress:
watch ceph pg stat

# If recovery is stuck, check for down OSDs
ceph osd stat
```

**Rule: Do not add or remove OSDs during recovery/rebalancing. Wait for the cluster to reach active+clean state.**

## G. Full cluster (OSDFULL)

### Symptom
`ceph health` shows HEALTH_ERR with "OSDFULL". Writes are blocked.

### Recovery

```bash
# Check capacity
ceph df

# If near full, add more OSDs or delete unnecessary data
ceph osd df

# If a pool is full, increase its quota or delete old snapshots
ceph osd pool set <pool-name> size <new-size>

# Verify
ceph health
ceph df
```

**Rule: Keep cluster capacity below 85% to avoid OSDFULL.**

## H. Cross-references

- `storage/ceph/cephadm-deployment.md` §Recovery — Ceph deployment and recovery
- `lifecycle/disaster-recovery/index.md` §Storage cluster degraded — Do not restore workloads into a degraded pool
- `lifecycle/backup/backup-and-dr.md` §Ceph — Ceph backup (RBD export / CephFS snapshot)
- `storage/rook-ceph/rook-ceph.md` — Rook-Ceph deployment model
