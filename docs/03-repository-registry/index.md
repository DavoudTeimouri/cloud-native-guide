# Repository and Registry Management

Centralized software-distribution architecture: upstream/downstream repos and registries, platform selection, installation, catalog, reverse proxy, client configuration, and validation.

## Purpose

Define how software artifacts (OS packages, container images, Helm charts, Git, language packages) are stored, synchronized, promoted, and served — including fully disconnected operating models — so no node requires outbound internet at runtime.

## Subsections

| Subsection | Covers |
| --- | --- |
| [Architecture](3.1-architecture.md) | Upstream/downstream architecture; sync, replication, promotion, controlled transfer; fully disconnected models |
| [Platform Selection](3.2-platform-selection.md) | Nexus vs Harbor vs alternatives; which platform manages each artifact type; no single product assumed to support every protocol |
| [Installation & Configuration](3.3-installation-config.md) | Native and container-based (Docker Compose preferred) install; persistent storage, HA/scalability, backup/restore, auth, TLS, monitoring, logging, upgrades |
| [Repository & Registry Catalog](3.4-repository-catalog.md) | Name, type, purpose, upstream source, downstream endpoint, protocol, auth, sync method, retention, scanning, consumers |
| [Reverse Proxy Architecture](3.5-reverse-proxy.md) | DNS/hostname preservation, TLS termination/passthrough, path routing, header forwarding, Docker/OCI/Helm/package-manager compatibility; services that cannot operate behind a reverse proxy |
| [Client Configuration](3.6-client-config.md) | DNF/YUM, APT, Docker, containerd, Helm, Git, pip, npm, Maven, NuGet, Cargo — config examples through internal repos |
| [Validation & Operations](3.7-validation-operations.md) | Connectivity testing, sync validation, integrity verification, backup, monitoring, troubleshooting, recovery |

## Cross-references

- Consumes the [shared version & compatibility matrix](../shared/matrices/version-matrix/) for pinned artifact versions.
- Referenced by [Components (2.10 Repo & Registry Manager Servers)](../02-components/2.10-repo-registry-servers.md) and [Operation Servers (4.4 Operational Workflows)](../04-operation-servers/4.4-operational-workflows.md).
