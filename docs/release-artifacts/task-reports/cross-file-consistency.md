# TASK 007.8 — Phase 4 Cross-File Consistency

**Task:** Controlled Content Reconciliation, Phase 4
**Scope:** Cross-file consistency between the three reconciled scripts and with the repository

## 1. Cross-File Consistency Between the Three Files

| Dimension | compare_tree.py | gh_refs.py | verify_github.py | Consistent? |
|-----------|---------------|------------|-----------------|-------------|
| Shebang | `#!/usr/bin/env python3` | `#!/usr/bin/env python3` | `#!/usr/bin/env python3` | ✅ Yes |
| Docstring | Present | Present | Present | ✅ Yes |
| Stdlib-only imports | json, os, subprocess, sys, urllib.request | json, subprocess, sys, urllib.error, urllib.request | json, os, subprocess, sys, urllib.request | ✅ Yes |
| GitHub API auth | Bearer token from $GITHUB_TOKEN | Bearer token from $GITHUB_TOKEN | Bearer token from $GITHUB_TOKEN | ✅ Yes |
| Headers | Authorization, Accept, User-Agent | Authorization, Accept, User-Agent | Authorization, Accept, User-Agent | ✅ Yes |
| User-Agent | cloud-native-guide-verify | cloud-native-guide-verify | cloud-native-guide-verify | ✅ Yes |
| `get()` helper function | Yes | Yes | Yes | ✅ Yes |
| Read-only operations | Yes | refs mode yes; delete-repo explicit | Yes | ✅ Yes |
| CLI interface | owner repo branch local_dir | refs <owner> <repo> or delete-repo <owner> <repo> | owner repo branch | ✅ Yes (consistent CLI pattern) |

## 2. Consistency with Existing Repository Scripts

The 3 new scripts follow the same patterns as existing scripts in the repository:

| Pattern | compare_tree.py | gh_refs.py | verify_github.py |
|---------|---------------|------------|-----------------|
| Shebang line | ✅ `#!/usr/bin/env python3` | ✅ `#!/usr/bin/env python3` | ✅ `#!/usr/bin/env python3` |
| Module docstring | ✅ Present | ✅ Present | ✅ Present |
| GitHub API base URL | `https://api.github.com` | `https://api.github.com` | `https://api.github.com` |
| Auth pattern | Bearer token from env | Bearer token from env | Bearer token from env |
| `get()` helper | Yes | Yes | Yes |
| `Request` + `urlopen` | Yes | Yes | Yes |
| Headers dict | Yes | Yes | Yes |
| Timeout | 90s | 60s | 60s |
| `sys.argv` CLI | Yes | Yes | Yes |
| Stdlib-only | Yes | Yes | Yes |

## 3. Catalog / Site / Workflow Consistency

| Dimension | compare_tree.py | gh_refs.py | verify_github.py | Consistent? |
|-----------|---------------|------------|-----------------|-------------|
| No catalog references | ✅ None | ✅ None | ✅ None | Yes |
| No site/data.json references | ✅ None | ✅ None | ✅ None | Yes |
| No site/modules references | ✅ None | ✅ None | ✅ None | Yes |
| No workflow references | ✅ None | ✅ None | ✅ None | Yes |
| No test references | ✅ None | ✅ None | ✅ None | Yes |
| No script references (other scripts) | ✅ None | ✅ None | ✅ None | Yes |

## 4. Cross-File References

| File | Internal References | Status |
|------|-------------------|--------|
| `scripts/compare_tree.py` | None (self-contained) | ✅ Standalone |
| `scripts/gh_refs.py` | None (self-contained) | ✅ Standalone |
| `scripts/verify_github.py` | None (self-contained) | ✅ Standalone |

All 3 scripts are mutually independent with no cross-file references.

## 5. Deferred Consistency Issues

| Issue | Disposition |
|-------|-------------|
| None | No deferred consistency issues |

## 6. Conclusion

The 3 files are mutually consistent, consistent with existing repository script patterns (same auth pattern, same `get()` helper, same header format, same stdlib-only approach), and have no cross-file references or dependencies on catalog/site/workflow/test files. No contradictions found.
