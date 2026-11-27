# Repository Cross-Reference Validation

## 🎯 Purpose

Automated validation of all documentation cross-references across the cloud-native-guide repository. This file documents the validation process, link integrity checks, and broken link prevention strategies to ensure operators can always navigate to valid targets.

## 🔍 Validation Strategy

### Automated Cross-Reference Checking

The repository uses `scripts/check_links.py` — a stdlib-only Python script that scans every `.md` file for markdown link syntax and validates:

- **Relative file links**: Target file must exist on disk
- **In-page anchors**: `#anchor` references must match a heading or explicit `<a id="anchor">` in the target file
- **External URLs** (http/https/mailto/tel) are skipped — only repository-internal links are validated

Run the validator:

```bash
python3 scripts/check_links.py
```

Output reports broken links in the format `<relative-path>: <issue>` and exits with code 1 if any problems exist.

### Broken Link Prevention

- **Pre-commit hook recommended**: Run `scripts/check_links.py` before committing any document changes
- **CI gate**: `check_links.py` must report 0 broken links for merge approval
- **Golden path validation**: All new documents and significant restructures must pass linkcheck locally before push
- **Cross-reference audit** (duplicate-detection.md:58): Trace every link to verify the target exists and the anchor is valid

## 📋 Validation Checklist

| Item | Description | Command |
|------|-------------|---------|
| File existence | Every reference to `path/to/file.md` must exist | `check_links.py` |
| Anchor validity | Every reference to `#anchor` must match a heading or explicit ID in the target | `check_links.py` |
| No duplicate version claims | No two documents should claim the same version without a shared source | `validate_catalog.py` |
| Catalog consistency | `catalog/catalog.json` must reflect all documented docs | `validate_catalog.py` |

Run all local checks:

```bash
python3 scripts/check_links.py
python3 scripts/validate_catalog.py
python3 scripts/test_repo_tools.py
```

## 🛠️ Adding New Documents

When adding a new markdown document:

1. **Add to navigation-index.md** (if appropriate) — see `repository/navigation-index.md` for the structure
2. **Run `check_links.py`** after creation to verify all internal links resolve
3. **Update catalog** if the doc should appear in `catalog/catalog.json`
4. **Add cross-reference audit checklist item** in `duplicate-detection.md` if the doc contains links to other reposurce files

## 📊 Current Status

```bash
$ python3 scripts/check_links.py
0 broken link(s) in /workspace/project/github/public-repository/cloud-native-guide
```

All cross-references currently resolve with 0 broken links.

## 🔄 Maintenance

- **Regular runs**: Run `check_links.py` before merging any pull request that modifies docs
- **Anchor updates**: When renaming a heading, update all anchor references to point to the new heading, or add explicit `<a id="old-anchor">` for backward compatibility
- **File moves**: Update all relative links if a markdown file is moved to a new path
- **Catalog sync**: After adding/removing docs, run `validate_catalog.py` to keep `catalog/catalog.json` in sync

---

**Last validated**: `check_links.py` reports 0 broken links

**Related**:
- `scripts/check_links.py` — Link validation script
- `scripts/validate_catalog.py` — Catalog consistency validation
- `repository/navigation-index.md` — Central navigation index
- `duplicate-detection.md` — Cross-reference audit guidelines