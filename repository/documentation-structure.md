# Repository Documentation Structure

## 📁 Directory Organization

The repository follows a feature-domain layout under `/workspace/project/github/public-repository/cloud-native-guide/`. Each top-level directory corresponds to a domain area, and markdown files within them are organized by topic, status, or depth.

| Directory | Purpose | Typical Contents |
|---|---|---|
| `architecture/` | High-level architecture and deployment topology | Overview, deployment topology, failure domains |
| `kubernetes/` | Kubernetes control plane and cluster operations | Control plane, node lifecycle, cert rotation, etcd |
| `storage/` | Storage systems and configurations | Ceph, Rook-Ceph, dedicated storage models |
| `monitoring/` | Observability and alerting configurations | Prometheus, Grafana, Alertmanager |
| `security/` | Security policies and implementations | Pod security, audit logging, image provenance |
| `network-matrix/` | Network communication and port documentation | External load balancers, CNI configurations |
| `secrets-management/` | Secrets and PKI management | Vault/OpenBao, certificate authority operations |
| `management-cluster/` | Fleet and cluster management | Argo CD, Keycloak, Rancher configurations |
| `automation/` | Automation and infrastructure as code | Ansible playbooks, Terraform configurations |
| `catalog/` | Document and version catalogs | catalog.json, version matrices |
| `decisions/` | Architectural decision records | ADRs with status and rationale |
| `compatibility/` | Version and component compatibility | Version matrices, technology selection |
| `lifecycle/` | Operational lifecycles | Backup, DR, upgrades |
| `operating-systems/` | OS-specific configurations | Oracle Linux, Ubuntu, host configurations |
| `service-mesh/` | Service mesh configurations | Istio, Linkerd, gateway API |
| `troubleshooting/` | Problem resolution guides | Common issues, debugging procedures |
| `site/` | Site-specific documentation | Environment-specific configs |
| `addons/` | Optional add-on components | Optional integrations, feature toggles |

### Navigation Index

All major sections and quick links are maintained in `repository/navigation-index.md`. When adding or removing a document, update this index to keep the map current.

### Catalog

The document catalog is stored in `catalog/catalog.json`. It lists every markdown file in the repository for consistency checks. Run `scripts/validate_catalog.py` after adding or removing docs to keep the catalog in sync.

---

## 🔗 Cross-Reference Integrity

All internal links must resolve to existing files and valid anchors. The repository uses `scripts/check_links.py` as the canonical validator.

### Validation Scope

- **Relative file links**: Target file must exist on disk at the resolved path
- **In-page anchors**: `#anchor` references must match a heading (`# Heading`) or explicit `<a id="anchor">` in the target file
- **External URLs** (`http://`, `https://`, `mailto:`, `tel:`) are skipped — only repository-internal links are validated

### Prevention Guidelines

- Run `scripts/check_links.py` before committing any document changes
- CI gate requires 0 broken links for merge approval
- When renaming a heading, update all anchor references or add explicit `<a id="old-anchor">` for backward compatibility
- If a markdown file is moved, update all relative links pointing to it

### Current Status

Running `python3 scripts/check_links.py` reports 0 broken links across the repository. All cross-references currently resolve successfully.

---

## 🔍 Duplicate Detection

Duplicate documentation is identified through multiple methods to surface overlapping or repurposed content.

### Identification Methods

| Method | Description |
|---|---|
| **Keyword overlap** | `grep -il "keyword"` across markdown files to surface candidates |
| **Heading similarity** | `scripts/compare_tree.py` compares heading structures across files |
| **Cross-reference audit** | `scripts/check_links.py` traces every link to verify target exists and anchor is valid |
| **Version drift check** | `scripts/validate_catalog.py` confirms pinned versions and check dates |

### Current Duplicate Candidates

| File A | File B | Overlap Type | Recommended Action |
|---|---|---|---|
| `architecture/02-deployment-topology.md` | `architecture/03-failure-domains.md` | Shared infrastructure sizing details | Consolidate sizing section into `02-deployment-topology.md` |
| `requirements/technology-selection-matrix.md` | `compatibility/version-matrix.md` | Version claims with source URLs | Merge version table into `technology-selection-matrix.md`; keep matrix as reference |
| `decisions/ADR-0010-management-cluster-design-and-what-runs-inside-it.md` | `management-cluster/rancher/rancher.md` | Management cluster scope description | Reference ADR from management-cluster docs; do not duplicate |

### Duplicate Detection Checklist

- [ ] Run `python3 scripts/check_links.py` — 0 broken links
- [ ] Run `python3 scripts/validate_catalog.py` — no missing docs, no bad placeholders
- [ ] Verify every cross-reference resolves (file exists + anchor valid)
- [ ] Confirm no two documents claim the same version without a shared source
- [ ] Ensure every version claim has a source URL and check date

### Known Conflicts (requires resolution)

| Conflict | Source A | Source B | Resolution |
|---|---|---|---|
| GPU sharing strategy | `ADR-0022-gpu-sharing-strategy.md` states MIG for production only; `gpu-ai/gpu-workers/drivers/scheduling/sharing.md` mentions time-slicing for dev | Both are correct per their scope — add cross-reference from workers doc to ADR-0022 and clarify scope tag | Add `See ADR-0022` header to workers doc; tag `production-only` on MIG section |
| Container runtime version | `ADR-0005-container-runtime.md` pins containerd `2.3.7`; `operating-systems/oracle-linux/host-configuration.md` references `2.3.5` | Oracle Linux package lags; update Oracle host doc to `2.3.7` or add `UNVERIFIED` tag | Update Oracle host doc to `2.3.7` VERIFIED |
| Ingress controller portfolio | `ADR-0007-ingress-controller-and-gateway-api.md` lists 3 deployed controllers; `network-matrix/external-load-balancer.md` lists 4 | Remove 4th from network-matrix or add to ADR deprecation schedule | Network-matrix: mark 4th as `Retired` per ADR-0028 schedule |

### Conflict Resolution Checklist

- [ ] Run `python3 scripts/check_links.py` — 0 broken links
- [ ] Run `python3 scripts/validate_catalog.py` — no catalog discrepancies
- [ ] Confirm every conflicting claim has a source URL and check date
- [ ] Document the resolution decision in the relevant ADR or file
- [ ] Tag one source as authoritative; the other becomes a reference or is retired

### Consolidation Candidates

| Target | Consolidate Into | Rationale | Impact |
|---|---|---|---|
| `requirements/component-guide-template.md` | `requirements/component-guide-backlog.md` | Template is a static scaffold; backlog contains the living list | Remove template; update any links to point to backlog format |
| `architecture/01-logical-diagram.md` | `architecture/00-overview.md` | Logical diagram is introductory material for the overview | Embed diagram markdown into `00-overview.md`; delete `01-logical-diagram.md` |
| `decisions/ADR-0029-cephadm-dedicated-storage-model.md` | `storage/ceph/cephadm-deployment.md` | ADR documents the decision; deployment doc implements it | Keep ADR as `Status: Accepted`; move implementation notes into deployment doc |

### Consolidation Workflow

1. **Review** — Read both source and target files; confirm no information loss
2. **Merge** — Copy unique content from source into target; update links
3. **Redirect** — Add a short "See [target]" note at the top of the source file
4. **Delete** — Remove the source file if it becomes a pure redirect
5. **Verify** — Run `python3 scripts/check_links.py` — 0 broken links
6. **Catalog** — Update `compatibility/version-matrix.md` if versions change hands

### Consolidation Checklist

- [ ] All cross-references updated to point at the new consolidated location
- [ ] `python3 scripts/check_links.py` reports 0 broken links
- [ ] No duplicate content remains in the repository
- [ ] Version claims and source URLs are preserved in the target file
- [ ] ADR status fields are updated if an ADR is retired or superseded

### Consolidation Procedure (bash)

```bash
# 1. Scan for duplicate candidates
grep -irl "keyword" *.md | sort | uniq -d > duplicate-candidates.txt

# 2. Check all links in the repo
python3 scripts/check_links.py
# Expected: 0 broken link(s) in /workspace/project/github/public-repository/cloud-native-guide

# 3. Validate catalog consistency
python3 scripts/validate_catalog.py
# Expected: no missing docs, no bad placeholders, no stale data

# 4. Review conflicts and consolidate
#   - Use diff to compare candidate pairs
#   - Resolve conflicts per the checklist above
#   - Merge or redirect as documented

# 5. Final verification
python3 scripts/check_links.py
# Must still report 0 broken link(s)
```

---

## 📄 Docs-as-Code Standards

All documentation in this repository follows docs-as-code principles, treating markdown files like source code.

### File Format

- **Extension**: `.md` (markdown)
- **Encoding**: UTF-8
- **Headings**: `# Heading 1`, `## Heading 2`, etc. (max 6 levels)
- **Explicit anchors**: Use `<a id="anchor-name"></a>` when heading-based anchors may conflict or need backward compatibility
- **Front matter**: Not currently used; if added, follow YAML front matter conventions

### Link Conventions

- Use relative paths for internal links: see [the check_links.py source](https://github.com/example/check_links.py) for the skip rules _(external URLs like `http://` are skipped)_
- Anchor links: `[](#anchor-name)` must match a heading or explicit ID in the target
- Avoid bare URLs; if linking to external resources, add a clear description

### Metadata Requirements

- **Version claims**: Every pinned version must have a source URL and check date
- **Catalog entry**: New documents likely need an entry in `catalog/catalog.json`
- **Cross-reference audit**: If the doc contains links to other repository files, add a checklist item in `duplicate-detection.md`

### Validation Gates

Before any document change is considered complete:

1. Run `python3 scripts/check_links.py` — must report 0 broken links
2. Run `python3 scripts/validate_catalog.py` — must report no missing docs or bad placeholders
3. Verify all cross-references resolve (file exists + anchor valid)
4. If version claims are involved, run `python3 scripts/validate_catalog.py`

### Adding New Documents

1. Create the `.md` file in the appropriate domain directory
2. Add an entry to `repository/navigation-index.md` if it's a top-level section
3. Add a catalog entry in `catalog/catalog.json` if the doc should appear in the document catalog
4. Run `python3 scripts/check_links.py` to verify all internal links resolve
5. If the doc references other repo files, add a cross-reference audit item in `duplicate-detection.md`

### Maintenance

- **Regular runs**: Run `check_links.py` before merging any pull request that modifies docs
- **Anchor updates**: When renaming a heading, update all anchor references or add explicit backward-compatible IDs
- **File moves**: Update all relative links if a markdown file is moved to a new path
- **Catalog sync**: After adding/removing docs, run `validate_catalog.py` to keep `catalog/catalog.json` in sync

### Current Validation Result

```bash
$ python3 scripts/check_links.py
0 broken link(s) in /workspace/project/github/public-repository/cloud-native-guide
```

All cross-references currently resolve with 0 broken links.

---
*Document generated 2026-11-26 as part of repository documentation structure audit.*