# Monitoring Review & Vulnerability Management

## Purpose and scope
Monitoring review, vulnerability management, security scanning.

## Monitoring review
- Review Prometheus/Grafana dashboards; alert rules relevant
- Review Alertmanager routing; no alert fatigue
- Review Loki/Fluent Bit log ingestion; no gaps
- Review recording rules; cardinality under control

## Vulnerability management
- Monthly Trivy image scans; critical/high vulnerabilities patched
- Monthly Gitleaks secret scans; secrets removed from Git
- Monthly Checkov IaC scans; misconfigurations remediated
- CVE announcements reviewed; affected components patched

## Implementation
```bash
# Trivy image scan
trivy image
trivy fs .

# Gitleaks
gitleaks detect --source .

# Checkov
checkov -d .
```

## Validation
- No critical/high vulnerabilities unremediated
- No secrets found in Git
- No IaC misconfigurations unremediated
- Monitoring dashboards/alerts reviewed and current

## Related
- [06 · Kubernetes Infrastructure (6.13 Monitoring and Logging)](../06-kubernetes-infrastructure/6.13-monitoring-and-logging.md)
- [06 · Kubernetes Infrastructure (6.14 Alert Management)](../06-kubernetes-infrastructure/6.14-alert-management.md)
- [06 · Kubernetes Infrastructure (6.16 Security and Identity)](../06-kubernetes-infrastructure/6.16-security-and-identity.md)
