# Audit Logging

## A. Purpose and scope

Document audit logging for Kubernetes: audit policy levels, log destination, retention, analysis, alerting on audit failures.

Cross-references `kubernetes/security/security-controls.md` §Audit, `kubernetes/control-plane/index.md`, `lifecycle/backup/backup-and-dr.md`.

## B. Kubernetes audit policy

The API server audit policy controls what is logged. Metadata level is the default:

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages:
  - RequestReceived
rules:
  # Log nothing for system components watching endpoints
  - level: None
    users: ["system:kube-proxy", "system:node:agent"]
    verbs: ["watch"]
    resources: ["endpoints", "services", "endpointslices"]
  # Log nothing for garbage collector
  - level: None
    users: ["system:serviceaccount:kube-system:generic-garbage-collector"]
    verbs: ["get"]
    resources: [""]
  # Log request/response for secrets (sensitive)
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["secrets"]
  # Log metadata for other core resources
  - level: Metadata
    resources:
      - group: ""
        resources: ["pods", "pods/log", "configmaps"]
  - level: Metadata
    resources:
      - group: "authentication.k8s.io"
        resources: ["tokenreviews"]
  # Default: log nothing
```

## C. Audit log destination

Audit logs must be written to a local file, shipped off-host quickly, and kept out of the cluster's own failure domain:

```yaml
# kube-apiserver audit configuration
apiVersion: audit.k8s.io/v1
kind: AuditConfiguration
logPath: /var/log/kubernetes/audit.log
logMaxAge: 30
logMaxBackup: 10
logMaxSize: 100
policyFile: /etc/kubernetes/audit-policy.yaml
```

## D. Retention

| Log type | Retention | Storage |
|----------|-----------|---------|
| API server audit | 30 days | Local + off-host |
| Vault audit | 90 days | Local + off-host |
| Ceph audit | 30 days | Local + off-host |

## E. Analysis

Audit logs should be shipped to a central logging system (Loki/Elasticsearch) for analysis and alerting:

```bash
# Example: search audit logs for unauthorized access
grep "Unauthorized" /var/log/kubernetes/audit.log | tail -50

# Example: search for secret access
grep "secrets" /var/log/kubernetes/audit.log | grep "verb=get" | tail -50
```

## F. Alerting on audit failures

Alert when the audit pipeline fails (not just on audit log content):

- Audit log pipeline failure
- Audit disk usage > 85%
- Failed authentication attempts spike
- Unauthorized access attempts

## G. Cross-references

- `kubernetes/security/security-controls.md` §I — Audit
- `kubernetes/control-plane/index.md` — Control plane
- `lifecycle/backup/backup-and-dr.md` — Backup mechanics
