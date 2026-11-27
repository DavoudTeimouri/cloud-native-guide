# OSD Addition Procedure

## Purpose

Adding a new OSD to a Rook-Ceph cluster to increase capacity.

## When to Add

- Cluster capacity below threshold (e.g., < 20% free).
- OSD failure replacement (covered in OSD Replacement Procedure).
- Planned capacity growth per capacity forecast.

## Provisioning

- Ensure a new block device of equal or greater capacity is available on a node.
- Label the node if using zone/rack constraints.
- Create the OSD via the Rook operator: `kubectl -n rook-ceph create ceph-osd /dev/<device-path>`.

## Verification

- `ceph osd tree` — new OSD shows `in/up`.
- `ceph osd status` — cluster includes the new OSD.
- `ceph osd df` — usable size increased by the new OSD capacity.
- Rebalancing begins automatically; monitor with `ceph pg stat`.

## Related Procedures

- [Backup & Recovery Procedure](backup-recovery-procedure.md)
- [Failover Procedure](failover-procedure.md)
- [OSD Replacement Procedure](../rook-ceph/osd-replacement-procedure.md)
