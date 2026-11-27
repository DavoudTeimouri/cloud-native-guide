# 11 · Quarterly Capacity Review

## Purpose and scope
Quarterly reviews, capacity reviews, growth estimates.

## Quarterly review checklist
- Review resource utilization trends (CPU/memory/disk/network)
- Forecast growth based on historical usage
- Plan hardware procurement for next quarter
- Review Ceph OSD capacity and plan expansion
- Review registry/storage capacity and plan expansion
- Review monitoring/logging retention and storage
- Document capacity decisions and actions

## Implementation
```bash
# Resource utilization
kubectl top nodes
kubectl top pods
ceph df
df -h

# Growth forecast (example)
# Compute average monthly growth from monitoring data
# Plan hardware procurement based on forecast
```

## Validation
- Capacity forecast documented
- Hardware procurement planned
- Expansion projects scheduled

## Related
- [01 · Overview (1.2 Reference Architectures)](../01-overview-and-architecture/1.2-reference-architectures.md)
- [01 · Overview (1.3 Infrastructure Sizing)](../01-overview-and-architecture/1.3-infrastructure-sizing-and-resource-calculation.md)
- [09 · Scaling & Expansion (09-capacity-planning-risk)](../09-scaling-and-expansion/09-capacity-planning-risk.md)
