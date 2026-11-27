# On-call Rotation Register

Incident on-call schedule, escalation contacts, and notification routing for the cloud-native platform.

## Rotation schedule

| Role | Name | Slack / Matrix | Phone | Rotation | Escalates to |
|------|------|----------------|-------|----------|--------------|
| On-call lead (P0/P1 primary) | `<user-decision>` | `<user-decision>` | `<user-decision>` | Weekly | On-call secondary |
| On-call secondary (P0/P1 backup) | `<user-decision>` | `<user-decision>` | `<user-decision>` | Weekly | Escalation contact |
| Escalation contact (standing) | `<user-decision>` | `<user-decision>` | `<user-decision>` | Standing | Platform lead |

Rules:
- Rotate weekly. The on-call lead owns P0/P1 escalation; the secondary covers absence.
- P0 auto-escalates to on-call lead after 1 hour (`troubleshooting/runbooks-and-checklists.md`).
- P1 escalates after 2 hours if no progress.
- Break-glass path is used when the normal path is unavailable, not only when convenient. Every break-glass use is reviewed.

## Internal alert routing (air-gapped)

PagerDuty and Slack are SaaS and unreachable in the air-gapped environment. Route alerts to an internal target:

| Severity | Internal route | External fallback |
|----------|---------------|-------------------|
| Critical | Internal SMTP smarthost / Matrix room `#critical-alerts` | PagerDuty (connected env only) |
| Warning | Internal SMTP smarthost / Matrix room `#warnings-alerts` | Slack (connected env only) |
| Info | Internal SMTP smarthost / Matrix room `#info-alerts` | None |

**User decision:** Select the internal notification target (SMTP list or Matrix room) and record it above. Update `monitoring/alertmanager-configuration.md` receivers accordingly.
