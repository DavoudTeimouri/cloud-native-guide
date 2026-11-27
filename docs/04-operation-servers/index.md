# 04 · Operation Servers and GitLab

Operational management environment and GitLab: architecture, tools, network access matrix, operational workflows, and GitLab installation/CI/CD.

## Purpose
Define the management/automation servers from which all infrastructure deployment and configuration is performed, plus GitLab installation and CI/CD for building, validating, scanning, and deploying Cloud-Native components.

## Subsections

| Subsection | Covers |
|---|---|
| [4.1 Operation Server Architecture](4.1-operation-server-architecture.md) | Operational architecture & responsibilities of Linux and Windows management servers; pair of Linux mgmt/automation servers preferred |
| [4.2 Required Tools](4.2-required-tools.md) | Ansible, Kubespray deps, K8s CLI, Helm, Git, container tools, SSH, PowerShell, infra utilities, monitoring/troubleshooting tools — installed through centralized repos |
| [4.3 Centralized Network Access Matrix](4.3-centralized-network-access-matrix.md) | Consolidated matrix of network access required by management servers; least-privilege admin access |
| [4.4 Operational Workflows](4.4-operational-workflows.md) | Complete workflows: OS prep, infra config, K8s deployment, storage, LB config, repo sync, monitoring config, troubleshooting, maintenance, upgrades |
| [4.5 GitLab](4.5-gitlab.md) | Install, architecture, auth, AD/LDAP, Git repo mgmt, CI/CD, Runners, container registry integration, artifact mgmt, backup/restore, security, monitoring, offline operation, upgrades; CI/CD examples |

## Cross-references
- Tools installed via [03 · Repository and Registry Management](../03-repository-registry/).
- Network access references [shared network matrix](../shared/network-matrix/).
- GitLab CI/CD deploys components covered in [06 · Kubernetes](../06-kubernetes-infrastructure/).
