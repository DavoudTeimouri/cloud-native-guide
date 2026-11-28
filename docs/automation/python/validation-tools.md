# Automated Validation Tools

## 🔍 Consistency Checks

### Purpose

Validate structural and semantic consistency across the documentation repository. These checks ensure that all files adhere to the same formatting rules, version references, and cross-reference patterns.

### Checks Included

- **Duplicate content detection**: Identify overlapping topics across markdown files using keyword and heading similarity analysis
- **Version drift detection**: Verify that pinned versions and check dates are identical where content overlaps
- **formatting compliance**: Check that markdown files follow the repository's style conventions (headings, tables, links)
- **Link pattern validation**: Ensure all internal links follow expected patterns; anchors must resolve to headings or explicit `<a name>` tags

### Usage

```bash
# Run all consistency checks
python3 scripts/validate_catalog.py

# Check for duplicates
grep -irl "keyword" automation/**/*.md | sort | uniq -d > duplicate-candidates.txt
```

## 🔗 Cross-Reference Validation

### Purpose

Verify that every cross-reference in the documentation resolves correctly — both the target file exists and any in-page anchors are valid.

### Checks Included

- **File existence**: Every link target must exist in the repository — documentation example pattern, do not create `path/to/file.md`
- **Anchor validity**: Every `#anchor` reference must correspond to a heading or explicit `<a name="...">` in the target file
- **Broken link detection**: Catch dead anchors and missing files before they reach readers
- **Relative path correctness**: Ensure all internal links use correct relative paths from the repository root

### Usage

```bash
# Run the link checker
python3 scripts/check_links.py

# Expected: 0 broken link(s) in /workspace/project/github/public-repository/cloud-native-guide
```

### Anchor Resolution

The `scripts/check_links.py` tool detects:

- Missing file references: used as documentation example only — do not create a file named `nonexistent.md`
- Missing anchors: used as documentation example only — no heading generates the anchor `#missing-anchor`
- Explicit anchor mismatches: used as documentation example only — anchor `#anchor-name` does not exist in the target file

## 🚫 Broken Link Detection

### Purpose

Scan the entire repository for broken relative links and dead in-page anchors. This is the primary gate before any merge or publication.

### How It Works

- Walks all `.md` files in the repository
- Extracts Markdown link syntax `][(url)]`
- Skips external URLs (http/https/mailto/tel)
- Checks relative file existence
- Validates in-page anchors against generated heading slugs
- Reports each broken link with its source file path

### Output Format

```text
<relative-path>: missing file <target>
<relative-path>: missing anchor <target>
```

### Usage

```bash
python3 scripts/check_links.py
# Reports: N broken link(s) in <repository-root>
# Exit code: 1 if problems found, 0 if clean
```

## ⚙️ Configuration Validation

### Purpose

Validate configuration files (YAML, JSON, HCL) used throughout the repository for correctness, required fields, and schema compliance.

### Checks Included

- **Schema validation**: Verify configuration files conform to expected JSON/YAML schemas
- **Required field presence**: Ensure all mandatory fields are present
- **Value range checks**: Validate that numeric values (ports, sizes, counts) are within acceptable ranges
- **Type checking**: Verify that values are the expected types (string, integer, boolean, list)
- **Cross-config consistency**: Ensure configuration values are consistent across multiple files

### Usage

```bash
# Example: Validate YAML config files
python3 -c "
import yaml, sys, os
base = '/workspace/project/github/public-repository/cloud-native-guide'
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__'}]
    for f in files:
        if f.endswith('.yaml') or f.endswith('.yml'):
            path = os.path.join(root, f)
            try:
                with open(path) as fh:
                    data = yaml.safe_load(fh)
                # Add specific validation rules here
            except Exception as e:
                print(f'{path}: YAML parse error: {e}')
"
```

## 🔄 CI Integration

### Purpose

Integrate validation tools into the CI/CD pipeline so that every pull request passes all consistency, link, and configuration checks before merging.

### Recommended GitHub Actions Workflow

```yaml
name: Validation Gates

on:
  pull_request:
    branches: [main]

jobs:
  consistency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run link check
        run: python3 scripts/check_links.py
      - name: Run catalog validation
        run: python3 scripts/validate_catalog.py
      - name: Check for duplicates
        run: |
          grep -irl "keyword" automation/**/*.md | sort | uniq -d > duplicate-candidates.txt
          if [ -s duplicate-candidates.txt ]; then
            echo "Duplicate candidates found — review required"
            exit 1
          fi

  config-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate YAML configs
        run: python3 -c "
import yaml, os
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__'}]
    for f in files:
        if f.endswith('.yaml') or f.endswith('.yml'):
            path = os.path.join(root, f)
            try:
                with open(path) as fh:
                    data = yaml.safe_load(fh)
            except Exception as e:
                print(f'{path}: YAML parse error: {e}')
"

  # Fail the PR if any check fails
    if: failure()
```

### Failure Conditions

- `scripts/check_links.py` returns exit code 1 (broken links found)
- `scripts/validate_catalog.py` reports missing docs, bad placeholders, or stale data
- Duplicate content candidates are detected without review
- Any YAML/JSON configuration fails schema validation

---
**DevOps Automator**: This documentation ensures automated validation is embedded in the development workflow. All changes must pass the link-check gate before merging. Regularly run these checks to catch drift, duplicates, and configuration errors early.
