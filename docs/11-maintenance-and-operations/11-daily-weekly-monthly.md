# Daily, Weekly, Monthly Operations

## Purpose and scope
Daily health checks, weekly checks, monthly checks — routine operational procedures.

## Daily
- Check cluster health: kubectl get nodes, ceph -s, Prometheus targets
- Check alertmanager for firing alerts
- Check backup jobs completed
- Check disk usage on critical nodes

## Weekly
- Review security scan results (Trivy, Falco)
- Review log retention and rotation
- Check certificate expiry (14/7 day warnings)
- Review cost/capacity trends

## Monthly
- Apply security patches to OS/container runtime
- Rotate certificates/keys as needed
- Review and test backup restore
- Review audit logs for anomalies

## Implementation
```bash
# Daily health check
kubectl get nodes
ceph -s
promtool check rules /etc/prometheus/rules/*.yml

# Weekly security scan
trivy image <image>
kubectl get events -A --sort-by=.lastTimestamp

# Monthly certificate check
openssl x509 -in <cert> -text -noout | grep "Not After"
```

## Validation
- All nodes Ready; ceph HEALTH_OK
- No critical/firing alerts unacknowledged
- Backups completed successfully
- Certificates not expired

## Related
- [Kubernetes Infrastructure (6.15 Alert Management)](../06-kubernetes-infrastructure/6.14-alert-management.md)
- [Software-Defined Storage (7.7 Maintenance and Data Protection)](../07-software-defined-storage/7.7-maintenance-and-data-protection.md)
