# Cloud-Native Guide

Production-oriented deployment and operations guide for on-premises, air-gapped cloud-native infrastructure. Follow the numbered sections in order — each section lists purpose, prerequisites, implementation, validation, and cross-references.

## The 5-second test

**What**: A pinned, ordered playbook for designing, deploying, operating, troubleshooting, scaling, upgrading, and maintaining a cloud-native stack on premises or air-gapped — Kubernetes via Kubespray, Ceph storage, F5/NGINX Gateway ingress, Rancher/Argo CD management, Vault/Keycloak identity and secrets, Velero backup.

**Why**: Production on-prem stacks fail at the edges — day-2 restore, upgrades, ingress retirement, Helm EOL. This guide pins versions, orders the work, and validates each phase before the next starts.

**How**: Work through sections 01–11 in order. Do not start section N+1 until section N validation passes. All versions are pinned from the [shared version & compatibility matrix](shared/matrices/version-matrix/index.md).

## Numbered sections

| Section | What it covers | Start here |
|---|---|---|
| **[01 · Overview](01-overview-and-architecture/index.md)** | Orientation: architecture, sizing, network matrix, air-gapped models, repositories/registries, components, technologies, standards, design principles | [01-overview-and-architecture/index.md](01-overview-and-architecture/index.md) |
| **[02 · Components](02-components/index.md)** | Component preparation: operating systems, physical/virtual, hardware/virtualization, OS by role, operation servers, K8s nodes, Ceph/storage nodes, LB nodes, repo/registry servers, GitLab, other infra | [02-components/index.md](02-components/index.md) |
| **[03 · Repository & Registry Management](03-repository-registry/index.md)** | Upstream/downstream software distribution, platform selection, install, catalog, reverse proxy, client config, validation | [03-repository-registry/index.md](03-repository-registry/index.md) |
| **[04 · Operation Servers & GitLab](04-operation-servers/index.md)** | Mgmt/automation servers, tools, network access matrix, operational workflows, GitLab CI/CD | [04-operation-servers/index.md](04-operation-servers/index.md) |
| **[05 · Load Balancers](05-load-balancers/index.md)** | HA load balancing, mgmt + app cluster LBs, native/container deploy, config & operations | [05-load-balancers/index.md](05-load-balancers/index.md) |
| **[06 · Kubernetes](06-kubernetes-infrastructure/index.md)** | Architecture, best practices, Kubespray deploy, mgmt + app clusters, Rancher, Argo CD GitOps, CNI/CSI/networking, add-ons, observability, policies, alerts | [06-kubernetes-infrastructure/index.md](06-kubernetes-infrastructure/index.md) |
| **[07 · SDS](07-software-defined-storage/index.md)** | Storage architecture, platform selection, independent Ceph, Rook-Ceph, storage appliances, monitoring | [07-software-defined-storage/index.md](07-software-defined-storage/index.md) |
| **[08 · Troubleshooting](08-troubleshooting-and-diagnostics/index.md)** | Symptom-driven runbooks by component and failure category | [08-troubleshooting-and-diagnostics/index.md](08-troubleshooting-and-diagnostics/index.md) |
| **[09 · Scaling & Expansion](09-scaling-and-expansion/index.md)** | Controlled infrastructure growth: servers, VMs, K8s clusters, worker pools, Ceph, storage, repo, monitoring, LB | [09-scaling-and-expansion/index.md](09-scaling-and-expansion/index.md) |
| **[10 · Upgrade](10-upgrade-and-lifecycle-management/index.md)** | Controlled upgrades for every component: OS, firmware, hypervisor, K8s, Kubespray, Rancher, CNI, CSI, add-ons, Ceph, LB, GitLab, Nexus, Harbor, monitoring | [10-upgrade-and-lifecycle-management/index.md](10-upgrade-and-lifecycle-management/index.md) |
| **[11 · Maintenance](11-maintenance-and-operations/index.md)** | Daily/weekly/monthly ops, quarterly reviews, patching, cert renewal, backup verification, recovery testing, drift, node replacement, DR exercises | [11-maintenance-and-operations/index.md](11-maintenance-and-operations/index.md) |

## Shared catalogs (referenced by all sections)

- [Shared network matrix](shared/network-matrix/index.md) — authoritative communication matrix and port requirements
- [Shared version & compatibility matrix](shared/matrices/version-matrix/index.md) — pinned versions with source URLs and check dates
- [Shared templates](shared/templates/index.md) — reusable deployment, validation, troubleshooting, upgrade, maintenance templates
- [Shared diagrams](shared/diagrams/index.md) — Mermaid architecture diagrams

## Key references

- **Version & Compatibility Matrix**: `shared/matrices/version-matrix/index.md` — every pinned version with source URL and check date.

## Source of truth

This site is generated from the [cloud-native-guide](https://github.com/DavoudTeimouri/cloud-native-guide) repository using [MkDocs](https://www.mkdocs.org/). The repository is the source of truth for procedures, decisions, versions, and matrices; the site carries no independent knowledge.
