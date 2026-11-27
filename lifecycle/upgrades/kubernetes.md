# Kubernetes Upgrade Procedure

## A. Purpose and scope

Document the Kubernetes minor-version upgrade procedure using Kubespray. Referenced by `kubespray/kubespray-deployment.md` Section J (Upgrades).

This procedure covers the upgrade-order checklist, etcd upgrade, CNI/CSI considerations, and rollback path.

## B. Prerequisites

| Prerequisite | Source |
|--------------|--------|
| Kubespray release pinned in `kubespray/VERSION` | `kubespray/kubespray-deployment.md` §M |
| Inventory and group vars in Git | `kubespray/kubespray-deployment.md` §M |
| etcd snapshot taken before upgrade | Section F below |
| New `kube_version` verified against compatibility matrix | `compatibility/version-matrix.md` |
| Ansible version compatible with target Kubespray release | `compatibility/version-matrix.md` |

## C. Upgrade constraints

- Kubernetes supports only one minor version skew in each direction. Do not skip minors.
- The kubeadm version must be compatible with the target Kubernetes version.
- etcd is upgraded as part of the node upgrade.
- CNI and CSI may need separate upgrades. Plan them explicitly.
- Rollback of a Kubernetes minor version is not supported. Take a snapshot before starting.

## D. Upgrade order

1. **Take etcd snapshot** (Section F)
2. **Upgrade control-plane nodes one at a time** (Section E)
3. **Upgrade worker nodes one at a time** (Section E)
4. **Verify cluster health** (Section G)
5. **Update kubespray/VERSION and group vars** to the new release

## E. Node upgrade sequence (one at a time)

### Control-plane nodes

```bash
# 1. Update kube_version in group_vars/k8s_cluster/k8s-cluster.yml
# 2. Commit the change to Git
# 3. Run Kubespray for one control-plane node
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-1

# 4. Verify node is Ready
kubectl get nodes k8s-cp-1

# 5. Verify etcd member is healthy
kubectl -n kube-system exec etcd-k8s-cp-1 -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster

# 6. Repeat for the next control-plane node
```

**Never upgrade all control-plane nodes simultaneously** — this removes etcd quorum and makes the cluster unreachable.

### Worker nodes

```bash
# 1. Drain the worker
kubectl drain k8s-w-1 --ignore-daemonsets --delete-emptydir-data

# 2. Run Kubespray for one worker node
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-1

# 3. Uncordon the worker
kubectl uncordon k8s-w-1

# 4. Verify node is Ready and pods are running
kubectl get nodes k8s-w-1
kubectl get pods -o wide --field-selector spec.nodeName=k8s-w-1

# 5. Repeat for the next worker node
```

## F. etcd snapshot before upgrade

```bash
# Take snapshot on one etcd member
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd/snapshot-pre-upgrade-$(date +%F).db

# Verify snapshot
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  snapshot status /var/lib/etcd/snapshot-pre-upgrade-$(date +%F).db

# Move snapshot off the node
kubectl -n kube-system cp etcd-<node>:/var/lib/etcd/snapshot-pre-upgrade-$(date +%F).db \
  /tmp/snapshot-pre-upgrade-$(date +%F).db
```

## G. Post-upgrade verification

```bash
# All nodes Ready
kubectl get nodes

# All system pods running
kubectl -n kube-system get pods

# etcd cluster healthy
kubectl -n kube-system exec etcd-<node> -- etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  endpoint health --cluster

# API server ready
kubectl get --raw='/readyz?verbose'

# Version matches target
kubectl version --short
```

## H. Rollback

Kubernetes minor-version rollback is **not supported**. If an upgrade fails:

1. Restore etcd from the pre-upgrade snapshot (Section F)
2. Revert group_vars and kubespray/VERSION to the previous values
3. Re-run Kubespray on affected nodes
4. Verify cluster health (Section G)

## I. Cross-references

- `kubespray/kubespray-deployment.md` §J — Upgrades (references this document)
- `kubespray/kubespray-deployment.md` §M — Best practices (pin release, keep inventory in Git)
- `lifecycle/upgrades/kubespray.md` — Kubespray-specific upgrade procedure
- `compatibility/version-matrix.md` — Version pins and compatibility
- `lifecycle/backup/backup-and-dr.md` — etcd backup RPO/RTO
