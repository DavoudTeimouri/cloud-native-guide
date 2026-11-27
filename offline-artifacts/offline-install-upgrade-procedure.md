# Offline Installation and Upgrade Procedure

## A. Purpose and scope

Document reproducible offline installation and upgrade of the cloud-native platform without internet access. This procedure covers initial deployment, subsequent upgrades, and rollback for air-gapped environments. Cross-references `offline-artifacts/artifact-matrix.md`, `offline-artifacts/offline-package-repository.md`, and `lifecycle/upgrades/kubernetes.md`.

## B. Pre-deployment checklist

Before initiating any offline installation or upgrade, complete the following checks:

- [ ] **Artifact inventory** — Verify all required images, packages, and manifests are present in the internal mirror. Consult `offline-artifacts/artifact-matrix.md` for the expected component versions.
- [ ] **Internal mirror integrity** — Run checksum verification against the `offline-artifacts/offline-package-repository.md` manifest. All SHA-256 hashes must match.
- [ ] **Signature verification** — Confirm Cosign signatures for all container images using `offline-artifacts/signature-verification.md` procedures.
- [ ] **SBOM validation** — Verify Software Bill of Materials for all critical packages using Trivy or SPDX tools.
- [ ] **Cluster prerequisites** — Ensure all control-plane nodes meet minimum hardware requirements (CPU, memory, storage). Verify network connectivity between nodes on the offline VLAN.
- [ ] **Storage validation** — Confirm persistent storage classes are available and provisioned. Test snapshot/restore capability if using external databases.
- [ ] ** RBAC readiness** — Verify service accounts and roles required by the installation pipeline have been created in the internal cluster.
- [ ] **Disaster recovery backup** — etcd snapshot must be taken and verified before any upgrade. Store backup in the internal artifact repository.

## C. Bootstrap procedure

### C.1 Initial offline installation

1. **Mirror initialization** — Load the internal artifact mirror into the environment. Use `offline-artifacts/artifact-mirroring-procedure.md` to populate the registry and package repository.
2. **Node preparation** — Bootstrap each control-plane node with the pre-loaded container images and OS packages. No outbound internet access is required after mirror initialization.
3. **Cluster deployment** — Apply the Kubespray (or equivalent) playbooks referencing the internal image registry and package source. Set `offline=true` in the inventory to suppress internet-dependent steps.
4. **Core services bring-up** — Verify etcd, control-plane components, and CNI are running. Check `kubectl get nodes` shows all control-plane nodes `Ready`.
5. **Addon deployment** — Deploy core addons (ingress, metrics-server, DNS) from the internal mirror. Verify all pods are in `Running` state.

### C.2 Offline upgrade initiation

1. **New artifact mirror** — Populate the new version's artifact mirror using the mirroring procedure. Update `offline-artifacts/artifact-matrix.md` with the upgraded versions.
2. **Compatibility validation** — Cross-reference `kubespray/multi-version-support.md` to confirm the new versions are compatible with the existing cluster baseline.
3. **Pre-upgrade snapshot** — Take a fresh etcd snapshot and store it in the internal repository. Document the snapshot ID and retention policy.
4. **Upgrade readiness gate** — All pre-deployment checklist items from Section B must be confirmed complete before proceeding.

## D. Air-gapped validation

### D.1 Image integrity validation

```bash
# Verify each image in the offline mirror
for image in $(cat offline-artifacts/artifact-matrix.md | grep image | awk '{print $2}'); do
  skopeo inspect docker://$image | grep -E "RepoTags|Digest"
done
```

### D.2 Package integrity validation

```bash
# Verify OS package checksums against the repository manifest
cd /path/to/internal/mirror
sha256sum -c offline-artifacts/offline-package-repository.md
```

### D.3 Signature validation

```bash
# Verify Cosign signatures for all images
cosign verify-blob --signature-file <sig_file> --certificate-file <cert_file> docker://<image>
```

### D.4 Network air-gap confirmation

- No outbound DNS or HTTP requests should be observed from control-plane or worker nodes after bootstrap.
- Use `tcpdump` or `wireshark` on a monitoring host to confirm zero external traffic from the cluster CIDR during the validation window.
- Verify internal registry serves all required manifests via `curl http://<internal-registry>:5000/v2/_catalog`.

### D.5 Component compatibility check

- Run `kubectl get crds` and compare against the expected CRD set for the targeted version.
- Validate custom addons against `offline-artifacts/nexus-harbor-architecture.md` and `offline-artifacts/nexus-harbor-integration.md` integration patterns.

## E. Upgrade rollback

### E.1 Pre-upgrade rollback plan

1. **Snapshot etcd** before each upgrade phase. Store snapshot IDs in `offline-artifacts/offline-upgrade-procedure.md` and the internal artifact repository.
2. **Document current state** — `kubectl get all, kubectl get nodes, kubectl get pvc` captured before starting the upgrade.
3. **Rollback trigger conditions** — Any phase failure that leaves critical components in a `CrashLoopBackOff`, `Pending`, or `Error` state for >5 minutes triggers rollback.

### E.2 Rollback procedure by phase

#### Phase rollback — etcd upgrade

1. Stop the etcd upgrade process if still in progress.
2. Restore etcd from the previous snapshot: `etcdctl snapshot restore <snapshot-id> --data-dir /var/lib/etcd/new`.
3. Restart the etcd service and verify `kubectl get nodes` shows all Ready.
4. If the new etcd version is incompatible, roll back to the etcd binary from the pre-upgrade snapshot.

#### Phase rollback — control plane upgrade

1. Drain the control-plane node being upgraded.
2. Revert the container image to the pre-upgrade version.
3. Restart the kube-apiserver, kube-scheduler, and kube-controller-manager pods.
4. Verify API server health: `kubectl get --raw=/readyz`.
5. Uncordon the node and confirm it returns to `Ready` status.

#### Phase rollback — worker node upgrade

1. Cordon the worker node.
2. Drain pods to other nodes (`kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`).
3. Revert kubelet and container runtime to the pre-upgrade version.
4. Uncordon the node and verify pods resume scheduling.

#### Phase rollback — CNI/ addon upgrade

1. Revert the CNI plugin manifest to the previous version.
2. Restart the CNI daemon set.
3. Verify networking connectivity: `kubectl get pods --all-namespaces`.
4. For addons, restart the addon deployment from the pre-upgrade image tag.

### E.3 Post-rollback validation

- `kubectl cluster-info` returns expected endpoints.
- All critical pods (`kube-system` namespace) are `Running` and `Ready`.
- API response times are within normal range.
- etcd database integrity check: `etcdctl check-database --write-out=table`.
- If any validation fails, repeat the rollup steps or escalate to the disaster recovery plan.

## F. Sign-off procedures

### F.1 Installation sign-off

| Role | Name | Date | Status |
|------|------|------|--------|
| Infrastructure Lead | | | ✅ Pass / ❌ Fail |
| Security Officer | | | ✅ Pass / ❌ Fail |
| Platform Operator | | | ✅ Pass / ❌ Fail |
| QA Lead | | | ✅ Pass / ❌ Fail |

**Installation sign-off requirements:**
- All pre-deployment checklist items (Section B) marked complete.
- All air-gapped validation checks (Section D) passed.
- etcd snapshot verified and stored.
- All critical cluster APIs responding.
- No critical alerts active in monitoring.

### F.2 Upgrade sign-off

| Phase | Result | Rollback Performed | Sign-off |
|-------|--------|-------------------|----------|
| Pre-upgrade validation | ✅ Pass / ❌ Fail | N/A | |
| etcd upgrade | ✅ Pass / ❌ Fail | ✅ Yes / ❌ No | |
| Control plane upgrade | ✅ Pass / ❌ Fail | ✅ Yes / ❌ No | |
| Worker upgrade | ✅ Pass / ❌ Fail | ✅ Yes / ❌ No | |
| CNI upgrade | ✅ Pass / ❌ Fail | ✅ Yes / ❌ No | |
| Addon upgrade | ✅ Pass / ❌ Fail | ✅ Yes / ❌ No | |
| Post-upgrade validation | ✅ Pass / ❌ Fail | N/A | |

**Upgrade sign-off requirements:**
- All phases report ✅ Pass.
- No rollback was required, or all rollbacks were successfully completed and validated.
- Post-upgrade air-gapped validation (Section D) all passed.
- Monitoring shows no critical errors for >1 hour post-upgrade.
- Security team confirms no new vulnerabilities introduced.

### F.3 Archive and documentation

- Record the completed sign-off sheet in the cluster's documentation repository.
- Tag the `offline-artifacts/artifact-matrix.md` with the new version and date.
- Store the etcd snapshots and rollback logs in the internal artifact repository per retention policy.
- Notify the on-call team and update the change management system (e.g., JIRA, ServiceNow).

---
**DevOps Automator**: Offline installation and upgrade procedure documented.
**Document path**: `offline-artifacts/offline-install-upgrade-procedure.md`
**Generated**: $(date +%Y-%m-%d)