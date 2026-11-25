# Section 3: RPO/RTO and Recovery Classification

## Definitions

| Term | Definition |
|---|---|
| **RPO (Recovery Point Objective)** | Maximum tolerable data loss; the oldest acceptable point in time to which data can be restored. Expressed as a time window before recovery initiation. |
| **RTO (Recovery Time Objective)** | Maximum tolerable downtime; the maximum time allowed to restore operations after a failure event. Expressed as elapsed time from failure detection to full restoration. |
| **MTD (Maximum Tolerable Downtime)** | The absolute maximum time a business function can be offline before irreversible impact occurs. |
| **Error Budget** | The portion of unavailable time remaining within an SLO target (e.g., 99.95% availability over 30d window). |

---

## Recovery Classification Tiers

| Tier | Description | Example Components | Illustrative RPO | Illustrative RTO |
|---|---|---|---|---|
| **Tier 0** | Critical; platform-wide outage; immediate activation | K8s control plane, etcd, cluster networking | < 5 min | < 30 min |
| **Tier 1** | High-priority stateful workloads; data loss unacceptable | Ceph/Rook-Ceph, stateful databases, registry | < 15 min | < 2 h |
| **Tier 2** | Important services; brief data loss acceptable | Monitoring stack, logging, CI runners | < 1 h | < 8 h |
| **Tier 3** | Operational services; data can be re-synchronized | Argo CD, ingress, cert-manager | < 4 h | < 24 h |
| **Tier 4** | Supporting services; manual recovery acceptable | Documentation repos, read-only caches | < 24 h | < 5 d |

> **All RPO/RTO values above are illustrative and not production-committed.** Actual values must be derived from business impact analysis, SLO targets, and acceptable data loss tolerance for each service or component.

---

## RPO/RTO by Component (Illustrative Only)

| Component | RPO (Illustrative) | RTO (Illustrative) | Data Consistency Model |
|---|---|---|---|
| **K8s Control Plane** | < 5 min | < 30 min | Etcd snapshots; quorum-based consistency |
| **Stateful Workloads (PVC-backed)** | < 15 min (depends on pool) | < 2 h (depends on resync) | Application-consistent snapshots; CSI driver |
| **Ceph Storage** | < 10 min (OSD resync) | < 1 h (cluster rebalancing) | CRUSH-map; OSD quorum; PG active+clean |
| **Identity/Secrets (Vault/OpenBao)** | < 5 min | < 15 min | Seal/unseal key rotation; storage backend snapshot |
| **Registry/Repository (Harbor/Nexus)** | < 15 min | < 2 h | Image digest immutability; storage layer snapshot |
| **Monitoring (Prometheus/Grafana)** | < 1 h (TSDB export) | < 4 h (rule re-evaluation) | Honest TSDB export; remote write retention |
| **Logging (Loki/Fluent Bit)** | < 1 h (chunk upload) | < 4 h (index rebuild) | Chunked storage; index compaction |
| **GitOps/Config Repos** | < 24 h | < 8 h | Git event log; remote mirror; backup branch |

---

## How to Measure Actual RPO/RTO During Recovery Exercises

| Step | Action | Metric Captured |
|---|---|---|
| **1. Define Failure Scenario** | Document the failure mode (node crash, power outage, etcd corruption, etc.) | Failure type, detection time |
| **2. Record Failure Detection Time** | `t_detect` — time from failure onset to alert firing | Detection latency |
| **3. Initiate Recovery** | `t_recovery_start` — time from detection to recovery action commencement | Time to action |
| **4. Capture Recovery Completion** | `t_recovery_end` — time from start to full operational restoration | Recovery duration |
| **5. Compute RTO** | `RTO = t_recovery_end - t_detect` | Actual downtime |
| **6. Compute RPO** | Compare data state at `t_detect` vs. `t_recovery_end`; measure oldest acceptable data loss | Data loss window |
| **7. Compare to Target** | `RTO_actual ≤ RTO_target` / `RPO_actual ≤ RPO_target` | Pass/fail assessment |
| **8. Post-Incident Review** | Adjust targets based on observed data; document lessons learned | Target refinement |

> **Exercise cadence:** Conduct full-dress recovery drills at least annually for Tier 0–2 components; tabletop reviews quarterly for Tier 3–4.

---

## Recovery Order / Prioritization

1. **Tier 0 — Control plane and quorum-dependent services** (etcd, K8s API, MON quorum)
2. **Tier 1 — Stateful storage and data services** (Ceph, registry, databases)
3. **Tier 2 — Observability and logging** (Prometheus, Grafana, Loki)
4. **Tier 3 — Identity and access** (Vault, Keycloak)
5. **Tier 4 — GitOps, ingress, cert-manager** (application delivery pipeline)
6. **Tier 5 — Supporting / documentation services** (static repos, read-only caches)

> **Priority is driven by business impact and error budget consumption**, not component hierarchy alone. Re-assess after each exercise.

---