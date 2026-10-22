# Enterprise Cloud-Native Deployment & Operations Guide

Personal cloud-native knowledge base: on-premises, air-gapped, production-oriented. Documentation as code. Every version pinned, every URL sourced, every claim traceable.

## Scope

| Domain | Stack |
|---|---|
| OS | Oracle Linux, Ubuntu Server |
| Orchestration | Kubernetes via Kubespray (Ansible) |
| Storage | Ceph (cephadm / Rook-Ceph) |
| Management | Rancher Management Cluster + Application Clusters |
| Traffic | MetalLB (L4) + NGINX/Traefik (L7) + Gateway API |
| GitOps | Argo CD, GitLab CI |
| Identity | Keycloak, SSSD/realmd, AD/LDAP |
| Secrets | HashiCorp Vault (or OpenBao), cert-manager |
| Observability | Prometheus/Grafana/Alertmanager/Thanos, Loki/Fluent Bit |
| Security | Pod Security Standards, OPA Gatekeeper, Kyverno, Falco, Trivy, Cosign, Syft |
| AI | NVIDIA H100/H200 workers, MIG, vLLM, DCGM |

## Repository map

```
architecture/            logical + physical topology, failure domains
decisions/               ADR-0001..ADR-0025
requirements/            confirmed requirements, assumptions, risks
compatibility/           version & compatibility matrix (pinned)
offline-artifacts/       artifact matrix, staging workflow, repo responsibilities
operating-systems/       oracle-linux/ ubuntu/ distro-specific procedures
automation/              ansible/ awx/ gitlab-ci/
kubespray/               inventories, group vars, offline image overrides
kubernetes/              control-plane networking ingress csi security
storage/                 ceph/ rook-ceph/ alternatives/
management-cluster/      rancher argocd keycloak platform-services
identity/                SSSD realmd Kerberos AD integration
secrets-management/      vault kubernetes-integration pki recovery
gpu-ai/                  gpu-workers drivers scheduling sharing inference monitoring
monitoring/ logging/ security/ service-mesh/
network-matrix/          source and destination communication matrix
lifecycle/               upgrades/ backup/ disaster-recovery/
troubleshooting/         symptom-driven runbooks
scripts/ ansible/ helm/ manifests/ tests/
```

## Status legend

| Mark | Meaning |
|---|---|
| VERIFIED | checked against official source on the recorded date |
| UNVERIFIED | value not yet confirmed; verification procedure recorded |
| PROVISIONAL | chosen default pending review; safe to change before build |

## Working rules

1. No version, image tag, URL, port, or compatibility claim enters this repo without a source URL and a check date.
2. Facts that cannot be verified are labelled UNVERIFIED with the verification procedure. Never silently assumed.
3. Sensitive values never enter this repo. Sanitized examples and secret identifiers only.
4. Every command states its execution context.
5. Destructive or production-impacting actions require explicit authorization before execution.

## Implementation phases

Dependency-aware 15-phase plan with acceptance criteria per phase: `requirements/implementation-roadmap.md`.
