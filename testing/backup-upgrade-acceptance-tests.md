# Section 13: Backup, Restore and Upgrade Acceptance

*Illustrative only — not production-committed configurations. No backup, restore, upgrade, or rollback operation is executed from this document. All commands are representative; verify against authoritative upstream documentation.*

## 13.1 Backup and restore acceptance tests

| Test ID | Scenario | Type | Classification |
|---|---|---|---|
| BKP-001 | etcd snapshot integrity | Positive | lab-safe |
| BKP-002 | Kubernetes object backup | Positive | lab-safe |
| BKP-003 | Persistent data backup | Positive | lab-safe |
| BKP-004 | Redis recovery | Positive | lab-safe |
| BKP-005 | Ceph recovery procedures | Positive | lab-safe |
| BKP-006 | Registry and repository backup | Positive | lab-safe |
| BKP-007 | Vault/OpenBao recovery readiness | Positive | lab-safe |
| BKP-008 | Keycloak database recovery | Positive | lab-safe |
| BKP-009 | GitOps configuration recovery | Positive | lab-safe |

## 13.2 etcd snapshot integrity

**Objective**: Confirm an etcd snapshot is valid and restorable.

**Preconditions**: etcd cluster deployed; `etcdctl` available; snapshot file exists.

**Test command**:
```bash
# Illustrative
etcdctl snapshot status /backup/etcd-snapshot.db --write-out=table
```

**Expected output**: `Hash`, `Revision`, `TotalKey`, `TotalSize` present; no corruption errors.

**Failure condition**: Snapshot corrupt; fields missing.

**Remediation**: Take a new snapshot; investigate etcd data directory.

**Evidence**: `etcdctl snapshot status` output.

**Automation**: Shell script.

---

## 13.3 Kubernetes object backup

**Objective**: Confirm Kubernetes resources can be exported and restored.

**Preconditions**: `kubectl` available; cluster access.

**Test command**:
```bash
kubectl get all,configmap,secret,pvc -A -o yaml > cluster-objects-backup.yaml
kubectl apply --dry-run=server -f cluster-objects-backup.yaml
```

**Expected output**: Export succeeds; dry-run validation passes.

**Failure condition**: Export fails; dry-run rejects resources.

**Remediation**: Fix resource definitions; re-export.

**Evidence**: Backup file; dry-run output.

**Automation**: Shell script / Kubernetes Job.

---

## 13.4 Persistent data backup

**Objective**: Confirm persistent data (PVC data) is captured by backup.

**Preconditions**: PVC `Bound` with data; backup tool (Velero/CSI snapshot) available.

**Test command**:
```bash
# Illustrative — Velero
velero backup create redis-backup --include-namespaces default
velero backup describe redis-backup --details
```

**Expected output**: Backup `Completed`; includes PVC data.

**Failure condition**: Backup `Failed`; PVC data missing.

**Remediation**: Fix Velero configuration; check CSI snapshot support.

**Evidence**: `velero backup describe` output.

**Automation**: Velero / shell script.

---

## 13.5 Redis recovery

**Objective**: Confirm a Redis application recovers from backup with data intact.

**Preconditions**: Redis backup (RDB/AOF + PVC) available.

**Test command**:
```bash
# Illustrative
kubectl apply -f redis-statefulset-restored.yaml
kubectl exec statefulset/redis-restored -- cat /data/redis-test
```

**Expected output**: Previously persisted data readable.

**Failure condition**: Data missing after restore.

**Remediation**: Verify backup captured correct data path; check Redis persistence config.

**Evidence**: Command output before/after restore.

**Automation**: Kubernetes Job / shell script.

---

## 13.6 Ceph recovery procedures

**Objective**: Confirm Ceph recovery procedures are documented and validated.

**Preconditions**: Ceph cluster; recovery procedure from `operations/ceph-disaster-recovery.md`.

**Test command**:
```bash
# Illustrative — verification only, no destructive action
ceph -s
ceph osd tree
ceph pg stat
```

**Expected output**: `HEALTH_OK`; OSDs `up`/`in`; PGs `active+clean`.

**Failure condition**: `HEALTH_WARN`/`HEALTH_ERR`.

**Remediation**: Follow Ceph recovery runbook; specialist review if unresolved.

**Evidence**: `ceph -s` output.

**Automation**: Manual operator procedure.

---

## 13.7 Registry and repository backup

**Objective**: Confirm Nexus/Harbor configuration, metadata DB, and blob/artifact storage are backed up.

**Preconditions**: Registry deployed; backup tooling available.

**Test command**:
```bash
# Illustrative — Harbor
kubectl get pod -n harbor | grep harbor-core
kubectl get pvc -n harbor
```

**Expected output**: Harbor core pod `Running`; PVCs `Bound`.

**Failure condition**: Core pod not `Running`; PVC not `Bound`.

**Remediation**: Fix Harbor deployment; check storage.

**Evidence**: `kubectl get pod/pvc` output.

**Automation**: Shell script.

---

## 13.8 Vault/OpenBao recovery readiness

**Objective**: Confirm Vault/OpenBao Raft snapshot and unseal material are backed up.

**Preconditions**: Vault/OpenBao deployed; snapshot available.

**Test command**:
```bash
# Illustrative
vault operator raft list-peers
vault status
```

**Expected output**: `Sealed: false`; peers listed; snapshot path documented.

**Failure condition**: `Sealed: true` with no unseal material; no snapshot.

**Remediation**: Restore from snapshot; re-issue unseal keys.

**Evidence**: `vault status` output; snapshot record.

**Automation**: Manual operator procedure.

---

## 13.9 Keycloak database recovery

**Objective**: Confirm Keycloak database and realm configuration can be restored.

**Preconditions**: Keycloak DB backup; realm export available.

**Test command**:
```bash
# Illustrative
kubectl get pod -l app.kubernetes.io/name=keycloak
```

**Expected output**: Keycloak pod `Running`; health endpoint reachable.

**Failure condition**: Pod not `Running`; health endpoint failing.

**Remediation**: Restore DB from backup; re-import realm export.

**Evidence**: `kubectl get pod` output; health endpoint response.

**Automation**: Shell script.

---

## 13.10 GitOps configuration recovery

**Objective**: Confirm GitOps configuration (Argo CD Applications, Projects, repository credentials) can be recovered from Git/backup.

**Preconditions**: Git repository with Argo CD resources; credential backup available.

**Test command**:
```bash
# Illustrative
kubectl get application,appproject -A
argocd repo list
```

**Expected output**: Applications and Projects present; repositories reachable.

**Failure condition**: Resources missing; repositories unreachable.

**Remediation**: Re-apply from Git; restore repository credentials from backup.

**Evidence**: `kubectl get` output; `argocd repo list`.

**Automation**: Shell script.

---

## 13.13 Upgrade readiness acceptance tests

| Test ID | Scenario | Type | Classification |
|---|---|---|---|
| UPG-001 | Version compatibility | Positive | lab-safe |
| UPG-002 | API deprecation checks | Positive | lab-safe |
| UPG-003 | CRD compatibility | Positive | lab-safe |
| UPG-004 | CNI/CSI compatibility | Positive | lab-safe |
| UPG-005 | Backup readiness | Positive | lab-safe |
| UPG-006 | Upgrade dependency gates | Positive | lab-safe |
| UPG-007 | Post-upgrade validation | Positive | lab-safe |
| UPG-008 | Rollback classification | Positive | lab-safe |

## 13.14 Version compatibility

**Objective**: Confirm target versions are compatible with the current stack.

**Preconditions**: `lifecycle/version-compatibility-matrix.md` current.

**Test command**:
```bash
kubectl version
kubectl get crd | head
```

**Expected output**: Current versions match matrix baseline; target versions listed as compatible.

**Failure condition**: Target version not in matrix; compatibility `UNVERIFIED` or `UNSUPPORTED`.

**Remediation**: Verify against upstream documentation; update matrix.

**Evidence**: `kubectl version` output; matrix reference.

**Automation**: Shell script.

---

## 13.15 API deprecation checks

**Objective**: Confirm no deprecated/removed APIs will break after upgrade.

**Preconditions**: Target Kubernetes version known.

**Test command**:
```bash
kubectl get --raw "/apis" | jq '.groups[].name'
kubectl get events -A | grep -i "deprecated\|removed"
```

**Expected output**: No deprecation warnings for APIs in use.

**Failure condition**: Deprecated API in use detected.

**Remediation**: Migrate workloads off deprecated API before upgrade.

**Evidence**: API group list; event output.

**Automation**: Shell script.

---

## 13.16 CRD compatibility

**Objective**: Confirm CRDs are compatible with target version.

**Preconditions**: CRDs deployed; target version known.

**Test command**:
```bash
kubectl get crd -o yaml | grep -E "storage:|served:"
```

**Expected output**: CRD storage version consistent; conversion webhooks healthy.

**Failure condition**: Storage version change; webhook failing.

**Remediation**: Migrate CRD data; fix conversion webhook.

**Evidence**: CRD YAML; webhook pod logs.

**Automation**: kubectl check.

---

## 13.17 CNI/CSI compatibility

**Objective**: Confirm CNI and CSI versions support target Kubernetes version.

**Preconditions**: CNI/CSI versions known; target version known.

**Test command**:
```bash
kubectl get daemonset -A | grep -E "cilium|csi"
```

**Expected output**: CNI/CSI versions in compatibility matrix as compatible.

**Failure condition**: Version not compatible.

**Remediation**: Upgrade CNI/CSI before Kubernetes upgrade.

**Evidence**: DaemonSet image output.

**Automation**: kubectl check.

---

## 13.18 Backup readiness

**Objective**: Confirm backups are current and valid before upgrade.

**Preconditions**: Backup procedure from `operations/backup-validation-and-drills.md`.

**Test command**:
```bash
# Illustrative — verify latest etcd snapshot exists and is recent
ls -lh /backup/etcd-snapshot.db
etcdctl snapshot status /backup/etcd-snapshot.db
```

**Expected output**: Snapshot exists; recent; valid.

**Failure condition**: Snapshot missing or stale.

**Remediation: Take a new snapshot before upgrade.

**Evidence**: Snapshot file listing; status output.

**Automation**: Shell script.

---

## 13.19 Upgrade dependency gates

**Objective**: Confirm upgrade dependency gates from `lifecycle/upgrade-sequencing.md` are satisfied.

**Preconditions**: Dependency graph reviewed.

**Test command**: Review dependency gates against current state.

**Expected output**: All gates green; prerequisites met.

**Failure condition**: Gate red; prerequisite missing.

**Remediation**: Satisfy prerequisite before upgrade.

**Evidence**: Gate checklist.

**Automation**: Manual operator procedure.

---

## 13.20 Post-upgrade validation

**Objective**: Confirm post-upgrade validation procedures are defined.

**Preconditions**: Upgrade completed (simulated).

**Test command**:
```bash
kubectl get nodes
kubectl get componentstatuses
kubectl get pod -A | grep -v Running
```

**Expected output**: All nodes `Ready`; components `Healthy`; no non-Running pods.

**Failure condition**: Node `NotReady`; component unhealthy; pods stuck.

**Remediation**: Follow rollback procedure (`lifecycle/rollback-and-recovery.md`).

**Evidence**: Command output.

**Automation**: Shell script.

---

## 13.21 Rollback classification

**Objective**: Confirm each major component's rollback option is classified.

**Preconditions**: `lifecycle/rollback-and-recovery.md` current.

**Test command**: Review rollback classification table.

**Expected output**: Each component classified (supported in-place rollback / restore from backup / reinstallation / forward-fix only / unsupported).

**Failure condition**: Component without rollback classification.

**Remediation**: Determine rollback option from upstream documentation.

**Evidence**: Classification table.

**Automation**: Manual operator procedure.

---

## 13.22 Limitations

- Documented procedures are not proof of tested recovery; actual restore drills required (see Section 14).
- No real backup, restore, upgrade, or rollback operation is executed from this document.

---

*SND 004-P11.7 — Backup, Restore and Upgrade Acceptance Tests (illustrative)*
