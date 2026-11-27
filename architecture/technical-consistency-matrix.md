# Technical Consistency Matrix

## A. Purpose and scope

Document the relationships between all major repository domains: architecture, compatibility matrices, deployment procedures, configuration examples, security controls, operational runbooks, automation, monitoring, backup and recovery, and offline deployment.

This matrix ensures that changes in one domain are reflected in all dependent domains. It is the single source of truth for cross-domain consistency.

## B. Version consistency matrix

| Component | Version | Source of truth | Dependent documents |
|-----------|---------|-----------------|---------------------|
| Kubespray | v2.32.0 | compatibility/version-matrix.md | kubespray-deployment.md, group-vars-template.md, multi-version-support.md |
| Kubernetes (default) | 1.36.5 | compatibility/version-matrix.md | kubespray-deployment.md, group-vars-template.md, control-plane/index.md |
| Kubernetes (minimum) | v1.34.0 | compatibility/version-matrix.md | kubespray-deployment.md, ADR-0026 |
| Ansible | >=2.19.0, <2.20.0 | compatibility/version-matrix.md | automation/ansible/ansible-structure.md, multi-version-support.md |
| Python | 3.11-3.13 | compatibility/version-matrix.md | automation/ansible/ansible-structure.md, multi-version-support.md |
| containerd | 2.3.7 | compatibility/version-matrix.md | kubespray-deployment.md, group-vars-template.md |
| etcd | 3.6.15 | compatibility/version-matrix.md | kubespray-deployment.md |
| Helm | 3.22.0 | compatibility/version-matrix.md | kubespray-deployment.md, offline-artifacts/artifact-matrix.md |
| CoreDNS | 1.14.2 | compatibility/version-matrix.md | kubespray-deployment.md |
| Cilium | 1.20.3 | compatibility/version-matrix.md | kubernetes/networking/cilium.md, kubespray-deployment.md |
| MetalLB | 0.13.9 | compatibility/version-matrix.md | network-matrix/port-requirements.md |
| cert-manager | 1.15.3 | compatibility/version-matrix.md | service-mesh/evaluation.md, kubespray-deployment.md |
| Argo CD | 2.14.5 | compatibility/version-matrix.md | management-cluster/argocd/argocd.md |
| Rancher | — | management-cluster/rancher/rancher.md | management-cluster/rancher/rancher.md |
| Vault | — | secrets-management/vault/vault-architecture.md | secrets-management/pki/root-ca-rotation.md |
| Keycloak | — | management-cluster/keycloak/keycloak.md | management-cluster/keycloak/keycloak.md |
| GitLab | — | automation/gitlab-ci/pipeline.md | automation/gitlab-ci/gitlab-ansible-design.md |
| Harbor | — | offline-artifacts/nexus-harbor-integration.md | offline-artifacts/nexus-harbor-integration.md |
| Nexus | — | offline-artifacts/nexus-harbor-integration.md | offline-artifacts/nexus-harbor-integration.md |
| Ceph | — | storage/ceph/cephadm-deployment.md | storage/ceph/cephadm-deployment.md |
| Rook-Ceph | — | storage/rook-ceph/rook-ceph.md | storage/rook-ceph/rook-ceph.md |

**Rule:** When a version changes in compatibility/version-matrix.md, all dependent documents must be updated in the same change.

## C. Domain dependency graph

| Domain | Depends on | Referenced by |
|--------|-----------|---------------|
| Architecture | — | All domains |
| Compatibility matrix | Architecture | kubespray-deployment.md, group-vars-template.md, all deployment docs |
| Kubespray deployment | Compatibility matrix, Architecture | control-plane/index.md, disaster-recovery/index.md, lifecycle/upgrades/kubernetes.md |
| Control plane | Kubespray deployment, Compatibility matrix | disaster-recovery/index.md, ha-topology.md |
| etcd | Kubespray deployment, Control plane | disaster-recovery/index.md, control-plane/index.md |
| CNI (Cilium) | Kubespray deployment, Compatibility matrix | kubespray-deployment.md, kubernetes/networking/bgp-ebpf.md |
| Network policy | CNI (Cilium) | kubernetes/networking/network-policy-examples.md |
| Storage (Ceph) | Architecture, Compatibility matrix | disaster-recovery/index.md, kubespray-deployment.md |
| Storage (Rook-Ceph) | Architecture, Compatibility matrix | disaster-recovery/index.md |
| Disaster recovery | Kubespray deployment, etcd, Storage, Vault | All recovery runbooks |
| Secrets (Vault) | Architecture, Compatibility matrix | disaster-recovery/index.md, kubernetes/security/security-controls.md |
| Secrets (PKI) | Architecture | kubespray-deployment.md (OIDC CA), security-controls.md |
| Monitoring | Architecture, Compatibility matrix | kubernetes/networking/cilium.md (Hubble) |
| Alerting | Monitoring | monitoring/alerting-rules.md |
| Dashboards | Monitoring | monitoring/grafana-dashboards.md |
| Automation (Ansible) | Kubespray deployment, Compatibility matrix | kubespray-deployment.md, management-cluster/rancher/rancher.md |
| Automation (Terraform) | Architecture | automation/terraform/vsphere.md |
| GitOps (Argo CD) | Architecture, Secrets | management-cluster/rancher/rancher.md, disaster-recovery/index.md |
| Offline deployment | Compatibility matrix, All domains | kubespray-deployment.md §F, nexus-harbor-integration.md |
| Security controls | Architecture, CNI, Secrets | All domain docs |
| Host baseline | Architecture, Compatibility matrix | kubernetes/security/security-controls.md |

## D. Cross-domain consistency checks

| Check | Frequency | Method | Responsible |
|-------|-----------|--------|-------------|
| Version pins match compatibility matrix | On every version change | Grep all .md for component versions | Domain owner |
| Cross-references resolve | On every doc change | scripts/check_links.py | Author |
| Catalog consistency | On every catalog change | scripts/validate_catalog.py | Author |
| No plaintext secrets | On every commit | tests/test_repo_tools.py | Author |
| Python scripts compile | On every script change | tests/test_scripts.py | Author |
| ADR structure complete | On every ADR change | tests/test_repo_tools.py | Author |
| OIDC variables present | On every OIDC change | tests/test_repo_tools.py | Author |

## E. Update procedure

When changing a version or configuration in one domain:

1. **Identify the source of truth** — usually compatibility/version-matrix.md or the relevant ADR
2. **Update the source of truth** with the new version/configuration and check date
3. **Identify all dependent documents** using the Domain dependency matrix (Section C)
4. **Update each dependent document** to match
5. **Run validation**: check_links.py, validate_catalog.py, test_repo_tools.py, test_scripts.py
6. **Record the change** in the change log of each affected document

## F. Known consistency risks

| Risk | Mitigation |
|------|------------|
| Kubespray version pinned differently in kubespray-deployment.md vs group-vars-template.md | Documented as blocked task TASK-008.1-P09-17 — human architectural decision required |
| OIDC CA certificate path referenced but not automated | Documented in kubespray-deployment.md §L — owner-operated procedure |
| etcd version compatibility across Kubespray releases | Documented in compatibility/version-matrix.md — hard floor v1.34.0 for release-2.32 |
| CNI migration (Cilium → Calico fallback) | Documented in ADR-0006 — migration requires pod recreation |

## G. Cross-references

- compatibility/version-matrix.md — Version pins and check dates
- kubespray/kubespray-deployment.md — Kubespray deployment, offline configuration, OIDC CA
- kubespray/group-vars-template.md — Authoritative group variable template
- architecture/02-deployment-topology.md — Deployment topology
- architecture/03-failure-domains.md — Failure domain design
- kubernetes/security/security-controls.md — Cluster security controls
- security/host-baseline.md — Host CIS baseline
- lifecycle/backup/backup-and-dr.md — Backup mechanics and RPO/RTO
- lifecycle/disaster-recovery/index.md — Recovery order and runbooks
- offline-artifacts/artifact-matrix.md — Offline artifact inventory
- offline-artifacts/nexus-harbor-integration.md — Nexus/Harbor integration
- network-matrix/port-requirements.md — Network port requirements
- ADR-0006 — CNI selection (Cilium)
- ADR-0026 — Kubespray multi-version support
- ADR-0010 — Management cluster design
- ADR-0011 — Rancher vs alternatives
