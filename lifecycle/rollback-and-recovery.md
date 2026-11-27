# Section 11: Rollback and Recovery Strategy

*Last reviewed: 2026-11-24 | Version: 1.0*

---

## Overview

This section classifies rollback and recovery options for every major component in the cloud-native stack. **Never claim a component supports rollback unless upstream documentation confirms it.** Restoring old data into a newer (or older) software version is frequently unsafe and can result in data corruption, feature failure, or security vulnerabilities.

### Classification Key

| Code | Meaning |
|------|---------|
| `IR` | In-place rollback supported (binary or configuration) |
| `RB` | Restore from backup required |
| `RI` | Reinstallation and data restoration required |
| `FF` | Forward-fix only — downgrade unsupported |
| `UD` | Unsupported or unsafe downgrade — do not attempt |

---

## 11.1 Rollback Option Classifications by Component

### Kubernetes Control Plane

| Component | Rollback Option | Notes |
|-----------|----------------|-------|
| etcd | RB | Restore from snapshot requires etcd cluster stop; control-plane rollback limited to etcd data-store revert. |
| kube-apiserver | FF | API server version skew limits apply (one minor version); rolling back requires full cluster restart with older binary. |
| kube-controller-manager | FF | No in-place rollback; redeploy older binary. |
| kube-scheduler | FF | No in-place rollback; redeploy older binary. |
| kubelet | FF | No in-place rollback; kubelet version must match kube-apiserver within skew limits. |
| Kubernetes API | FF | Rolling back the API server is a control-plane operation requiring node-by-node binary replacement. |

### Cluster Networking

| Component | Rollback Option | Notes |
|-----------|----------------|-------|
| CNI plugins (Canal, Calico, Cilium, etc.) | RB | Some CNI plugins support in-place configuration rollback; binary rollback requires pod restart with older daemon set image. |
| Calico | RB | Configuration rollback via `calicoctl policy delete`; binary rollback via DaemonSet image tag change. |
| Cilium | RB | BPF program rollback supported; version rollback requires new Cilium pod deployment. |
| metallb | RB | Configuration rollback via `metallbctl`; binary rollback via DaemonSet image. |
| ingress-nginx | RB | Configuration rollback via `kubectl rollout undo`; binary rollback via container image tag. |

### Ingress and Service Mesh

| Component | Rollback Option | Notes |
|-----------|----------------|-------|
| ingress-nginx | RB | `kubectl rollout undo deployment/ingress-nginx-controller` supported. |
| istio | RB | `istioctlX rollback` supported for pilot-agent, sidecar injector, and policy components. |
| linkerd | RB | `linkerd rollback` supported. |

### Security Components

| Component | Rollback Option | Security-Sensitive Considerations |
|-----------|----------------|-----------------------------------|
| **Vault/OpenBao** | RB | Snapshot restore requires valid unseal keys and Raft state alignment. Restoring an old snapshot into a newer Vault version may reject incompatible data formats. **Warn**: secrets and unseal material from older versions may not import cleanly into newer versions. |
| **Keycloak** | RB | Database migration scripts may not be reversible. Token signing keys rotate on version upgrade; old tokens may not validate after rollback. **Warn**: restoring old user data into a newer Keycloak version may fail if schema changed. |
| **Gatekeeper / Kyverno** | RB | Policy definitions are versioned; rolling back the controller may leave policies from newer versions in an unresolved state. **Warn**: policy CRDs from newer Gatekeeper/Kyverno versions may not be editable by older versions. |
| **Falco** | FF | Falco rules and downstream alerts are not versioned for rollback; binary rollback requires daemon set image change. |
| **Trivy** | FF | Trivy scanner version and DB format are not compatible across major versions; DB must be rebuilt after rollback. |
| **Cosign** | FF | Signature keys and cosign key rings are not forward/backward compatible; rollback requires re-signing all artifacts. |

### Service Mesh (Istio / Linkerd)

| Component | Rollback Option | Notes |
|-----------|----------------|-------|
| Istio | RB | `istioctlX rollback` supported for specific components; mesh configuration is version-sensitive. |
| Linkerd | RB | `linkerd rollback` supported for control plane and data plane. |

### Storage

| Component | Rollback Option | Notes |
|-----------|----------------|-------|
| Rook Ceph | RB | Ceph cluster rollback requires `cephadm` rollback or restoring from cephadm backup; online rollback to older OS/mon version is unsafe. |
| CSI drivers | RB | CSI driver version rollback via Helm chart revision; ensure target version supports the current K8s API version. |
| NFS / EFS / PV backends | FF | Storage class parameters cannot be rolled back; data restoration from snapshot required. |

### Application Workloads

| Component | Rollback Option | Notes |
|-----------|----------------|-------|
| Helm releases | RB | `helm rollback` supported for releases using the history feature; history may be GC'd after 2-3 revisions. |
| Kustomize | RB | `kubectl apply -k` with previous patch; not a true binary rollback. |
| Operator-backed apps | RB | Depends on operator; many operators support `operator-sdk` revert or `oc apply --revision`. |

---

## 11.2 Recovery Decision Trees

### Decision Tree 1: Upgrade Failure During Rollout

```
Did the upgrade fail during canary phase?
  ├── Yes → Halt rollout, verify canary metrics, apply component-specific rollback
  │       ├── Kubernetes control plane: RB etcd snapshot restore, then redeploy older kube-apiserver binary on all nodes
  │       ├── Helm release: `helm rollback <release> <revision>`
  │       ├── Vault: RB — restore from most recent snapshot, re-unseal with stored shards
  │       └── Keycloak: RB — restore from database backup if schema unchanged; otherwise RI
  └── No → Upgrade completed; proceed to post-upgrade verification (Section 8 of upgrade-strategy.md)
```

### Decision Tree 2: Post-Upgrade Regression

```
Are application errors or data corruption observed after upgrade?
  ├── Yes → Identify changed component(s)
  │       ├── If security component (Vault, Keycloak, Gatekeeper): 
  │       │       • Check audit logs for API changes
  │       │       • Verify secrets and tokens still validate
  │       │       • If incompatible: RB from verified backup
  │       ├── If networking (CNI, ingress): 
  │       │       • Roll back CNI daemon set image tag
  │       │       • Roll back ingress-nginx via `kubectl rollout undo`
  │       └── If application: 
  │           ├── Check database schema migration reversibility
  │           ├── If schema changed: RI (reinstallation and data restoration)
  │           └── If data-only issue: RB from database snapshot
  └── No → Issue resolved; document root cause and update runbooks
```

### Decision Tree 3: Data Restoration Across Version Boundaries

```
Is data being restored into a version different from its origin?
  ├── Older data → newer version
  │       ├── Vault: ⚠ UNSAFE — older snapshots may use Raft format incompatible with newer versions; rebuild from export if possible.
  │       ├── Keycloak: ⚠ UNSAFE — token format, claim names, and schema may differ; export-import recommended over snapshot restore.
  │       ├── Database: ⚠ UNSAFE — column removals, type changes, and constraint additions may cause import failure.
  │       └── General: ⚠ UNSAFE — always test in staging first; plan for data transformation.
  └── Newer data → older version
          ├── Vault: ⚠ UNSAFE — newer Raft snapshots may not be readable by older Vault versions; export secrets first.
          ├── Keycloak: ⚠ UNSAFE — newer token signing keys may not be accepted; older clients may fail authentication.
          └── General: ⚠ UNSAFE — schema drift likely; use database migration tools to downgrade schema.
```

---

## 11.3 Configuration Rollback

| Method | Supported Components | Command Example |
|--------|----------------------|-----------------|
| `kubectl rollout undo` | Deployments, DaemonSets, Ingress-NGINX, Gatekeeper/Kyverno policies | `kubectl rollout undo deployment/ingress-nginx-controller` |
| Helm revision rollback | Helm releases with history preserved | `helm rollback my-release 3` |
| GitOps `argocd app sync --revision` | Argo CD managed applications | `argocd app sync my-app --revision 5` |
| Operator revert | Operator-dependent | Consult operator documentation (`oc apply --revision`, `operator-sdk revert`) |
| Manual config revert | Configuration files, CRDs | Restore previous ConfigMap/Secret revision from etcd backup |

### Configuration Rollback Limitations

- **CRD rollback**: CRDs are not automatically versioned. If a newer CRD definition removes a field, rolling back the controller does not restore the field in existing resources. **Action**: Export previous CRD spec from etcd backup before rolling back.
- **Secret rollback**: Secrets etcd-stored are binary-blob; rolling back the K8s API server does not guarantee Secret content compatibility across versions. **Action**: Use sealed-secrets or HashiCorp Vault versioned storage for secret rollback.
- **Certificate rollback**: TLS certificates issued by newer PKI versions may not be accepted by older service mesh control planes. **Action**: Maintain separate certificate rollback bundles sealed in offline storage.

---

## 11.4 Binary/Version Rollback

| Component | In-Place Binary Rollback | Requires Restore/Reinstall |
|-----------|-------------------------|----------------------------|
| Kubernetes binaries (kube-apiserver, kubelet) | FF | Redeploy older binary on all nodes; etcd data-store must be compatible |
| Container runtimes (containerd, crio) | RB | Restart daemon with older image; verify storage compatibility |
| Helm charts | RB | `helm install --revision` or `helm rollback` |
| Operators | FF | Redeploy operator with older CRD version; plan for GVK migration |
| Application container images | RB | Newer pod spec with older image tag; data migration may be required |

### Binary Rollback Workflow

1. **Identify the last known-good version** from the version inventory (`compatibility/version-matrix.md`).
2. **Verify etcd compatibility** — the etcd version must support the K8s API version of the target binary.
3. **Stop the component** on all affected nodes (if stateful) or set replicas to 0 (if stateless).
4. **Replace the binary/image** with the previous version.
5. **Start the component** and verify health checks pass.
6. **Validate data consistency** — compare critical data states against pre-upgrade snapshots.

---

## 11.5 Database Schema Rollback

| Scenario | Rollback Option | Notes |
|----------|----------------|-------|
| Liquibase/Flyway migration | RB | If `rollbackCount` or `rollbackTag` is defined in migration script.
| Manual SQL ALTER | FF | Downgrade scripts often incorrect; manual SQL required.
| Automatic ORM migration | FF | ORM rarely supports downgrade; data loss likely.
| Snapshot-based | RB | Database snapshot restore (pg_dump, mysqldump) to pre-migration state.

### Database Rollback Warnings

- **Never restore a production database snapshot into a newer PostgreSQL/MySQL version without testing first** — newer versions may have incompatible data formats or removed features.
- **Schema removal**: If the upgrade added a column/index, the downgrade SQL may fail if the older version expects the schema without it.
- **Data truncation**: If the newer version stores more data per row, restoring to an older version may truncate or reject rows.

---

## 11.6 Persistent Data Rollback

| Data Type | Rollback Option | Notes |
|-----------|----------------|-------|
| PV data (Ceph, Rook Ceph, EBS, GCS) | RB | Ceph snapshots; cloud provider snapshots. Verify snapshot compatibility with target version.
| Application state (Redis, Memcached) | RB | RDB/AOF snapshot restore; note that in-memory data since last snapshot is lost.
| Message queues (Kafka, RabbitMQ) | RB | Topic/message group restore from stored offsets/snapshots.
| Object storage (S3, Ceph RGW) | RB | Bucket versioning restore; note that delete markers may persist.

### Persistent Data Rollback Warnings

- **Restoring Ceph RGW snapshots across OS version boundaries is unsafe** — newer OS versions may use different kernel interfaces or librados versions. **Action**: Test in staging; plan for data transformation.
- **Cloud provider snapshots** (EBS, GCS) are zone-dependent and may not be restorable into a different Kubernetes cluster topology.

---

## 11.7 Kubernetes Control-Planet Rollback Limitations

| Limitation | Description | Mitigation |
|------------|-------------|------------|
| etcd data-store skew | etcd 3.6 supports K8s v1.36-v1.37 per upstream; rolling back to an older etcd version may require re-indexing the data-store. | Maintain etcd snapshot chain; verify compatibility matrix before rollback.
| API server version skew | K8s supports one minor version of skew between control plane and nodes; rolling back the API server requires coordinated node binary replacement. | Use rolling node upgrade; verify `kubectl version --client` compatibility.
| CNI/CSI dependency | CNI and CSI plugins must support the target K8s API version; rolling back K8s without updating CNI/CSI may cause pod startup failures. | Update CNI/CSI first, then roll back K8s control plane.
| CRD field removal | Newer K8s versions may remove API fields; rolling back the API server does not restore removed fields in existing CRs. | Export CRD specs from etcd; apply migration scripts before rollback.
| Cloud-addon compatibility | Ingress controllers, OIDC providers, and monitoring agents may have hard-coded version checks that prevent startup on older K8s. | Upgrade addons in lockstep; maintain compatibility matrix.

---

## 11.8 Security-Sensitive Rollback Considerations

### Secrets and Certificates

| Component | Rollback Consideration | Action |
|-----------|----------------------|--------|
| **Vault** | Snapshot restore + unseal | Always keep unseal shards and rotation keys offline. Verify snapshot integrity (`vault operator raft snapshot inspect`) before restore. |
| **Keycloak** | Token signing key rollback | After rollback, invalidate all existing sessions and force re-authentication. Old tokens may cryptographically fail validation. |
| **TLS certificates** | Certificate chain rollback | Maintain separate certificate rollback bundles. Rotating to a previous CA may break trust with clients that stored the newer CA certificate. |
| **Cosign** | Signature key rollback | Old signatures cannot be verified with new keys; re-sign all artifacts after rollback. |

### Policy and Admission Control

| Component | Rollback Consideration | Action |
|-----------|----------------------|--------|
| **Gatekeeper / Kyverno** | Policy CRD version skew | After policy controller rollback, audit `ConstraintTemplate` and `ClusterConstraint` objects for unresolved API versions. |
| **Falco** | Rule format changes | Falco rule YAML format may change between versions; after binary rollback, verify rules load without parse errors. |
| **OPA policies** | Rego version changes | Old Rego policies may reference removed built-in functions; test policy load after rollback. |

### Supply Chain and SBOM

| Component | Rollback Consideration | Action |
|-----------|----------------------|--------|
| **Cosign** | Signature verification across versions | Maintain SBOM for all container images; verify signature chain is intact before and after rollback. |
| **Trivy** | DB format changes | Trivy vulnerability DB is not cross-version compatible; rebuild DB after rollback. |
| **Helm releases** | Chart version and dependency constraints | After `helm rollback`, verify that no chart dependencies have been updated to incompatible versions in the mean time. |

---

## 11.9 Upgrade and Rollback Tracking

Maintain a rollback log alongside the upgrade inventory:

| Field | Description |
|-------|-------------|
| Component | Name of the component rolled back |
| Trigger | What triggered the rollback (upgrade failure, regression, etc.) |
| Version | Version rolled back to |
| Timestamp | When the rollback started/ended |
| Success | Whether the rollback completed successfully |
| Data consistency check | Result of post-rollback data validation |
| Lessons learned | Root cause and improvements to process |

This log is stored in `docs/fa/rollback-log.md` and reviewed at every CAB meeting.

---

## References

- `lifecycle/upgrade-strategy.md` — 10-phase lifecycle model with backup readiness (Section 5)
- `lifecycle/upgrade-validation-troubleshooting.md` — Post-upgrade verification checklist
- `lifecycle/upgrade-sequencing.md` — Upgrade order dependencies
- `lifecycle/version-compatibility-matrix.md` — Verified component versions and upgrade paths
- `backup-recovery/vault-backup-restore.md` — Vault snapshot restore procedure
- `backup-recovery/etcd-backup-restore.md` — etcd snapshot restore procedure
- `docs/fa/kubernetes-security-baseline.md` — Security baseline for control plane components
- `security/secrets-and-runtime-security.md` — Secrets management and runtime security
- `operations/rpo-rto-and-recovery-tiers.md` — Recovery time and point objectives