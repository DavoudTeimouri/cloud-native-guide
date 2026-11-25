# Observability: Security Monitoring

*Illustrative only — not production-committed configurations. Marked as such where indicated.*

This document maps security-relevant observability surfaces across core infrastructure components and enforcement layers. It distinguishes **security events** (identity misuse, policy violations, credential exposure) from **infrastructure availability** alerts (process crashes, network partitions, storage failures). Metric sources are classified as native, exporter‑driven, API‑based, or external; no single product is assumed to expose every metric in every edition.

---

## Vault / OpenBao

| Surface | What to Observe | Typical Sources | Collection Method |
|---|---|---|---|
| **Availability & sealed state** | Process liveness, sealed/unsealed transition | Native metrics (if available), health endpoints | `curl https://vault.example.com/v1/sys/seal-status`; Prometheus exporter `hashicorp-vault-exporter` (community) |
| **HA & leadership** | Leader election status, follower health | Native metrics, Zookeeper/Consul integration | `vault_status{mode="leader"}` / `vault_status{mode="follower"}` |
| **Storage backend health** | DB connection pool, latency, error rate | Backend‑specific metrics (DynamoDB, PostgreSQL, etc.) | Cloud‑provider metrics or JMX exporter |
| **Request latency & errors** | p95/p99 latency, 5xx count per path | `vault_request_duration_seconds`, `vault_requests_total{status="5xx"}` | HashiCorp Vault exporter for Prometheus |
| **Token & authentication failures** | Token revocation, TTL exhaustion, auth method errors | Auth method counters, token API return codes | `vault_auth_failures_total` via exporter |
| **Lease & secret-engine behavior** | Active leases, time‑to‑expiry, secret version count | Secret engine stats API | Periodic API scrape: `GET /v1/sys/leases/recovery`; `GET /v1/sys/metrics` |
| **Audit device health** | Audit log write failures, device disconnects | Audit device configuration, file‑based audit | File tail monitoring; syslog forwarder; `vault_audit_device_status` |
| **Certificate/PKI issuance & expiration** | Issued cert TTL, remaining validity, renewal failures | PKI secrets engine metrics, Certificate Transparency logs | `vault_pki_cert_expiry_seconds`; renew‑before‑expiry alert (e.g., 30 days) |

> **Note**: Not all Vault editions expose the same metric names. Use the `/sys/metrics` endpoint to discover available metrics for your version. Exporter versions should be pinned to avoid drift.

---

## Keycloak

| Surface | What to Observe | Typical Sources | Collection Method |
|---|---|---|---|
| **Availability** | Process liveness, node health | JMX, Prometheus JMX exporter | `keycloak_server_Uptime`; `keycloak_node_status{node="…"}` |
| **Authentication latency & failures** | Login duration, failed auth attempts, timeout count | `org.keycloak:type=Authentication,type=Login` MBeans; `authentication_failure_total` | Prometheus JMX exporter or K8s stats |
| **Token issuance** | Access/refresh token rate, time‑to‑token, revocation count | Token manager metrics | `keycloak_token_issued_total`, `keycloak_token_revoked_total` |
| **Database connectivity** | Connection pool usage, query latency, DB errors | HikariCP metrics, JDBC stats | JMX: `com.zaxxer.hikari:type=Pool,name=Keycloak` |
| **JVM performance** | GC pause, heap usage, thread count | JVM built‑in MBeans | `jvm_memory_used_bytes`, `gc_pause_seconds_sum` |
| **User / session metrics** | Active sessions, session creation/termination, expired sessions | `org.keycloak:type=Session` MBeans | `keycloak_active_sessions_total` |
| **Identity provider failures** | IdP reachability, SAML/OIDC error count, latency | IdP connector stats, connector‑specific metrics | API-based scrape of IdP health endpoint; Prometheus exporter `keycloak-idp-exporter` (community) |

> **Note**: Keycloak metrics stability varies by deployment mode (standalone vs. clustered) and database backend. Always validate metric presence in a staging environment before wiring alerts.

---

## Security Enforcement (Gatekeeper, Kyverno, Falco, Trivy, Cosign)

| Surface | What to Observe | Typical Sources | Collection Method |
|---|---|---|---|
| **Admission request failures & policy violations** | Admission webhook error count, denied resources, violation categories | Admission controller audit logs, OPA/Rego violation events | Kubernetes audit log parse; `gatekeeper_audit_denied_total` or `kyverno_violation_rejected_total` |
| **Policy evaluation latency** | p95/p99 admission request duration, webhook timeout count | Admission controller Prometheus metrics | `gatekeeper_admission_duration_seconds_bucket`; `kyverno_webhook_duration_seconds_bucket` |
| **Runtime security events** | Container behavior anomalies (syscall patterns, file access) | Falco rule triggers, runtime syscall logs | Falco event export (JSON/CEF); Prometheus `falco_events_total` by rule |
| **Vulnerability scan failures** | Image scan timeout, scanner crash, partial scan count | Trivy exit codes, scan operator status | Trivy operator `trivy_scan_status`; CI‑pipeline step result |
| **Image verification failures** | Cosign signature verification fail, immutability violation, repo access error | Cosign audit log, key transparency logs | `cosign_verification_failed_total`; `cosign_key_not_found_total` |
| **Audit pipeline health** | Upstream forwarder failures, log drop count, audit log lag | Fluentd/Flutter audit forwarder metrics, syslog queue depth | Forwarder exporter (`fluent-bit_pipeline_status`); file‑tail lag alert |

> **Distinction**: 
> - **Security events** = policy denial, verified violation, image signature failure, anomalous runtime behavior. These are *intent/result* metrics and should trigger security‑team alerts.
> - **Infrastructure availability** = webhook process crash, missing CustomResourceDefinition, Prometheus scrape failure. These are *platform* alerts and should not be conflated with policy violations.

> **Note on exporters**: Metric names shown are representative. Actual exposure depends on the specific product version, deployment configuration (e.g., Kyverno vs. Gatekeeper in -admission‑only mode), and whether the component runs inside or outside the cluster. Always `kubectl get --raw /metrics` or consult the vendor docs to confirm available surfaces.

---

## Collection Strategy Overview

| Source Type | Typical Exposure | Recommended Tooling |
|---|---|---|
| **Native metrics** | Export built‑in HTTP `/metrics` or JMX endpoints | Prometheus `scrape_config`; `prometheus‑operator` ServiceMonitor |
| **Exporters** | Community‑ or vendor‑maintained Prometheus exporters | `hashicorp‑vault‑exporter`, `keycloak‑jmx‑exporter`, `falco‑prometheus‑exporter`, `cosign‑exporter` |
| **API‑based collection** | REST/GraphQL endpoints that return structured data | Periodic `curl`/SDK calls; `cron`‑driven jobs; webhook pipelines |
| **External monitoring** | Dedicated SaaS or on‑prem platforms (Splunk, Datadog, Elastic) | Forwarders (Fluentd, Filebeat, Vector); log‑based alerts; correlation rules |

No single approach covers every surface. A pragmatic deployment combines:
1. **Prometheus + ServiceMonitor** for native and exporter‑driven metrics.
2. **Audit‑log parsers** (Flutter/Fluentbit) for components that expose sparse metrics.
3. **API‑driven health checks** for sealed state, PKI expiry, and scan results.
4. **SaaS correlation** (if available) for cross‑component correlation and dashboards.

---

## What This File Is NOT

- A deployment guide for monitoring agents or exporters.
- A claim that every listed metric is available in every edition or distribution.
- A substitute for vendor‑specific documentation on metric stability and version compatibility.

*Next steps*: Validate metric availability in your specific versions. Cross‑reference with component release notes. Add or remove surfaces as your stack dictates.