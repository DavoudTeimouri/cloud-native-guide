# Adding Application Clusters

## Purpose and scope
Prepare infrastructure/networking, deploy additional clusters, register with Rancher, apply consistent configuration.

## Steps
1. Prepare infrastructure (OS baseline, containerd, storage)
2. Prepare networking (CIDRs, VIPs, DNS)
3. Deploy cluster via Kubespray (09-expanding-k8s-clusters.md)
4. Apply consistent configuration (labels, taints, network policies)
5. Integrate storage (Ceph/Rook)
6. Integrate monitoring (Prometheus scrape, Loki shipping)
7. Register with Rancher (06-cluster-registration.md)
8. Apply centralized policies (Gatekeeper/Kyverno, PSS)

## Prerequisites
- Management cluster healthy (Rancher, Argo CD)
- Internal Harbor/Nexus reachable
- Network segments allocated (pod CIDR, service CIDR)

## Implementation
```bash
# Register with Rancher
# Generate cluster registration token in Rancher UI
# Install Rancher agent on new cluster
kubectl apply -f cluster-registration.yaml

# Register with Argo CD
kubectl apply -f argocd-application.yaml -n argocd
```

## Validation
- Cluster shows in Rancher UI
- Argo CD syncs applications to new cluster
- Prometheus scrapes new cluster targets

## Related
- [06 · Kubernetes Infrastructure (6.6 Additional Application Clusters)](../06-kubernetes-infrastructure/6.6-additional-clusters.md)
- [06 · Kubernetes Infrastructure (6.9 Cluster Registration)](../06-kubernetes-infrastructure/6.9-kubernetes-networking.md)
