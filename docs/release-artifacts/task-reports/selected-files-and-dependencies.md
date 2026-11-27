# TASK 007.5 — Phase 1 Selected Files and Dependencies

**Task:** Controlled Content Reconciliation, Phase 1
**Scope:** File selection and dependency justification

## 1. Selected Files (2)

| # | Source Path | Type | Disposition | Reason for Selection |
|---|-------------|------|-------------|---------------------|
| 1 | `automation/awx/index.md` | Documentation | preserve | Pure addition (does not exist on origin/main). AWX web UI/RBAC/scheduler guide. No dependencies on conflict files, scripts, catalog, or site data. |
| 2 | `platform/backstage/catalog-info.yaml` | Config | preserve | Pure addition (does not exist on origin/main). Backstage component catalog definition. No dependencies on conflict files, scripts, catalog, or site data. |

## 2. Independence Verification

| Condition | automation/awx/index.md | platform/backstage/catalog-info.yaml |
|-----------|------------------------|--------------------------------------|
| Classified as preserve | Yes | Yes |
| No dependency on 20 conflicting files | Yes (deps=none) | Yes (deps=none) |
| No dependency on scripts/catalog/site data/workflows | Yes | Yes |
| No conflict with PR #2 content | Yes (pure addition, PR #2 doesn't touch) | Yes (pure addition, PR #2 doesn't touch) |
| No unnecessary duplication | Yes (new file, not on origin/main) | Yes (new file, not on origin/main) |
| Technically consistent with doc architecture | Yes | Yes |
| Suitable for meaningful validation | Yes (markdown lint + link check) | Yes (YAML validation) |
| Excluded from 20 conflict paths | Yes | Yes |

## 3. Source and Destination Status

| File | Exists on origin/main? | Exists on integration? | Action |
|------|------------------------|------------------------|--------|
| `automation/awx/index.md` | No | Yes | Pure addition — copy source content |
| `platform/backstage/catalog-info.yaml` | No | Yes | Pure addition — copy source content |

## 4. Dependencies Checked

| File | Referenced paths | Exist on destination? | Notes |
|------|-----------------|----------------------|-------|
| `automation/awx/index.md` | `ansible/README.md` | Yes | Existing on origin/main |
| `automation/awx/index.md` | `management-cluster/rancher/rancher.md` | Yes | Existing on origin/main |
| `automation/awx/index.md` | `lifecycle/backup/backup-and-dr.md` | Yes | Existing on origin/main |
| `automation/awx/index.md` | `compatibility/version-matrix.md` | Yes | Existing on origin/main (referenced by name only) |
| `automation/awx/index.md` | `management-cluster/keycloak/keycloak.md` | Not checked | Referenced as optional SSO prereq |
| `platform/backstage/catalog-info.yaml` | None | N/A | Self-contained YAML; dependsOn: [] |

## 5. Why Safe for Phase 1

- Both files are **pure additions** — no existing origin/main file is overwritten
- Both have **no dependencies** on any of the 20 conflicting files
- Neither touches catalog JSON, scripts, tests, workflows, or generated site data
- `automation/awx/index.md` is documentation only; `catalog-info.yaml` is self-contained YAML with `dependsOn: []`
- Cross-referenced paths in awx/index.md point to existing origin/main files
- Small scope (2 files, 80 lines total) enables complete validation

**No file modifications were made to the original repository during selection.**
