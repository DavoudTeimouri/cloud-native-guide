# Storage & Cluster Health

## Purpose and scope
Storage health, Ceph health, cluster health monitoring.

## Storage health
- Ceph: ceph -s; MON/MGR/OSD/MDS/RGW healthy; PGs active+clean
- Rook-Ceph: CephCluster Created/Ready; PVCs Bound
- Longhorn: volumes Healthy; replicas Running
- StorageClasses: available; storage capacity sufficient

## Cluster health
- Kubernetes: all nodes Ready; all system pods Running
- etcd: quorum preserved; all members healthy
- API server: readyz all ok
- Control plane: no tainted/unready nodes

## Implementation
```bash
# Storage health
ceph -s
ceph osd stat
ceph pg stat
kubectl get storageclass
kubectl get pvc

# Cluster health
kubectl get nodes
kubectl get pods -A
kubectl get --raw='/readyz?verbose'
etcdctl endpoint health --cluster \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
```

## Validation
- Ceph HEALTH_OK; all OSDs up/in; PGs active+clean
- All nodes Ready; all system pods Running
- etcd healthy; readyz all ok

## Related
- [07 · Software-Defined Storage (7.6 Monitoring and Logging)](../07-software-defined-storage/7.6-monitoring-and-logging.md)
- [06 · Kubernetes Infrastructure (6.17 Validation and Acceptance Testing)](../06-kubernetes-infrastructure/6.17-validation-and-acceptance-testing.md)
