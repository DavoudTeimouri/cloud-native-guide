# Cloud-Native Guide

Step-by-step deployment and operations guide for on-premises, air-gapped, production-oriented cloud-native infrastructure.

## Eight engineering domains

| Domain | Topics |
|--------|--------|
| **Kubernetes & Kubespray** | Kubespray deployment, multi-version support, control plane, networking, ingress, security, node reservation, multi-cluster |
| **Rancher & Cluster Operations** | Rancher, Argo CD, Keycloak, platform services, alternatives |
| **Ceph & Rook-Ceph** | Cephadm deployment, Rook-Ceph, storage alternatives |
| **Offline & Air-Gapped** | Artifact architecture, artifact matrix, version pinning |
| **Security & Secrets Management** | Vault architecture, PKI, secret delivery, recovery, host baseline |
| **Monitoring & Observability** | Prometheus, log pipeline |
| **Backup, Disaster Recovery & Continuity** | Disaster recovery, backup and DR, upgrade procedures |
| **Automation, Testing & Documentation** | Ansible, GitLab CI, AWX, requirements, ADRs, troubleshooting |

## Navigation

Use the sidebar to browse each domain. Every page links back to its authoritative document in the repository.

## Source of truth

This site is generated from the [cloud-native-guide](https://github.com/DavoudTeimouri/cloud-native-guide) repository using [MkDocs](https://www.mkdocs.org/). The repository is the source of truth for procedures, decisions, versions, and matrices. The site is generated from it and carries no independent knowledge.

## Interactive website

A separate interactive configurator website is published from the [`cloudnative-infrastructure-guide`](https://github.com/DavoudTeimouri/cloudnative-infrastructure-guide) repository. It consumes structured data from this repository but is a distinct product.
