# Section 6: Storage and Stateful Application Integration

*Illustrative only — not production-committed configurations. No live infrastructure is used and no destructive storage tests are run against live systems from this document. All commands are representative; verify against authoritative upstream documentation.*

## 6.1 Storage integration test design principles

- Validate Ceph health and capacity before exercising PVC/PV lifecycle.
- Distinguish successful PVC provisioning from verified data durability.
- Do not run destructive storage tests against live infrastructure.
- Tests marked `lab-safe` may be run in a non-production lab; tests marked `staging-only` require staging approval.

## 6.2 Storage test scenarios

| Test ID | Scenario | Type | Classification |
|---|---|---|---|
| STG-001 | Ceph health and capacity | Positive | lab-safe |
| STG-002 | Ceph CSI provisioning | Positive | lab-safe |
| STG-003 | StorageClass behavior | Positive | lab-safe |
| STG-004 | PVC provisioning and binding | Positive | lab-safe |
| STG-005 | Pod mount and read/write | Positive | lab-safe |
| STG-006 | RBD-backed workload | Positive | lab-safe |
| STG-007 | CephFS shared access | Positive | lab-safe |
| STG-008 | Volume expansion where supported | Positive | lab-safe |
| STG-009 | Volume snapshot and restore where supported | Positive | lab-safe |
| STG-010 | Pod rescheduling and volume reattachment | Positive | lab-safe |
| STG-011 | Node failure behavior | Negative/failure | lab-safe |
| STG-012 | Storage failure alerts | Negative/failure | lab-safe |

## 6.3 Ceph health and capacity

**Objective**: Confirm Ceph cluster is healthy before any storage test proceeds.

**Preconditions**: Ceph cluster deployed; `ceph` CLI available with admin keyring.

**Test command**:
```bash
# Illustrative — replace namespace/pod with actual values
kubectl exec -n rook-ceph deploy/rook-ceph-tools -- ceph -s
```

**Expected output**: `HEALTH_OK`; all OSDs `up`/`in`; all PGs `active+clean`.

**Failure condition**: `HEALTH_WARN` or `HEALTH_ERR`; any PG `down`/`incomplete`/`undersized`.

**Remediation**: Resolve Ceph health alerts before proceeding; see `operations/ceph-disaster-recovery.md`.

**Evidence**: `ceph -s` output.

**Automation**: Manual operator procedure.

---

## 6.4 Ceph CSI provisioning

**Objective**: Confirm Ceph CSI driver can provision volumes.

**Preconditions**: Ceph CSI driver deployed; StorageClass referencing CSI exists.

**Test command**:
```bash
# Illustrative
kubectl get storageclass
kubectl get csinode
kubectl get pod -n rook-ceph -l app=csi-rbdplugin
```

**Expected output**: StorageClass with `provisioner: cephfs.csi.ceph.com` or `rbd.csi.ceph.com`; CSI driver pods `Running`.

**Failure condition**: CSI driver pods not `Running`; StorageClass missing.

**Remediation**: Redeploy CSI driver; verify driver version compatibility with Ceph version (see `lifecycle/version-compatibility-matrix.md`).

**Evidence**: `kubectl get storageclass` and `kubectl get pod -n rook-ceph`.

**Automation**: Shell script / kubectl check.

---

## 6.5 StorageClass behavior

**Objective**: Confirm StorageClass parameters (replication, pool, topology) are applied.

**Preconditions**: StorageClass defined; CSI provisioner available.

**Test command**:
```bash
kubectl get storageclass <sc-name> -o yaml
```

**Expected output**: Parameters match intended replication level (e.g., `replicated` size) and pool; `reclaimPolicy` as intended.

**Failure condition**: Parameters differ from intended configuration.

**Remediation**: Correct StorageClass parameters; re-provision.

**Evidence**: StorageClass YAML.

**Automation**: kubectl check.

---

## 6.6 PVC provisioning and binding

**Objective**: Confirm a PVC transitions to `Bound` and a PV is created.

**Preconditions**: StorageClass available; cluster has capacity.

**Test command**:
```bash
kubectl apply -f pvc-test.yaml
kubectl get pvc pvc-test
kubectl get pv
```

**Expected output**: PVC `Bound`; PV `Bound` with matching capacity.

**Failure condition**: PVC stuck `Pending`.

**Remediation**: Check StorageClass, capacity, CSI driver logs; `kubectl describe pvc pvc-test`.

**Evidence**: `kubectl get pvc pvcvc` and `kubectl get pv`.

**Automation**: Shell script / Kubernetes Job.

---

## 6.7 Pod mount and read/write

**Objective**: Confirm a pod can mount a PVC and perform read/write.

**Preconditions**: PVC `Bound`; test pod spec referencing PVC.

**Test command**:
```bash
kubectl apply -f pod-storage-test.yaml
kubectl exec pod/storage-test -- sh -c 'echo test-data > /mnt/data/testfile && cat /mnt/data/testfile'
```

**Expected output**: `test-data` echoed back.

**Failure condition**: Mount fails; read/write error.

**Remediation**: Check CSI node plugin, SELinux/AppArmor context, volume permissions.

**Evidence**: Command output.

**Automation**: Kubernetes Job / shell script.

---

## 6.8 RBD-backed workload

**Objective**: Confirm an RBD-backed workload can schedule and use block storage.

**Preconditions**: RBD StorageClass; pool with sufficient capacity.

**Test command**:
```bash
kubectl apply -f rbd-workload.yaml
kubectl get pod rbd-workload
```

**Expected output**: Pod `Running`; RBD image mapped on node.

**Failure condition**: Pod `Pending`/`CrashLoopBackOff` due to volume attach failure.

**Remediation**: Check Ceph OSD health, CSI rbdplugin, node multipath/rbd module.

**Evidence**: `kubectl get pod`; CSI rbdplugin logs.

**Automation**: Kubernetes Job.

---

## 6.9 CephFS shared access

**Objective**: Confirm multiple pods can mount the same CephFS volume concurrently.

**Preconditions**: CephFS StorageClass; MDS healthy.

**Test command**:
```bash
kubectl apply -f cephfs-pod1.yaml
kubectl apply -f cephfs-pod2.yaml
kubectl exec pod/cephfs-pod1 -- sh -c 'echo shared > /mnt/cephfs/sharedfile'
kubectl exec pod/cephfs-pod2 -- cat /mnt/cephfs/sharedfile
```

**Expected output**: `shared` readable from both pods.

**Failure condition**: One pod cannot mount or read.

**Remediation**: Check MDS health, CephFS subvolume group, permissions.

**Evidence**: Output from both pods.

**Automation**: Kubernetes Job.

---

## 6.10 Volume expansion where supported

**Objective**: Confirm volume expansion works when StorageClass `allowVolumeExpansion: true`.

**Preconditions**: PVC `Bound`; CSI driver supports expansion; file system supports online resize.

**Test command**:
```bash
kubectl patch pvc pvc-test --patch '{"spec":{"resources":{"requests":{"storage":"10Gi"}}}}'
kubectl get pvc pvc-test
```

**Expected output**: PVC size increases; file system resized.

**Failure condition**: PVC stuck `Resizing`; expansion rejected.

**Remediation**: Verify StorageClass `allowVolumeExpansion`; check CSI driver support.

**Evidence**: `kubectl get pvc` before/after.

**Automation**: Shell script.

---

## 6.11 Volume snapshot and restore where supported

**Objective**: Confirm a volume snapshot can be created and restored.

**Preconditions**: CSI driver supports snapshots; VolumeSnapshotClass defined.

**Test command**:
```bash
kubectl apply -f volumesnapshot.yaml
kubectl get volumesnapshot
kubectl apply -f pvc-from-snapshot.yaml
kubectl get pvc restored-pvc
```

**Expected output**: VolumeSnapshot `ReadyToUse`; restored PVC `Bound`.

**Failure condition**: Snapshot `Error`; restored PVC `Pending`.

**Remediation**: Check CSI snapshot controller, snapshot class, storage capacity.

**Evidence**: `kubectl get volumesnapshot`; `kubectl get pvc`.

**Automation**: Kubernetes Job.

---

## 6.12 Pod rescheduling and volume reattachment

**Objective**: Confirm a pod using a PVC can reschedule to another node and reattach the volume.

**Preconditions**: PVC `Bound` to a node; multiple worker nodes available.

**Test command**:
```bash
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
kubectl get pod <pod> -o wide
kubectl uncordon <node>
```

**Expected output**: Pod reschedules to another node; volume reattaches; read/write still works.

**Failure condition**: Pod stuck `Pending` with `AttachFailed`/`MountFailed`.

**Remediation**: Check CSI node plugin, node storage, multipath.

**Evidence**: `kubectl get pod -o wide`; event log.

**Automation**: Shell script (lab-safe only).

---

## 6.13 Node failure behavior

**Objective**: Confirm storage behavior when a node fails.

**Preconditions**: RBD/CephFS PVC in use on a node; lab-safe environment.

**Test command**: Simulate node failure (lab-safe); observe pod rescheduling.

**Expected output**: Pod reschedules; volume detaches from failed node and reattaches; data intact.

**Failure condition**: Volume remains attached to failed node; data loss.

**Remediation**: Force-detach volume; check Ceph OSD health.

**Evidence**: `kubectl get pod`; Ceph OSD status.

**Automation**: Lab-safe failure simulation only.

---

## 6.14 Storage failure alerts

**Objective**: Confirm storage failures generate alerts visible in monitoring.

**Preconditions**: Prometheus + Alertmanager configured; Ceph exporter scraping.

**Test command**:
```bash
kubectl get alertmanagerconfig -n monitoring
kubectl get prometheusrule -n monitoring | grep ceph
```

**Expected output**: Alert rules exist for Ceph health, OSD down, PG degraded, capacity near-full.

**Failure condition**: No Ceph alerts configured.

**Remediation**: Add Ceph alert rules; verify Alertmanager routing.

**Evidence**: PrometheusRule YAML.

**Automation**: kubectl check.

---

## 6.15 End-to-end stateful application test (Redis example)

**Objective**: Confirm a stateful application with persistent data survives pod recreation.

**Preconditions**: Redis image in internal Harbor; PVC StorageClass available.

**Test command**:
```bash
# Illustrative — replace image digest with pinned value
kubectl apply -f redis-statefulset.yaml
kubectl exec statefulset/redis -- sh -c 'echo e2e-test-data > /data/redis-test'
kubectl delete pod redis-0
kubectl wait --for=condition=ready pod/redis-0
kubectl exec statefulset/redis -- cat /data/redis-test
```

**Expected output**: `e2e-test-data` readable after pod recreation.

**Failure condition**: Data missing after pod recreation.

**Remediation**: Verify PVC binding, volume mount path, Redis persistence config (RDB/AOF).

**Evidence**: Output before/after pod deletion.

**Automation**: Kubernetes Job / shell script.

---

## 6.16 Validation summary

| Check | Expected result |
|---|---|
| Ceph health | `HEALTH_OK` |
| CSI driver pods | `Running` |
| PVC provisioning | `Bound` within timeout |
| Pod read/write | Data round-trips correctly |
| Pod reschedule + reattach | Volume reattaches; data intact |
| Redis after restart | Persisted data readable |
| Storage alerts | Configured and routed |

**Limitation**: Successful PVC provisioning is not proof of data durability; data integrity is only confirmed by read/write verification (STG-005) and pod recreation (STG-015).

---

*SND 004-P11.7 — Storage and Stateful Application Integration Tests (illustrative)*
