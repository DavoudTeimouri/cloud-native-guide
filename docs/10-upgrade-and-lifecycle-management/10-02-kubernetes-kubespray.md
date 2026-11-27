# Kubernetes & Kubespray

## Purpose and scope
K8s and Kubespray version upgrades; upgrade order, etcd backup, one control-plane node at a time.

## Steps
1. Check version compatibility matrix
2. Backup etcd snapshot
3. Upgrade control plane one node at a time
4. Upgrade workers
5. Verify cluster healthy

## Implementation
```bash
# Backup etcd
etcdctl snapshot save /var/lib/etcd/snapshot-$(date +%F).db \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Upgrade Kubespray release
cd /opt/kubespray
git checkout release-2.33
ansible-playbook -i inventory/<cluster>/hosts.ini upgrade-cluster.yml

# Verify
kubectl get nodes
kubectl get --raw='/readyz?verbose'
etcdctl endpoint health --cluster
```

## Rules
- Never skip a minor version; K8s supports one minor of skew each direction
- Pin target version in compatibility matrix before starting
- One control-plane node at a time to preserve etcd quorum
- Backup etcd before upgrade

## Validation
- All nodes Ready; version matches target
- etcd healthy; readyz all ok

## Related
- [Kubernetes Infrastructure (6.3 Deployment Methods)](../06-kubernetes-infrastructure/6.3-deployment-methods.md)
- [Kubernetes Infrastructure (6.4 Management Cluster Deployment)](../06-kubernetes-infrastructure/6.4-mgmt-cluster-deployment.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
