# Section 13: Production Readiness Checklist

## Mandatory Production Blockers (Must be resolved before go-live)

| Checklist Item | Description | Evidence Required | Owner | Status |
|---|---|---|---|---|
| **Control-plane quorum** | Minimum 3 control-plane nodes with etcd quorum; no split-brain risk | etcd member list; quorum verification script output; `ceph health` equivalent for K8s | Platform team | |
| **HA / failover validated** | HA configurations tested for all Tier 0–1 components; documented rollback paths | HA test exercise report; failover drill sign-off; recovery time measurements | SRE | |
| **Backup/restore verified** | Backup tested restore for etcd, Ceph, registry, Vault within declared RPO/RTO | Restore drill reports; backup integrity checks; RPO/RTO measurement data | SRE / Storage team | |
| **Security / access control** | All RBAC, OPA/Gatekeeper policies, Vault sealing, Keycloak realms audited and approved | Policy repo audit diff; OPA constraint test results; Vault unseal key storage review; Keycloak admin audit | Security team | |
| **Monitoring / alerting active** | All critical alerts firing; notification paths confirmed; dashboards populated with real data | Alert test results; notification delivery logs; dashboard sanity-check screenshots; alertmanager config review | SRE | |
| **Capacity / performance** | Utilization within SLO targets; headroom for expected peak; capacity plan approved | Resource utilization reports (CPU/mem/disk I/O); traffic forecast vs. capacity; headroom calculation | Platform team | |
| **Upgrade / rollback readiness** | Last known-good version recorded; rollback procedure documented and tested; dependency compatibility matrix | Rollback drill report; version compatibility matrix; dependency change log | Platform team | |
| **Documentation / ownership** | All runbooks current; on-call rotation assigned; escalation paths documented and tested | Runbook version tags; on-call schedule export; escalation matrix sign-off | Team leads | |
| **DR exercises completed** | Full-disaster recovery exercise conducted within past 12 months; all Tier 0–2 components exercised | DR exercise report; lessons learned document; target RPO/RTO comparison | Platform SRE | |
| **Offline / restricted-network readiness** | All critical images and charts available offline; no external dependencies at runtime; air-gap compatibility confirmed | Offline image mirror verification; air-gap addon test; disconnected cluster install test | Platform team | |

---

## Recommended Improvements (Should be addressed; may be deferred if error budget permits)

| Checklist Item | Description | Target Resolution | Owner |
|---|---|---|---|
| **Chaos engineering integration** | Failure injection tests (Pod kill, node loss, network partition) integrated into CI/CD pipeline | Next sprint | SRE |
| **SLO error-budget alerting** | Custom alerts for error budget consumption rate, not just threshold breaches | Next release | SRE |
| **Disaster recovery quarterly drills** | Reduce from annual to quarterly for Tier 0–2; tabletop for Tier 3–4 | Next quarter | Platform SRE |
| **Cross-region failover documented** | Multi-region failover runbook; RPO/RTO targets for cross-region restores | Next month | Platform team |
| **Automated compliance checks** | Sentinel/OPA policy as code CI check; drift detection on every PR | Next release | Security |
| **Runbook automation** | Ansible/terraform scripts to execute recovery procedures from runbook steps | Next quarter | Platform team |
| **Third-party SLA verification** | Confirm SaaS dependencies (monitoring, logging, source repos) SLA aligns with internal RPO/RTO | Ongoing | SRE |

---

## Environment-Dependent Decisions (If applicable, mark yes/no and provide justification)

| Decision | Value | Justification | Owner |
|---|---|---|---|
| **Air-gapped installation** | Yes / No | Whether the cluster must operate without internet access; affects image mirroring, chart availability, update flow | Platform team |
| **Single-control-plane mode** | Yes / No | Acceptable only for non-critical workloads; introduces single point of failure for API server | Platform SRE |
| **Ceph RGW standalone** | Yes / No | Whether RGW is the only image registry; impacts Tier 1 RPO/RTO targets | Storage team |
| **Runtime (containerd vs. cri-o)** | containerd / cri-o | Choice affects OS package dependencies, upgrade path, and CRI-specific features | Platform team |
| **OPA/Gatekeeper enforcement mode** | dry-run / enforcing | Whether policies block admission or only log; affects developer velocity vs. security posture | Security team |
| **TLS certificate issuer** | self-signed / internal PKI / external CA | Affects renewal cadence, trust chain, and operational overhead | Security team |
| **GitOps repo external access** | Required / restricted / offline | Determines if Argo CD sync server needs outbound internet or can operate with mirrored repos | Platform team |

---

## Go / No-Go Decision (Evidence-Based)

| Decision | Go | No-Go |
|---|---|---|
| **Criteria** | All mandatory blockers resolved with sufficient evidence; all recommended improvements either completed or explicitly accepted via error-budget trade-off; DR exercise completed within past 12 months; ownership and runbooks current; offline readiness confirmed if required; HA and failover validated; capacity within SLO headroom; security policies audited and approved. | Any mandatory blocker unresolved; critical recommended improvement deferred without error-budget sign-off; DR exercise stale (> 12 months); ownership undefined; offline requirement unmet; HA not validated; capacity exceeds SLO target; security policies found non-compliant. |
| **Decision recorded by** | Platform SRE lead + Security lead | N/A |
| **Decision timestamp** | `YYYY-MM-DDTHH:MM:SSZ` | N/A |
| **Next review date** | `YYYY-MM-DDTHH:MM:SSZ` (or upon significant change) | N/A |
| **Sign-off** | [Name, Role] | [Name, Role] |

> **Go/No-Go is not a static checklist outcome** — it is a dynamic decision based on the cumulative state of all readiness dimensions at the time of evaluation. If any mandatory blocker remains open, the default is No-Go until resolution or an authorized exception is documented.

---
