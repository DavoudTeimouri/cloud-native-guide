# Expanding Repo, Monitoring, LB

## Purpose and scope
Expand registry capacity, monitoring infrastructure, load balancers.

## Registry expansion (Harbor/Nexus)
- Add storage volume to Harbor/Nexus
- Add replica for HA
- Update object storage bucket size

```bash
# Harbor: expand PVC
kubectl patch pvc harbor-registry -n harbor --type merge -p '{"spec":{"resources":{"requests":{"storage":"500Gi"}}}'
```

## Monitoring expansion
- Add Prometheus server replica
- Increase retention period
- Add Grafana datasource capacity

```yaml
# Prometheus scrape config expansion
- job_name: 'new-target'
  static_configs:
    - targets: ['<new-target>:9100']
```

## Load balancer expansion
- Add MetalLB IP pool range
- Add HAProxy/Nginx backend
- Add keepalived VRRP instance

```bash
# MetalLB: expand IP pool
kubectl patch ipaddresspool <pool> --type merge -p '{"spec":{"addresses":[["10.61.0.10-10.61.0.50"]]}}'
```

## Validation
- Registry push/pull succeeds
- Prometheus targets healthy
- LB VIP failover works; backends healthy

## Related
- [Repository & Registry Management](../03-repository-registry/index.md)
- [Load Balancers and Traffic Management](../05-load-balancers/index.md)
- [Kubernetes Infrastructure (6.13 Monitoring and Logging)](../06-kubernetes-infrastructure/6.13-monitoring-and-logging.md)
