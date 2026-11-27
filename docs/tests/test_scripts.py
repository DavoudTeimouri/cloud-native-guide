#!/usr/bin/env python3
"""Assert-based self-check for critical repository scripts.

Runs offline. No framework. Exit code 0 = all checks passed.

Usage: python3 tests/test_scripts.py
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []


def check(name, fn):
    try:
        fn()
        print(f"OK   {name}")
    except AssertionError as e:
        FAILURES.append((name, str(e)))
        print(f"FAIL {name}: {e}")
    except Exception as e:  # noqa: BLE001
        FAILURES.append((name, repr(e)))
        print(f"ERROR {name}: {e!r}")


def run_script(script_path, args=None, expect_exit=0):
    """Run a Python script and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
    return result.returncode, result.stdout, result.stderr


def test_check_links_runs_clean():
    """check_links.py exits 0 with 0 broken links."""
    code, out, err = run_script(os.path.join(BASE, "scripts", "check_links.py"))
    assert code == 0, f"check_links.py exited with {code}: {err}"
    assert "0 broken link" in out, f"check_links.py output doesn't show 0 broken links: {out}"


def test_validate_catalog_runs_clean():
    """validate_catalog.py exits 0 with all checks passed."""
    code, out, err = run_script(os.path.join(BASE, "scripts", "validate_catalog.py"))
    assert code == 0, f"validate_catalog.py exited with {code}: {err}"
    assert "All checks passed" in out, f"validate_catalog.py output doesn't show all checks passed: {out}"


def test_fetch_versions_no_crash():
    """fetch_versions.py runs without unhandled Python exceptions."""
    code, out, err = run_script(os.path.join(BASE, "scripts", "fetch_versions.py"))
    # Network-dependent script: may fail on network, but must not crash with traceback
    assert "Traceback" not in err, f"fetch_versions.py crashed with traceback: {err}"
    assert "SyntaxError" not in err, f"fetch_versions.py has syntax error: {err}"


def test_kubespray_release_matrix_no_crash():
    """kubespray_release_matrix.py runs without unhandled Python exceptions."""
    code, out, err = run_script(os.path.join(BASE, "scripts", "kubespray_release_matrix.py"), ["release-2.32"])
    # Network-dependent script: may fail on network, but must not crash with traceback
    assert "Traceback" not in err, f"kubespray_release_matrix.py crashed with traceback: {err}"
    assert "SyntaxError" not in err, f"kubespray_release_matrix.py has syntax error: {err}"


def test_build_site_syntax():
    """build_site.py compiles without syntax errors."""
    import py_compile
    path = os.path.join(BASE, "scripts", "build_site.py")
    py_compile.compile(path, doraise=True)


def test_acceptance_status_syntax():
    """acceptance_status.py compiles without syntax errors."""
    import py_compile
    path = os.path.join(BASE, "scripts", "acceptance_status.py")
    py_compile.compile(path, doraise=True)


def test_compare_tree_syntax():
    """compare_tree.py compiles without syntax errors."""
    import py_compile
    path = os.path.join(BASE, "scripts", "compare_tree.py")
    py_compile.compile(path, doraise=True)


def test_verify_github_syntax():
    """verify_github.py compiles without syntax errors."""
    import py_compile
    path = os.path.join(BASE, "scripts", "verify_github.py")
    py_compile.compile(path, doraise=True)


def test_all_scripts_have_shebang():
    """Every Python script in scripts/ has a shebang line."""
    scripts_dir = os.path.join(BASE, "scripts")
    missing = []
    for f in sorted(os.listdir(scripts_dir)):
        if not f.endswith(".py"):
            continue
        path = os.path.join(scripts_dir, f)
        with open(path) as fh:
            first = fh.readline()
        if not first.startswith("#!"):
            missing.append(f)
    assert not missing, f"Scripts missing shebang: {missing}"


def main():
    tests = [
        ("check_links.py runs clean", test_check_links_runs_clean),
        ("validate_catalog.py runs clean", test_validate_catalog_runs_clean),
        ("fetch_versions.py no crash", test_fetch_versions_no_crash),
        ("kubespray_release_matrix.py no crash", test_kubespray_release_matrix_no_crash),
        ("build_site.py compiles", test_build_site_syntax),
        ("acceptance_status.py compiles", test_acceptance_status_syntax),
        ("compare_tree.py compiles", test_compare_tree_syntax),
        ("verify_github.py compiles", test_verify_github_syntax),
        ("All scripts have shebang", test_all_scripts_have_shebang),
    ]
    for name, fn in tests:
        check(name, fn)
    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
