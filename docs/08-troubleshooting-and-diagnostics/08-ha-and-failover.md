# HA and Failover

## Symptoms
- Control plane VIP not failing over
- etcd quorum lost
- Node failure not triggering pod reschedule
- Load balancer not failing over
- Service disruption during node maintenance

## Possible causes
- Keepalived misconfigured or not running
- etcd member down; quorum below majority
- Pod not reschedulable (PDB, taints, node selector)
- LB health check misconfigured
- PodDisruptionBudget too restrictive

## Diagnostic commands
```bash
# Keepalived/VIP
systemctl status keepalived
ip addr show | grep <vip>
keepalived status

# etcd
kubectl get --raw='/readyz?verbose'
etcdctl endpoint health --cluster \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key

# Pod scheduling
kubectl get pods -o wide
kubectl describe pod <pod>
kubectl get poddisruptionbudget -A

# Nodes
kubectl get nodes
kubectl describe node <node>
```

## Expected output
- keepalived: master/backup state; VIP on master
- readyz: all ok
- etcdctl: all healthy
- pods: rescheduled to healthy nodes; PDB allowing eviction

## Investigation procedure
1. Check keepalived status and VIP ownership
2. Check etcd health and quorum
3. Check node status; identify failed node
4. Check pod scheduling; check PDB restrictions
5. Check LB health check configuration

## Resolution
- Fix keepalived; correct VRRP configuration
- Replace failed etcd node (one at a time); restore from snapshot if quorum lost
- Drain failed node; pods reschedule
- Adjust PDB to allow eviction
- Fix LB health check

## Verification
- VIP fails over between nodes; etcd quorum preserved; pods reschedule on node failure; service remains available

## Prevention
- Monitor keepalived/VIP ownership; alert on failover
- Monitor etcd quorum; alert on member down
- Monitor node health; alert on NotReady
- Test failover regularly; include in DR drills

## Related
- [Kubernetes Infrastructure (6.17 Validation and Acceptance Testing)](../06-kubernetes-infrastructure/6.17-validation-and-acceptance-testing.md)
- [Software-Defined Storage (7.7 Maintenance and Data Protection)](../07-software-defined-storage/7.7-maintenance-and-data-protection.md)
- [Maintenance and Operations](../11-maintenance-and-operations/index.md)
