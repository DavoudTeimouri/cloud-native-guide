# Kubernetes Node Upgrade Procedure

## A. Purpose and scope

Document the Kubernetes node upgrade procedure for clusters managed by Kubespray. This procedure covers node draining, kubeadm and kubelet upgrades, CNI compatibility verification, rollback, and validation steps. Cross-references `kubespray/kubespray-deployment.md` §Node lifecycle, `lifecycle/upgrades/kubernetes.md` §D — Upgrade order.

## B. Prerequisites

| Prerequisite | Source |
|---|---|
| Kubespray release pinned in `kubespray/VERSION` | `kubespray/kubespray-deployment.md` §M |
| Inventory and group vars in Git | `kubespray/kubespray-deployment.md` §M |
| etcd snapshot taken before upgrade | Section F below |
| New `kube_version` verified against compatibility matrix | `compatibility/version-matrix.md` |
| CNI plugin version compatible with target Kubernetes version | `compatibility/version-matrix.md` |
| Ansible version compatible with target Kubespray release | `compatibility/version-matrix.md` |

## C. Upgrade constraints

- Upgrade one node at a time; never upgrade all nodes simultaneously
- Control-plane nodes must be upgraded before worker nodes
- Kubernetes supports only one minor version skew in each direction. Do not skip minors.
- The kubeadm version must be compatible with the target Kubernetes version.
- CNI and CSI may need separate upgrades. Plan them explicitly.
- Rollback of a Kubernetes minor version is not supported. Take a snapshot before starting.
- Drain each node only after verifying no critical pods are stuck in `Terminating` state.

## D. Upgrade order

1. **Upgrade control-plane nodes one at a time** (Section E — control-plane)
2. **Upgrade worker nodes one at a time** (Section E — worker)
3. **Verify cluster health** (Section G)
4. **Update kubespray/VERSION and group vars** to the new release

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

## G. kubeadm upgrade path

### kubeadm control-plane upgrade (control-plane nodes)

```bash
# On each control-plane node, upgrade kubeadm and the control-plane components
sudo kubeadm upgrade apply v<VERSION> \
  --config=/etc/kubernetes/kubeadm-config.yaml

# Verify the upgrade
kubectl get nodes
kubectl version --short
```

### kubelet upgrade

```bash
# On all nodes (control-plane and worker)
sudo apt-get update && sudo apt-get install -y kubelet=<VERSION>-00
sudo systemctl restart kubelet

# Verify kubelet version
kubelet --version
```

**After kubelet upgrade**, verify that all pods are running and the node reports the correct version.

## H. CNI compatibility verification

After upgrading Kubernetes nodes, verify CNI plugin compatibility:

```bash
# Check CNI plugin version compatibility
kubectl get cni -n kube-system

# Verify pod networking is functional
kubectl run test-pod --image=nginx --restart=Never
kubectl get pods -o wide

# Check CNI status
kubectl describe cnf -n kube-system <cni-plugin-name>
```

If the CNI plugin requires a separate upgrade:

1. Upgrade the CNI plugin DaemonSet to the version compatible with the new Kubernetes version
2. Verify networking continues to function
3. Confirm no CNI-related pod errors in logs

## I. Rollback

Kubernetes minor-version rollback is **not supported**. If an upgrade fails:

1. **Restore etcd** from the pre-upgrade snapshot (Section F)
2. **Revert group_vars and kubespray/VERSION** to the previous values
3. **Re-run Kubespray** on affected nodes using the previous release
4. **Verify cluster health** (Section G)

**Important**: Take an etcd snapshot before starting any upgrade. Without a snapshot, rollback is impossible.

## J. Validation steps

After completing the upgrade of all nodes, run the following validations:

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

# CNI networking functional
kubectl run test-pod --image=nginx --restart=Never
kubectl get pods -o wide

# No CNI-related errors
kubectl logs -n kube-system -l k8s-app=<cni-plugin> | grep -i "error\|fail"
```

## K. Cross-references

- `kubespray/kubespray-deployment.md` §I — Node lifecycle
- `kubespray/kubespray-deployment.md` §J — Upgrades
- `kubespray/kubespray-deployment.md` §M — Best practices (pin release, keep inventory in Git)
- `lifecycle/upgrades/kubernetes.md` — Kubernetes upgrade procedure (cluster-wide)
- `lifecycle/upgrades/kubespray.md` — Kubespray-specific upgrade procedure
- `compatibility/version-matrix.md` — Version pins and compatibility
- `kubernetes/control-plane/index.md` §Failure scenarios — Control-plane failure scenarios
