# Enterprise Cloud-Native Deployment & Operations Guide

Personal cloud-native knowledge base: on-premises, air-gapped, production-oriented. Documentation as code. Every version pinned, every URL sourced, every claim traceable.

## Scope

| Domain | Stack |
|---|---|
| OS | Oracle Linux 9, Ubuntu Server 24.04 LTS |
| Orchestration | Kubernetes via Kubespray (Ansible) |
| Storage | Ceph (cephadm on dedicated hosts, Rook-Ceph in-cluster) |
| Management | Rancher Management Cluster + independent Application Clusters |
| Traffic | MetalLB (L4) + NGINX (L7) + Gateway API + Cilium |
| GitOps | Argo CD, GitLab CI |
| Identity | Keycloak, SSSD/realmd, AD/LDAP |
| Secrets | HashiCorp Vault (or OpenBao), cert-manager, External Secrets |
| Observability | Prometheus/Grafana/Alertmanager/Thanos, Loki/Fluent Bit |
| Security | Pod Security Standards, OPA Gatekeeper, Kyverno, Falco, Trivy, Cosign, Syft |
| AI | NVIDIA H100/H200 workers, MIG, vLLM, DCGM |

## Repository map

```
architecture/            logical topology, deployment topology, failure domains
decisions/               ADR-0001 .. ADR-0027
requirements/            requirements, tech matrix, roadmap, validation, acceptance,
                         standards, performance, component-guide template
compatibility/           version & compatibility matrix (pinned, with check dates)
offline-artifacts/       artifact matrix, offline architecture, staging workflow
operating-systems/       oracle-linux/ ubuntu/ distro-specific baselines
automation/              ansible/ awx/ gitlab-ci/
kubespray/               deployment guide, multi-version support, inventory and
                         group-vars templates
kubernetes/              control-plane/ networking/ ingress/ csi/ security/
storage/                 ceph/ rook-ceph/ alternatives/
management-cluster/      rancher/ argocd/ keycloak/ platform-services/
identity/                SSSD, realmd, Kerberos, AD integration
secrets-management/      vault/ kubernetes-integration/ pki/ recovery/
gpu-ai/                  gpu-ai-architecture, gpu-workers/ drivers/ scheduling/
                         sharing/ inference/ monitoring/
monitoring/ logging/ security/ service-mesh/
network-matrix/          communication matrix, firewall rule generation
lifecycle/               upgrades/ backup/ disaster-recovery/
troubleshooting/          symptom-driven runbooks
scripts/                 version-refresh helpers, Kubespray matrix extractors, ADR generator
tests/                   repository self-check
```

## Status legend

| Mark | Meaning |
|---|---|
| VERIFIED | checked against the official source on the recorded date |
| UNVERIFIED | value not yet confirmed; the verification procedure is recorded |
| PROVISIONAL | chosen default pending review; safe to change before build |

## Working rules

1. No version, image tag, URL, port, or compatibility claim enters this repo without a source URL and a check date.
2. Facts that cannot be verified are labelled UNVERIFIED with the verification procedure. Never silently assumed.
3. Sensitive values never enter this repo. Sanitized examples and secret identifiers only.
4. Every command states its execution context.
5. Destructive or production-impacting actions require explicit authorization before execution.
6. A test is PASSED only when it has been executed and the evidence is stored. Nothing in this repo is pre-marked as passed.

## Deliverables map (master prompt §32)

| # | Deliverable | Location |
|---|---|---|
| 1 | Requirements and assumptions | `requirements/requirements-and-assumptions.md` |
| 2 | Reference architecture | `architecture/` |
| 3 | Technology selection matrix | `requirements/technology-selection-matrix.md` |
| 4 | Version and compatibility baseline | `compatibility/version-matrix.md` |
| 5 | Offline artifact architecture | `offline-artifacts/` |
| 6 | Network communication matrix | `network-matrix/` |
| 7 | GitLab and Ansible design | `automation/` |
| 8 | Secrets management architecture | `secrets-management/` |
| 9 | GPU and AI architecture | `gpu-ai/` |
| 10 | Implementation roadmap | `requirements/implementation-roadmap.md` |
| 11 | Component guide backlog | `requirements/component-guide-backlog.md` |
| 12 | Validation strategy | `requirements/validation-strategy.md` |

## Maintenance

```bash
# Refresh the version data in a connected environment
python3 scripts/fetch_versions.py
python3 scripts/helm_chart_versions.py
python3 scripts/github_latest_releases.py <owner/repo>

# Regenerate the ADRs after editing the generator
python3 scripts/gen_adrs.py

# Self-check the repository (offline)
python3 tests/test_repo_tools.py
```

## Implementation phases

Dependency-aware 15-phase plan with acceptance criteria per phase: `requirements/implementation-roadmap.md`.
