# Duplicate Detection Procedure

## 🔍 Duplicate Identification

Purpose: Find documentation that covers the same topic, contains overlapping information, or duplicates content across the repository.

### Identification Methods

| Method | Description | Check |
|---|---|---|
| **Keyword overlap** | Search for shared terminology across markdown files to surface candidates | `grep -il "keyword" *.md` |
| **Heading similarity** | Compare heading structures across files to detect repurposed content | `scripts/compare_tree.py` |
| **Cross-reference audit** | Trace every `[link](architecture/00-overview.md)` to verify the target exists and the anchor is valid | `scripts/check_links.py` |
| **Version drift check** | Confirm pinned versions and check dates are identical where content overlaps | `scripts/validate_catalog.py` |

### Current Duplicate Candidates

The following file pairs require review for possible consolidation:

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

---

## ⚠️ Conflicting Content

Purpose: Detect documentation that asserts contradictory information, different defaults, or divergent steps for the same operation.

### Conflict Detection Methods

| Method | Description | Check |
|---|---|---|
| **Side-by-side diff** | Compare two files that share a parent section or ADR context | `diff -u file_a.md file_b.md` |
| **Key-value drift** | Check that pinned versions, CIDRs, and port ranges agree across files | Manual review of CIDR/port tables |
| **Step ordering** | Verify that sequential steps in the guide remain in consistent order | Review step-by-step links in `README.md` |

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

---

## 📦 Consolidation Candidates

Purpose: Identify documentation that can be merged, retired, or redirected without losing information.

### Consolidation Priorities

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

---

## 🛠️ Procedure Summary

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

**DevOps Automator**: This procedure ensures the repository documentation remains consistent, versioned, and traceable. All changes must pass the link-check gate before merging.