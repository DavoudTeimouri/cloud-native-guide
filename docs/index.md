# Cloud-Native Guide

Step-by-step deployment and operations guide for on-premises, air-gapped, production-oriented cloud-native infrastructure.

## The 5-second test

**What**: A pinned, ordered playbook for deploying and operating a cloud-native stack on premises or air-gapped — Kubernetes via Kubespray, Ceph storage, F5/NGINX Gateway ingress, Rancher/Argo CD management, Vault/Keycloak identity and secrets, Velero backup.

**Why**: Production on-prem stacks fail at the edges — day-2 restore, upgrades, ingress retirement, Helm EOL. This guide pins versions, orders the work, and validates each phase before the next starts.

**How**: Follow the 3-layer journey below. Do not start step N+1 until step N validation passes.

## The 3-layer journey

| Layer | What it covers | Start here |
|-------|----------------|------------|
| **Home** | Orientation: what this guide is, where each domain lives, source of truth | This page |
| **Journey 00–12** | Ordered build-and-operate flow: architecture → offline artifacts → OS baseline → cluster → traffic edge → platform services → validation → day-2 operations → upgrades, retirement, decommission | [Journey 00 — Overview & architecture →](en/cloud-native-stack-step-by-step.md#step-00) |
| **Reference & Operations** | Architecture, version matrix, ADRs, components, network, security; concepts, troubleshooting, contribution; backup/DR, upgrades | Sidebar sections **Reference**, **Knowledge**, **Operations** |

## Journey 00–12

The journey is a single ordered flow. Every step lists purpose, prerequisites, actions, and validation. All versions are pinned from `compatibility/version-matrix.md`.

1. [Step 00 — Overview & architecture](en/cloud-native-stack-step-by-step.md#step-00)
2. [Step 01 — Offline artifact infrastructure](en/cloud-native-stack-step-by-step.md#step-01)
3. [Step 02 — Foundational infrastructure](en/cloud-native-stack-step-by-step.md#step-02)
4. [Step 03 — OS baseline](en/cloud-native-stack-step-by-step.md#step-03)
5. [Step 04 — Container engine and offline images](en/cloud-native-stack-step-by-step.md#step-04)
6. [Step 05 — Storage — Ceph](en/cloud-native-stack-step-by-step.md#step-05)
7. [Step 06 — Kubernetes via Kubespray v2.32.0](en/cloud-native-stack-step-by-step.md#step-06)
8. [Step 07 — Management cluster](en/cloud-native-stack-step-by-step.md#step-07)
9. [Step 08 — Traffic edge (LB and ingress)](en/cloud-native-stack-step-by-step.md#step-08)
10. [Step 09 — Platform services and add-ons](en/cloud-native-stack-step-by-step.md#step-09)
11. [Step 10 — Validation, backup, upgrade, disaster recovery](en/cloud-native-stack-step-by-step.md#step-10)
12. [Step 11 — Day-2 Operations](journey/step-11-day-2-operations.md)
13. [Step 12 — Upgrades, Retirement & Decommission](journey/step-12-upgrades-retirement.md)

## Key references

- **Version & Compatibility Matrix**: [compatibility/version-matrix.md](compatibility/version-matrix.md) — every pinned version with source URL and check date.
- **Architecture Decisions (ADR)**: [decisions/ADR-0001 … ADR-0031](decisions/ADR-0001-oracle-linux-and-ubuntu-server-standardization.md) — control-plane topology, CNI, ingress, storage, secrets, Kubespray multi-release, external load balancer.

## Source of truth

This site is generated from the [cloud-native-guide](https://github.com/DavoudTeimouri/cloud-native-guide) repository using [MkDocs](https://www.mkdocs.org/). The repository is the source of truth for procedures, decisions, versions, and matrices; the site carries no independent knowledge.
