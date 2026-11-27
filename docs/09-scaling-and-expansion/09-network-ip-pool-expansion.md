# 09 · Network & IP Pool Expansion

## Purpose and scope
Network expansion, IP pool expansion, CIDR changes.

## Steps
1. Plan new CIDR blocks; verify no overlap
2. Update network matrix and firewall rules
3. Update MetalLB IP pool
4. Update CoreDNS/ingress if needed
5. Validate connectivity

## Implementation
```bash
# MetalLB: expand IP pool
kubectl patch ipaddresspool <pool> --type merge -p '{"spec":{"addresses":[["10.61.0.10-10.61.0.100"]]}}'

# Add new service CIDR (requires cluster recreation in most cases)
# kube_service_addresses: "10.32.0.0/16, 10.33.0.0/16"
```

## Validation
- MetalLB allocates IPs from expanded pool
- Services get IPs from new range
- Connectivity between old and new CIDR blocks works

## Related
- [Shared network matrix](../shared/network-matrix/index.md)
- [05 · Load Balancers (5.3 Application Cluster Load Balancers)](../05-load-balancers/5.3-app-cluster-lbs.md)
