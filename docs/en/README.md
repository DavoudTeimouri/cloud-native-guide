# Cloud-Native Stack Implementation Guide (English)

Welcome to the Cloud-Native Stack Implementation Guide — a practical, production-oriented, bilingual guide for deploying and operating a cloud-native platform on-premises and in air-gapped environments.

## Quick Start

| Role | Start Here |
|---|---|
| Platform Architect | [Reference Architecture](../../architecture/00-overview.md) |
| DevOps Engineer | [Implementation Roadmap](../../requirements/implementation-roadmap.md) |
| Security Engineer | [Security Standards](../../requirements/platform-standards.md#security) |
| Storage Engineer | [Ceph Deployment](../../storage/ceph/cephadm-deployment.md) |
| Kubernetes Engineer | [Kubespray Deployment](../../kubespray/kubespray-deployment.md) |

## Documentation Structure

| Directory | Purpose |
|---|---|
| [architecture/](../../architecture/) | Reference architecture, topology, failure domains |
| [requirements/](../../requirements/) | Requirements, roadmap, standards, validation, acceptance criteria |
| [decisions/](../../decisions/) | Architecture Decision Records (ADR-0001..ADR-0027) |
| [compatibility/](../../compatibility/) | Version matrix, compatibility constraints |
| [operating-systems/](../../operating-systems/) | Ubuntu 24.04 LTS, Oracle Linux 9 baselines |
| [automation/](../../automation/) | Ansible, GitLab CI, Terraform |
| [kubespray/](../../kubespray/) | Kubespray deployment, multi-version support |
| [kubernetes/](../../kubernetes/) | CNI, CSI, Ingress, Add-ons, Security |
| [storage/](../../storage/) | Ceph, Rook-Ceph, alternatives |
| [management-cluster/](../../management-cluster/) | Rancher, Argo CD, Keycloak |
| [identity/](../../identity/) | Keycloak, SSSD/realmd, AD/LDAP |
| [secrets-management/](../../secrets-management/) | Vault, PKI, Kubernetes integration |
| [monitoring/](../../monitoring/) | Prometheus, Grafana, Loki, Alertmanager |
| [logging/](../../logging/) | Log pipeline, Fluent Bit, Loki |
| [security/](../../security/) | Gatekeeper, Kyverno, Falco, PSS |
| [service-mesh/](../../service-mesh/) | Evaluation and adoption criteria |
| [offline-artifacts/](../../offline-artifacts/) | Air-gap artifact matrix, staging |
| [lifecycle/](../../lifecycle/) | Upgrades, backup, disaster recovery |
| [troubleshooting/](../../troubleshooting/) | Symptom-driven runbooks |
| [scripts/](../../scripts/) | Version refresh, matrix generators, ADR generator |
| [tests/](../../tests/) | Repository self-check, acceptance tests |

## Bilingual Documentation

| Language | Location |
|---|---|
| English | `docs/en/` (this directory) |
| Persian (فارسی) | `docs/fa/` |

## Quick Links

- [Component Guide Template](../../requirements/component-guide-template.md)
- [Implementation Roadmap](../../requirements/implementation-roadmap.md)
- [Version & Compatibility Matrix](../../compatibility/version-matrix.md)
- [Platform Standards](../../requirements/platform-standards.md)
- [Acceptance Criteria](../../requirements/acceptance-criteria.md)
- [Validation Strategy](../../requirements/validation-strategy.md)

## Status Legend

| Mark | Meaning |
|---|---|
| **VERIFIED** | Checked against official source on recorded date |
| **UNVERIFIED** | Not yet confirmed; verification procedure recorded |
| **PROVISIONAL** | Chosen default pending review; safe to change before build |

## Contributing

See [USER.md](../../USER.md) for communication and work style conventions.
See [MEMORY.md](../../MEMORY.md) for fact-store conventions.

## License

This guide is documentation-as-code. See repository LICENSE for terms.