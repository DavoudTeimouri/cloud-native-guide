# Step 12 — Upgrades, Retirement & Decommission

**Purpose**: Upgrade components in order, retire the community ingress-nginx controller, migrate Helm 3 to Helm 4, and decommission what is no longer needed. Re-run from Step 00 when any pinned version changes.

**Prerequisites**: Step 11 complete (day-2 operations validated); every backup verified before any change.

## 12.1 Upgrades

Every component upgrade follows: source → target, compatibility, pre-validation, offline artifact preparation, verified backup, dependency and upgrade order, canary, execution, post-checks, rollback feasibility, downtime, risks, success criteria. The authority is `../lifecycle/upgrades/upgrade-procedures.md`; `catalog/upgrades.json` mirrors the same gates and order.

Rules that apply to every upgrade:
- Never skip a minor version — Kubernetes supports one minor of skew in each direction.
- Pin, do not float — add the target to `compatibility/version-matrix.md` with a source URL and check date before starting.
- Mirror first, upgrade second — every target artifact is in the internal registry and pull-verified before any node is touched.
- Backup before the change — a verified backup, not "a backup exists".
- One node at a time for node-level components, with a health check between nodes.
- Canary first — run the upgrade on a staging copy of the production inventory.

Key paths:
- **Kubernetes**: Kubespray `cluster.yml` with a new `kube_version`; control plane first, then workers; rollback is not supported (recovery is the pre-upgrade etcd snapshot restore). See `../lifecycle/upgrades/kubernetes.md`.
- **Kubespray**: new release branch; diff inventory group-vars against the new release's `inventory/sample`; one control-plane node at a time to preserve etcd quorum. See `../lifecycle/upgrades/kubespray.md`.
- **OS / kernel / containerd**: package update + reboot; drain, upgrade, reboot, verify, uncordon. Retain the old kernel so the node-level change stays reversible.
- **etcd**: managed by Kubespray with the control-plane node; no rollback — take a snapshot first.

## 12.2 Ingress retirement: community ingress-nginx → F5 NIC

The community `kubernetes/ingress-nginx` is retired (no security fixes). Do not adopt it. Existing deployments keep running on their pinned version only.

- Migrate to the **F5 NGINX Ingress Controller** (F5 NIC) or NGINX Gateway Fabric. See `en/cloud-native-stack-step-by-step.md` Step 08 (install F5 NGINX IC chart 2.8.0 with Gateway API enabled) and `../lifecycle/upgrades/upgrade-procedures.md` (NGINX Ingress (F5) is reversible via Helm; the community ingress-nginx path is retired).

## 12.3 Helm 3 → Helm 4

Helm 3 is in support mode; security fixes end 2027-02-10. Helm 4 is the current stable line.

1. Read the Helm 4 release notes and the HIP-0012 migration notes for the pinned target version.
2. Install the Helm 4 binary alongside Helm 3 on the automation server and in the CI image — do not replace in place.
3. Run every chart install, upgrade, template, and lint with Helm 4 against the full chart set. Fix failures as MRs in the owning chart repositories.
4. Switch the CI image and automation scripts to Helm 4.
5. Keep the Helm 3 binary available until 2027-02-10, because Kubespray release-2.32 ships Helm 3.22.0 internally.

Rollback: the Helm 3 binary is kept, so rollback is a path change. Before removing the old binary, confirm any chart modified for Helm 4 still works with Helm 3.

See `../lifecycle/upgrades/upgrade-procedures.md` § Helm 3 to Helm 4.

## 12.4 Decommission

Decommission a component only after:
- Its workloads are migrated and verified on the replacement.
- A final backup is taken and stored off-site.
- The change record states the rollback feasibility (usually "No" for decommission).

Remove the component from `compatibility/version-matrix.md` and `offline-artifacts/artifact-matrix.md` only after the decommission window passes without incident.

---

[Next: Reference — Version & Compatibility Matrix →](../compatibility/version-matrix.md)
