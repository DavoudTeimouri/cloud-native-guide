# Kubespray 2.32 Upgrade Validation

[Previous step](../kubespray/kubespray-deployment.md) | [Next step](../lifecycle/upgrades/kubespray.md)

---

## A. Pre-upgrade checks

- **Inventory consistency**: Diff existing inventory against the release-2.32 sample inventory. Never reuse a group-vars file across releases without diffing it first (`lifecycle/upgrades/kubespray.md`).
- **Ansible version**: Verify Ansible >=2.19.0, <2.20.0 (2.19.x) and Python 3.11-3.13 (`kubespray/multi-version-support.md`).
- **Image mirroring**: All Kubespray and Kubernetes images must be mirrored to the internal registry and pull-verified before starting the upgrade.
- **etcd backup**: Create a current etcd snapshot backup using `etcdctl snapshot save` before any upgrade operation. Store the backup in a safe, separate location.
- **Inventory in Git**: Ensure the inventory and group vars are committed to Git so the pre-upgrade state is reproducible.
- **Control-plane quorum**: Verify the cluster has healthy control-plane quorum (3 members) before starting. Do not upgrade if quorum is lost.
- **Kubernetes minor version skew**: Kubespray 2.32 targets Kubernetes 1.36.x. Ensure the current cluster is on a compatible minor version (within one minor skew). Do not skip minors.
- **CNI/CSI compatibility**: Verify CNI (Cilium) and CSI driver versions are compatible with Kubernetes 1.36. Plan separate upgrades if needed.
- **Node resource health**: All nodes should be healthy with no critical alerts. Resolve any existing issues before upgrading.
- **Application awareness**: Notify application teams of the upgrade window. Ensure applications can handle graceful node draining and restart.

## B. Upgrade execution

- **One node at a time**: Upgrade control-plane nodes first, one at a time, preserving etcd quorum. Do not upgrade multiple control-plane nodes simultaneously.
- **Sequential worker upgrade**: After control-plane nodes are upgraded, upgrade worker nodes one at a time. Drain each node before upgrading and allow it to rejoin the cluster.
- **Kubespray playbook**: Run `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml` after updating `kube_version` in group vars to the target 2.32 release version.
- **Syntax and dry-run check**: Before each real run, execute `ansible-playbook ... --syntax-check` and `ansible-playbook ... -b --check --diff --limit control-plane` to validate changes.
- **etcd upgrade**: The etcd version is upgraded as part of the node upgrade process. Verify etcd health after each control-plane node upgrade using `etcdctl --endpoints=https://127.0.0.1:2379 endpoint health --cluster`.
- **CNI/CSI upgrade**: If the CNI or CSI drivers require a separate upgrade, execute those upgrades after the Kubernetes version upgrade, following the respective component's upgrade guide.
- **Verification after each node**: After each node upgrade, verify: `kubectl get nodes`, `kubectl get --raw='/readyz?verbose'`, and application health checks.

## C. Post-upgrade validation

- **Cluster health**: `kubectl get nodes` — all nodes Ready. `kubectl get --raw='/readyz?verbose'` — all checks passing.
- **Control-plane quorum**: Verify etcd quorum using `etcdctl --endpoints=https://127.0.0.1:2379 endpoint health --cluster`.
- **Kubernetes version**: Confirm `kubectl version --client` and `kubectl version --output=json` report the target 2.32 version.
- **CNI and CSI**: Verify Cilium version and CSI driver version are correct for Kubernetes 1.36.
- **Core addons**: Confirm CoreDNS, kube-proxy, and other addons are running and healthy: `kubectl -n kube-system get pods`.
- **Application smoke tests**: Run application-level health checks and smoke tests to confirm workloads are scheduling and running correctly on the new version.
- **Rollback test (documented)**: Review the rollback procedure in section D. Ensure the etcd backup and inventory git commit are available as a known-good restore point.
- **Monitoring validation**: Verify Prometheus/Grafana metrics are scraping correctly and no new alert firings have occurred post-upgrade.

## D. Rollback procedure

- **Restore etcd from snapshot**: If the upgrade fails or causes irreversible damage, restore etcd from the pre-upgrade snapshot: `etcdctl snapshot restore /tmp/etcd-backup-<date>.db --data-dir /var/lib/etcd/new`.
- **Revert inventory changes**: Reset the inventory to the pre-upgrade state by reverting the Git commit that updated group vars and inventory for the 2.32 release.
- **Control-plane rollback (one at a time)**: If a control-plane node upgrade failed partway through, drain the node and re-apply the previous `cluster.yml` to restore it. Repeat for any other control-plane nodes that were partially upgraded. Preserve quorum at all times — do not roll back all control-plane nodes simultaneously.
- **Worker node rollback**: Drain the affected worker node and re-apply the previous `cluster.yml` to restore it to the prior Kubernetes version.
- **Post-rollback validation**: After restoring etcd and reverting inventory, validate cluster health: `kubectl get nodes`, `kubectl get --raw='/readyz?verbose'`, etcd endpoint health, and application functionality.
- **Document the incident**: Record the upgrade failure, rollback actions taken, and lessons learned. Update the inventory and group vars only after the root cause is understood and remediated.

---

[Previous step](../kubespray/kubespray-deployment.md) | [Next step](../lifecycle/upgrades/kubespray.md)
