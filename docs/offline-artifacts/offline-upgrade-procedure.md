# Offline Upgrade Procedure

## A. Purpose and scope

Document offline upgrade procedure: upgrade Kubespray release, Kubernetes version, images, OS packages without internet.

Cross-references `offline-artifacts/artifact-matrix.md`, `kubespray/multi-version-support.md`, `lifecycle/upgrades/kubernetes.md`.

## B. Upgrade phases

| Phase | Action | Downtime |
|-------|--------|----------|
| 1. Inventory new artifacts | Download new images/packages to internal mirror | None |
| 2. Validate artifacts | Verify signatures, checksums, SBOMs | None |
| 3. Upgrade etcd | Rolling etcd upgrade one member at a time | Minimal |
| 4. Upgrade control plane | Rolling kube-apiserver/scheduler/controller-manager upgrade | Minimal |
| 5. Upgrade workers | Drain, upgrade, uncordon one node at a time | Per node |
| 6. Upgrade CNI | Rolling Cilium upgrade | Minimal |
| 7. Upgrade addons | Ingress, metrics-server, etc. | Minimal |

## C. Offline artifact inventory

Before upgrading, inventory all artifacts:

```bash
# List images required by new Kubespray release
cat inventory/<cluster>/group_vars/k8s_cluster/k8s-cluster.yml | grep image

# Verify images exist in internal registry
skopeo inspect docker://registry.internal/k8s.gcr.io/kube-apiserver:v1.36.5
```

## D. Step-by-step upgrade

### Phase 1: Inventory new artifacts

1. Pull new Kubespray release to internal Git mirror
2. Pull new images to internal registry
3. Pull new OS packages to internal mirror
4. Update artifact-matrix.md with new versions

### Phase 2: Validate artifacts

1. Verify image signatures with Cosign
2. Verify SBOMs with Trivy
3. Verify OS package checksums
4. Validate artifact-matrix.md consistency

### Phase 3: Upgrade etcd

1. Backup etcd snapshot (`kubernetes/control-plane/etcd-restore.md`)
2. Upgrade etcd binaries on one member
3. Verify etcd health
4. Repeat for remaining members

### Phase 4: Upgrade control plane

1. Run `kubespray upgrade playbook` on control-plane nodes
2. Verify `kubectl get nodes` shows all Ready
3. Verify API server health

### Phase 5: Upgrade workers

1. Cordon worker node
2. Drain pods to other nodes
3. Upgrade kubelet and container runtime
4. Uncordon node
5. Repeat for remaining workers

### Phase 6: Upgrade CNI

1. Deploy new Cilium version with `cilium upgrade`
2. Verify CNI connectivity

## E. Cross-references

- `offline-artifacts/artifact-matrix.md` — Artifact matrix
- `kubespray/multi-version-support.md` — Multi-version Kubespray
- `lifecycle/upgrades/kubernetes.md` — Kubernetes upgrade procedure
- `security/image-provenance.md` — Image signing and verification
