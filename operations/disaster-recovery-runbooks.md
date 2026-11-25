# Section 11 — Disaster Recovery Runbooks

*Illustrative only — not production-committed configurations. No live infrastructure or cluster is modified from this document. Mark destructive or irreversible actions clearly.*

Each runbook includes: scope and impact, preconditions, required access/dependencies, ordered recovery steps, commands and expected outputs, data integrity checks, service validation, rollback/escalation conditions, and evidence to retain.

## Runbook 1 — Loss of a Kubernetes Worker Node

**Scope and impact**: One worker node lost; its pods rescheduled to remaining nodes. Capacity reduced; workloads with `nodeSelector`/affinity to that node may be pending.

**Preconditions**: At least one remaining healthy worker; cluster API reachable.

**Required access**: `kubectl` cluster-admin; node SSH/console (for forensic, not recovery).

**Ordered recovery steps**:
1. `kubectl get nodes` — confirm the node is `NotReady`/`Unknown`.
2. Cordon the node (prevent new scheduling): `kubectl cordon <node>`.
3. Drain (if safe, to evacuate pods gracefully): `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --force`.
4. Verify pods rescheduled: `kubectl get pods -o wide | grep <node>` should return none.
5. Investigate node (hardware/hypervisor); repair or replace.
6. Uncordon only after node passes health checks: `kubectl uncordon <node>`.

**Expected outputs**: All non-DaemonSet pods from the lost node running on other nodes; node `NotReady` then removed/replaced.

**Data integrity checks**: PVCs attached to the lost node — confirm they detach and reattach on another node (`kubectl get pvc`).

**Service validation**: Application endpoints reachable; no `Pending` pods stuck due to node affinity.

**Rollback/abort**: If the node recovers and is healthy, uncordon it and rebalance.

**Evidence to retain**: `kubectl describe node <node>`, events, pod eviction logs.

---

## Runbook 2 — Loss of a Control-Plane Node

**Scope and impact**: One control-plane node lost; etcd quorum and API server capacity reduced. If 3-node stack loses 1 node, cluster remains operational but with no fault tolerance.

**Preconditions**: Remaining control-plane nodes maintain etcd quorum; API server reachable via VIP/LB.

**Required access**: `kubectl` cluster-admin; etcdctl access to remaining etcd nodes.

**Ordered recovery steps**:
1. `kubectl get nodes` — confirm control-plane node `NotReady`.
2. `etcdctl endpoint health --endpoints=<remaining-endpoints>` — confirm quorum healthy.
3. Confirm API server still serving: `kubectl get pod -A | head`.
4. Replace the lost node: provision new VM, join as control-plane node per Kubespray inventory.
5. Confirm new node joins etcd and becomes a voting member: `etcdctl member list`.
6. Remove the lost node from etcd membership if it will not return: `etcdctl member remove <lost-member-id>`.

**Expected outputs**: etcd cluster healthy with quorum; 3 control-plane nodes restored; API server fully redundant.

**Data integrity checks**: `etcdctl snapshot status /path/to/snapshot` — verify latest snapshot exists and is recent.

**Service validation**: `kubectl get nodes` all `Ready`; control-plane endpoints respond.

**Rollback/abort**: If the lost node recovers before replacement completes, rejoin it instead of provisioning new.

**Evidence to retain**: etcd member list, `kubectl get nodes`, etcd snapshot status.

---

## Runbook 3 — etcd Quorum or Data Recovery

**Scope and impact**: etcd lost quorum or data corruption; control plane may be read-only or unavailable.

**Preconditions**: A valid etcd snapshot exists; etcd binaries available.

**Required access**: etcdctl; root/sudo on etcd nodes; cluster-admin.

**Ordered recovery steps**:
1. Stop etcd on all nodes (`systemctl stop etcd`).
2. Back up existing (possibly corrupted) etcd data dirs — do not overwrite yet.
3. Restore snapshot on one node:
   ```bash
   etcdctl snapshot restore /backup/etcd-snapshot.db \
       --data-dir=/var/lib/etcd-restore
   ```
4. Verify snapshot integrity before relying on it:
   ```bash
   etcdctl snapshot status /backup/etcd-snapshot.db --write-out=table
   ```
   Expected: `Hash`, `Revision`, `TotalKey`, `TotalSize` present.
5. Start restored etcd node as a single-member cluster; verify `etcdctl endpoint health`.
6. Rejoin remaining nodes as new members; re-establish quorum.
7. Restart kube-apiserver, scheduler, controller-manager pointing at restored etcd.
8. `kubectl get componentstatuses` — all `Healthy`.

**Expected outputs**: etcd quorum restored; cluster API serving; all resources intact per snapshot revision.

**Data integrity checks**: `kubectl get ns` — all expected namespaces present; `kubectl get pod -A` — workloads match snapshot.

**Service validation**: Deploy a test pod; confirm it schedules and runs.

**Rollback/abort**: If snapshot is corrupt, fall back to an older snapshot; never restore into a partially recovered cluster without clearing data first.

**Evidence to retain**: etcdctl snapshot status output, etcdctl member list, `kubectl get componentstatuses`.

> **Warning**: Never restore an etcd snapshot into an existing etcd data directory without clearing it first — mixed data causes inconsistency and split-brain.

---

## Runbook 4 — Loss of a Ceph OSD

**Scope and impact**: One OSD down; PGs degraded; data remains available via replicas/erasure coding; reduced redundancy until OSD returns or is replaced.

**Preconditions**: Ceph cluster has remaining healthy OSDs; MON quorum intact.

**Required access**: `ceph` CLI (admin keyring); OSD node access.

**Ordered recovery steps**:
1. `ceph health detail` — confirm degraded state, identify down OSD.
2. `ceph osd tree` — confirm OSD `down`.
3. If OSD is temporarily down (host reboot): wait for `up` and `in`; `ceph osd stat`.
4. If OSD failed permanently: mark out and replace:
   ```bash
   ceph osd out <osd-id>
   # replace disk/host, redeploy OSD via Rook-Ceph or cephadm
   ceph osd in <new-osd-id>
   ```
5. Monitor recovery: `ceph -s` — PGs transition from `degraded` to `active+clean`.

**Expected outputs**: OSD replaced; all PGs `active+clean`; health `HEALTH_OK`.

**Data integrity checks**: `ceph pg stat` — no stuck/unclean PGs; `ceph osd df` — utilization balanced.

**Service validation**: RBD/CephFS/RGW clients continue operating during degraded state (reduced redundancy).

**Rollback/abort**: If replacement OSD causes further instability, keep failed OSD `out` and operate at reduced redundancy until stable.

**Evidence to retain**: `ceph -s`, `ceph osd tree`, `ceph pg stat`.

> Do not run `ceph osd destroy` or `ceph osd rm` as routine recovery — these are destructive and require specialist review.

---

## Runbook 5 — Loss of a Ceph Cluster

**Scope and impact**: All Ceph MONs/OSDs lost; block/file/object storage unavailable; dependent PVCs and workloads fail.

**Preconditions**: Off-site backup of Ceph data (RBD images, CephFS, RGW objects) and Ceph config/keyrings exists; new storage hardware available.

**Required access**: Ceph admin keyring; off-site backup storage; new cluster hardware.

**Ordered recovery steps**:
1. Provision new Ceph cluster (Rook-Ceph or cephadm) on new hardware.
2. Restore Ceph config and keyrings from backup.
3. Restore MON quorum from backup (MON store or `ceph-mon` backup).
4. Restore OSD data from off-site backup (RBD images, CephFS, RGW buckets).
5. `ceph -s` — confirm `HEALTH_OK` and all pools active.
6. Re-create PVCs/StorageClasses pointing to restored Ceph; restart dependent workloads.
7. Validate application data access.

**Expected outputs**: New Ceph cluster healthy; data restored; workloads reading/writing restored data.

**Data integrity checks**: `ceph df` — capacity matches expectation; `ceph osd df` — balanced; application-level read/write test.

**Service validation**: Application pods mount restored PVCs; RGW buckets accessible.

**Rollback/abort**: If restored data is inconsistent, fall back to an earlier backup snapshot.

**Evidence to retain**: `ceph -s`, `ceph osd tree`, `ceph df`, application read/write test results.

---

## Runbook 6 — Loss of a Registry/Repository Service (Harbor/Nexus)

**Scope and impact**: Container images and packages unavailable; deployments and installs fail.

**Preconditions**: Backup of Harbor/Nexus config, metadata DB, and blob/artifact storage exists; internal registry endpoint (`harbor.internal`/`nexus.internal`) DNS intact.

**Required access**: Harbor/Nexus admin; object storage access; `kubectl` for imagePullSecrets.

**Ordered recovery steps**:
1. Restore Harbor/Nexus PostgreSQL/config from backup.
2. Restore blob/artifact storage from off-site backup (S3/Ceph RGW/filesystem).
3. Start Harbor/Nexus services; verify `curl -I https://harbor.internal/` and Nexus health endpoint.
4. Verify image pull: `crictl pull harbor.internal/oci/<image>` (or `docker pull`).
5. Re-apply imagePullSecrets if lost; verify workloads can pull.
6. Confirm replication jobs (Harbor) / sync jobs (Nexus) resumed.

**Expected outputs**: Registry API reachable; images pullable; replication/sync healthy.

**Data integrity checks**: `crictl pull` succeeds; image digest matches expected (`@sha256:...`); artifact checksums match backup manifest.

**Service validation**: Deploy a workload using a restored image; confirm it starts.

**Rollback/abort**: If metadata and blobs are inconsistent, restore both from the same backup timestamp.

**Evidence to retain**: registry health endpoints, image pull logs, replication status.

---

## Runbook 7 — Vault/OpenBao Recovery

**Scope and impact**: Vault sealed/unavailable; secrets inaccessible; workloads using dynamic secrets fail.

**Preconditions**: Raft snapshot and unseal material (shards/KMS) available; storage backend reachable.

**Required access**: Vault operator; unseal shards or KMS admin; storage backend access.

**Ordered recovery steps** (see operations/registry-identity-secrets-recovery.md Section 7.4):
1. Restore Raft snapshot on first node: `vault operator raft snapshot restore <path>.snap`.
2. Start first node; wait for leader election (`vault operator raft list-peers`).
3. Start remaining nodes; they join automatically.
4. Unseal all nodes: provide shards via `vault operator unseal`.
5. `vault status` — `Sealed: false`, `HA: true`.
6. Validate: `vault kv get <known-path>`; deploy workload that reads a secret.

**Expected outputs**: Vault unsealed; secrets resolvable; HA healthy.

**Data integrity checks**: Read back known secrets; confirm policies/tokens present (`vault policy list`, `vault token list`).

**Service validation**: Application retrieves secret from Vault without error.

**Rollback/abort**: Loss of unseal material = permanent data loss; restore from older snapshot + re-issue unseal keys.

**Evidence to retain**: `vault status`, `vault operator raft list-peers`, secret read test results.

---

## Runbook 8 — Keycloak Identity Service Recovery

**Scope and impact**: Users cannot log in; OIDC clients (Argo CD, Harbor, etc.) cannot authenticate.

**Preconditions**: Keycloak database backup and realm export available; Keycloak DB reachable.

**Required access**: Keycloak admin; DB access; OIDC client config backups.

**Ordered recovery steps**:
1. Restore Keycloak PostgreSQL database from backup.
2. Restore realm/client configuration export (if separate).
3. Restore TLS keystore/truststore and OIDC IdP federation metadata.
4. Start Keycloak; verify `https://keycloak.internal/health`.
5. Test login with a known user; test OIDC token issuance.
6. Re-apply identity provider mappings and group/role sync.

**Expected outputs**: Keycloak reachable; users authenticate; OIDC clients receive tokens.

**Data integrity checks**: Realms present (`/admin/realms`); clients configured; users able to log in.

**Service validation**: Argo CD/Harbor OIDC login succeeds after Keycloak restore.

**Rollback/abort**: Restore realm export to a known-good revision if configuration is inconsistent.

**Evidence to retain**: Keycloak health endpoint, login test results, realm export.

---

## Runbook 9 — Loss of the Monitoring Stack

**Scope and impact**: Prometheus/Grafana/Alertmanager/Loki unavailable; visibility reduced; alerts may not fire.

**Preconditions**: Monitoring config (Grafana dashboards, Prometheus rules, Alertmanager routes) in Git; storage (TSDB, Loki chunks) backed up.

**Required access**: `kubectl`; monitoring admin; object storage for TSDB/Loki chunks.

**Ordered recovery steps**:
1. Restore Prometheus TSDB and Loki storage from backup.
2. Restore Grafana dashboards/datasources from Git/backup.
3. Restore Alertmanager config and notification receiver state.
4. Restart monitoring stack; verify `http://prometheus.internal/-/healthy` and Grafana health.
5. Confirm scrape targets reappear; alerts re-evaluate.

**Expected outputs**: Prometheus/Grafana/Loki reachable; targets scraped; dashboards load.

**Data integrity checks**: Prometheus targets up; Grafana dashboards render; Alertmanager routes configured.

**Service validation**: Test alert fires (silence and fire a known alert) to confirm alerting path.

**Rollback/abort**: Restore monitoring config from Git if restored config is inconsistent.

**Evidence to retain**: Prometheus/Grafana health endpoints, target list, alert rule list.

---

## Runbook 10 — Complete Site or Infrastructure Outage

**Scope and impact**: Entire site/infrastructure unavailable; full disaster recovery.

**Preconditions**: Off-site backups of etcd, application data, Ceph, registries, Vault, Keycloak, Git, and monitoring config; DR site hardware/network ready.

**Required access**: DR site admin; all service backups; network/DNS control to repoint endpoints.

**Ordered recovery steps**:
1. Declare disaster; notify stakeholders; open incident record.
2. Provision DR site network, load balancers, DNS (repoint `*.internal` endpoints to DR IPs).
3. Restore control plane (etcd → K8s) — Runbook 3/2.
4. Restore CNI, storage (Ceph — Runbook 5), ingress.
5. Restore registries (Harbor/Nexus — Runbook 6) so images are pullable.
6. Restore Vault (Runbook 7), then Keycloak (Runbook 8).
7. Restore Argo CD and Git (Runbook 8); sync applications.
8. Restore monitoring (Runbook 9).
9. Validate end-to-end: deploy a test workload end-to-end.
10. Declare recovery complete; update DNS failback when primary returns.

**Expected outputs**: DR site serving traffic; all services validated; end-to-end test passed.

**Data integrity checks**: Cross-check restored data against backup manifests; application read/write tests.

**Service validation**: Critical user journeys (login, deploy, image pull) pass on DR site.

**Rollback/abort**: If DR validation fails, do not failback; iterate on DR site until validation passes.

**Evidence to retain**: Incident timeline, each runbook's evidence, end-to-end test results, DNS repointing records.

---

*SND 004-P11.5 — Disaster Recovery Runbooks (illustrative)*
