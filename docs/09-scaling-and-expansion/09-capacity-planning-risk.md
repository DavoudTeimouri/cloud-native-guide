# 09 · Capacity Planning & Risk

## Purpose and scope
Capacity planning, growth estimates, failure tolerance, risk analysis, overcommit considerations.

## Capacity planning
- Forecast resource needs based on growth rate
- Plan hardware procurement lead time
- Monitor utilization trends; alert at 70%/80%
- Plan for failure tolerance (N+1, 2N)

## Risk analysis
- Single point of failure identification
- Mitigation: redundancy, HA, backups
- Rollback procedures for changes
- Disaster recovery drills

## Overcommit considerations
- CPU overcommit: safe for bursty workloads; risky for CPU-bound
- Memory overcommit: NOT recommended; causes OOM kills
- Storage overcommit: monitor actual usage; thin provisioning risk

## Related
- [01 · Overview (1.2 Reference Architectures)](../01-overview-and-architecture/1.2-reference-architectures.md)
- [01 · Overview (1.3 Infrastructure Sizing)](../01-overview-and-architecture/1.3-infrastructure-sizing-and-resource-calculation.md)
- [07 · Software-Defined Storage (7.2 Best Practices)](../07-software-defined-storage/7.2-best-practices.md)
