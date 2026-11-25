# Section 4: Kubernetes and Kubespray Upgrade

*Illustrative only — not production-committed configurations. No live cluster is upgraded from this document. All examples are version-dependent and labeled as such.*

## 4.1 Supported upgrade paths

Kubespray release-2.32 (pinned per `catalog/catalog.json`) supports Kubernetes v1.36.x → v1.37.x one-minor-skew upgrades. Version-skipping (e.g., v1.35.x → v1.37.x) is NOT supported; intermediate upgrade steps are required.

| From | To | Supported | Notes |
|---|---|---|---|
| v1.35.x | v1.36.x | Yes | via Kubespray release-2.31/2.32 |
| v1.36.x | v1.37.x | Yes | via Kubespray release-2.32 |
| v1.35.x | v1.37.x | No | version-skipping unsupported |
| v1.36.x | v1.38.x | No | version-skipping unsupported |

Do not assume all Kubespray releases support identical configuration variables or upgrade behavior. Review the Kubespray release notes and inventory variable changes for the target release before upgrading.

## 4.2 Pre-upgrade inventory

1. Record current versions: `kubectl version`, `kubectl get nodes`, etcd version, containerd version, CNI plugin version.
2. Inventory CustomResourceDefinitions and admission webhooks (see `lifecycle/crd-api-migration.md`).
3. Verify etcd backup is valid and recent (see `operations/kubernetes-control-plane-backup-restore.md`).
4. Confirm control-plane nodes are healthy: `kubectl get componentstatuses`.
5. Check pending pod disruptions: `kubectl get pdb`.
6. Verify worker node count and capacity can absorb one control-plane or worker upgrade at a time.

## 4.3 Version pinning

Pin all Kubernetes-related packages to the versions in `lifecycle/version-compatibility-matrix.conf`:

- `kubeadm`, `kubelet`, `kubectl` — same minor version on all nodes.
- `containerd` — pinned runtime version.
- CNI plugins — pinned version compatible with target Kubernetes.

Do not mix minor versions across control-plane nodes during upgrade.

## 4.4 Ansible/Kubespray configuration review

Before upgrading:

1. Review `kubespray` inventory for release-2.32 variable changes.
2. Verify `kube_version`, `etcd_version`, `containerd_version` variables match the target.
3. Review `kube_network_plugin` (cilium/calico) compatibility with target Kubernetes.
4. Test the inventory in a staging/lab cluster first.

## 4.5 Upgrade procedure (representative, illustrative)

Control plane first, then workers:

1. Upgrade etcd (backup first; see Section 4.2).
2. Upgrade first control-plane node: `kubeadm upgrade apply v1.37.x`.
3. Upgrade remaining control-plane nodes one at a time.
4. Upgrade worker nodes one at a time:
   - `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`
   - `kubeadm upgrade node`
   - `kubectl uncordon <node>`
5. Verify each node is `Ready` before proceeding to the next.

Drain and uncordon require PDBs to allow evacuation; verify `kubectl get pdb` before draining.

## 4.6 API deprecation checks

Before upgrading, identify deprecated/removed APIs:

```bash
# Illustrative — check for deprecated API usage in cluster events
kubectl get events -A | grep -i "deprecated\|removed"
# Review kube-apiserver logs for storage version warnings
```

Do not delete CRDs as a generic upgrade procedure (see `lifecycle/crd-api-migration.md`).

## 4.7 CNI, CSI, container runtime compatibility

- Confirm CNI plugin version supports target Kubernetes API version before upgrading K8s.
- Confirm CSI driver version supports target Kubernetes (see dependency group `Kubernetes & CSI` in `lifecycle/upgrade-sequencing.md`).
- Confirm containerd version is pinned per `version-compatibility-matrix.md`.

## 4.8 Add-on compatibility

Verify add-ons (cert-manager, ingress-nginx, Argo CD, Gatekeeper/Kyverno, Prometheus, etc.) support the target Kubernetes version before upgrading the control plane. See `lifecycle/version-compatibility-matrix.md`.

## 4.9 Common failure scenarios

| Symptom | Likely cause | Recovery |
|---|---|---|
| Control plane not Ready after upgrade | etcd mismatch, kubelet version skew | Restore etcd from backup; reconcile kubelet versions |
| Pods stuck Pending | CNI not ready, PDB blocking drain | Verify CNI daemonset; adjust PDB |
| Admission webhook failures | Gatekeeper/Kyverno webhook API mismatch | Temporarily bypass webhooks only with specialist review |

## 4.10 Post-upgrade verification

- `kubectl get nodes` — all `Ready`.
- `kubectl get componentstatuses` — all `Healthy`.
- `kubectl version` — client/server aligned.
- CoreDNS pods running; DNS resolution test from a pod.
- Deploy a test workload; confirm it schedules and runs.

---

*SND 004-P11.6 — Kubernetes and Kubespray Upgrade (illustrative)*
