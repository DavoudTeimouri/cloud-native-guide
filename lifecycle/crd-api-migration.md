# Section 9: CRD, API and Configuration Migration

*Illustrative only — not production-committed configurations. No live cluster is modified from this document. All examples are version-dependent and labeled as such.*

## 9.1 Kubernetes API deprecations and removals

Before upgrading Kubernetes, identify deprecated/removed APIs in the target version:

1. Review the Kubernetes release notes for the target version (API removals are announced one minor release in advance).
2. `kubectl get --raw "/apis"` — list served API groups and versions.
3. `kubectl get --raw "/openapi/v2"` — inspect API schemas for `x-kubernetes-deprecation` markers.
4. Review `kube-apiserver` logs for `storage_version_warnings` and deprecated API usage.

Deprecated APIs remain served but warn; removed APIs cause `kubectl apply` failures. Migrate workloads off removed APIs before upgrading.

## 9.2 CRD version transitions

CRDs can have multiple stored versions (e.g., `v1` and `v1beta1`). Version transitions:

- Conversion webhooks handle stored data migration between versions.
- Before upgrading, confirm conversion webhooks are healthy: `kubectl get conversionwebhookconfigurations` (if applicable) or check webhook pod logs.
- Check which version is `served` and `storage`: `kubectl get crd <name> -o yaml` → `spec.versions[*].served` and `.storage`.
- Do not delete CRDs as a generic upgrade or troubleshooting procedure — this deletes all instances of that custom resource.

## 9.3 Conversion webhooks

If a CRD uses a conversion webhook, the webhook must be available during upgrade:

```bash
# Illustrative — check webhook pod status
kubectl get pods -l app.kubernetes.io/name=<webhook-name>
kubectl logs -l app.kubernetes.io/name=<webhook-name>
```

## 9.4 Helm release migration

- Review `helm list -A` for releases that use deprecated APIs.
- `helm template <release> <chart>` — render manifests and compare against current cluster state.
- Helm chart value schema changes between major versions; review `values.yaml` changes before upgrading.

## 9.5 Configuration schema changes

Operators and controllers may change config schema between versions:

- Review operator release notes for config field deprecations.
- Validate config against the new schema before applying (e.g., `kubectl apply --dry-run=server`).
- Operator upgrade ordering: upgrade the operator CRD first, then the operator Deployment, then custom resources.

## 9.6 Admission webhook availability

Admission webhooks (Gatekeeper, Kyverno, cert-manager, etc.) intercept create/update requests. During upgrade:

- Ensure webhook pods are running and healthy before upgrading workloads that depend on them.
- A failing webhook can block `kubectl apply` and Helm upgrades.
- Temporarily bypassing webhooks is a specialist-review-only action.

## 9.7 Backup and recovery of custom resources

Custom resources are stored in etcd and backed up with etcd snapshots:

- Back up etcd before any CRD/API migration (see `operations/kubernetes-control-plane-backup-restore.md`).
- `kubectl get <crd> -A -o yaml` — export custom resources for reference before migration.
- After API migration, verify custom resources are intact and webhooks accept them.

## 9.8 GitOps synchronization behavior

Argo CD reconciles from Git to cluster. During API migration:

- Argo CD may report `OutOfSync` if Git manifests use removed APIs.
- Update Git manifests to target API versions before upgrading the cluster.
- Pause Argo CD sync during the migration window if needed: `argocd app sync-pause <app>`.
- Resume after cluster API migration is validated: `argocd app sync-resume <app>`.

## 9.9 Identifying deprecated APIs before upgrade

```bash
# Illustrative — list API groups and versions
kubectl get --raw "/apis" | jq '.groups[].name'

# Illustrative — check for deprecation warnings in events
kubectl get events -A --sort-by=.lastTimestamp | grep -i "deprecated\|remov"
```

Review `kube-apiserver` flags `--runtime-config` to confirm which API versions are enabled.

## 9.10 Limitations

- Do not delete CRDs as a generic upgrade/troubleshooting procedure.
- Do not assume the newest release is automatically compatible with existing CRDs.
- Record source URLs and verification dates for all compatibility claims (see `lifecycle/version-compatibility-matrix.md`).

---

*SND 004-P11.6 — CRD, API and Configuration Migration (illustrative)*
