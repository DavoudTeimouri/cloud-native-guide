# 01 · Overview and Architecture

Orientation for the complete Cloud-Native infrastructure and its design. Start here to understand the target architecture, sizing, network requirements, deployment environments, repositories/registries, components, technologies, standards, and design principles before touching infrastructure.

## Subsections
| Subsection | Covers |
|---|---|
| [1.1 Project Introduction and Goals](1.1-project-introduction-and-goals.md) | Objectives, requirements, design principles, target environments, assumptions, production readiness |
| [1.2 Reference Architectures](1.2-reference-architectures.md) | Layers, control/data plane split, deployment sizes, deployment environments, physical vs virtual |
| [1.3 Infrastructure Sizing and Resource Calculation](1.3-infrastructure-sizing-and-resource-calculation.md) | Sizing table, etcd storage, capacity planning |
| [1.4 Network Architecture and Access Matrix](1.4-network-architecture-and-access-matrix.md) | Segments, VLANs, routing, firewall, centralized access matrix |
| [1.5 Deployment Environments](1.5-deployment-environments.md) | Connected, partially disconnected, fully air-gapped, isolated zones |
| [1.6 Repositories and Registries](1.6-repositories-and-registries.md) | Package repos, container registries, Helm charts, Git, binary repos |
| [1.7 Infrastructure Components](1.7-infrastructure-components.md) | Complete component inventory and dependency map |
| [1.8 Technologies and Alternatives](1.8-technologies-and-alternatives.md) | Technology catalog, comparisons, selection criteria |
| [1.9 Standards and Best Practices](1.9-standards-and-best-practices.md) | Security, K8s, storage, networking, operational standards |

## Cross-references
- All sections reference [shared matrices](../shared/matrices/) for network access, version compatibility, and hardware requirements.
- [Shared decision records](../shared/decision-records/) for ADR-0001..ADR-0031.
- See [02 · Components](../02-components/) for node preparation details.
