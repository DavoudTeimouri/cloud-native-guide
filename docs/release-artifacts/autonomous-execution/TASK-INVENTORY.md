# TASK-INVENTORY — Cloud-Native Stack Migration

**Total unique files:** 93
**Reconciled:** 37 (Phases 1-6)
**Remaining:** 56

**Reconciled (Phase 1-6):**
| Phase | File |
|-------|------|
| 1 | automation/awx/index.md |
| 1 | platform/backstage/catalog-info.yaml |
| 2 | lifecycle/backup/backup-and-dr.md |
| 2 | lifecycle/disaster-recovery/index.md |
| 3 | offline-artifacts/artifact-matrix.md |
| 3 | architecture/00-overview.md |
| 4 | scripts/compare_tree.py |
| 4 | scripts/gh_refs.py |
| 4 | scripts/verify_github.py |
| 5 | architecture/02-deployment-topology.md |
| 5 | architecture/03-failure-domains.md |
| 5 | security/host-baseline.md |
| 5 | kubernetes/node-resource-reservation.md |
| 5 | kubernetes/security/security-controls.md |
| 5 | automation/ansible/ansible-structure.md |
| 5 | automation/ansible/index.md |
| 6 | PLAN-future.md |
| 6 | automation/terraform/vsphere-example.md |
| 6 | site/README.md |
| 6 | service-mesh/evaluation.md |
| 6 | kubernetes/networking/coredns-forwarding.md |
| 6 | network-matrix/cloud-native-dmz.md |
| 6 | network-matrix/port-requirements.md |

**Disposition (remaining 56):** preserve ~51 | adapt 3 | consolidate 2

**Adapt candidates:** CONTRIBUTING.md, README.md, platform/golden-paths/cloudnative-service.json
**Consolidate candidates:** ADR-0004, ADR-0028

**High-coupling clusters (avoid until deps reconciled):** catalog scripts, kubespray deployment, version matrix, identity scripts

**Recommended Phase 7:** architecture/01-logical-diagram.md, decisions/ADR-0015-identity-integration-layer.md, decisions/ADR-0031-identity-integration-with-ldap-ad-federation.md, kubernetes/addons/cert-manager.md, kubernetes/control-plane/index.md
