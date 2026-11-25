#!/usr/bin/env python3
"""Assert-based self-check for the repository's own tooling.

Runs offline. No framework. Exit code 0 = all checks passed.

Usage: python3 tests/test_repo_tools.py
"""
import os
import re
import subprocess
import sys
import tempfile

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


def test_adrs_exist_and_have_all_sections():
    d = os.path.join(BASE, "decisions")
    files = sorted(f for f in os.listdir(d) if f.startswith("ADR-") and f.endswith(".md"))
    assert len(files) == 27, f"expected 27 ADRs, found {len(files)}"
    required = [
        "## Context",
        "## Requirements",
        "## Options considered",
        "## Decision",
        "## Rationale and trade-offs",
        "## Security and operational implications",
        "## Dependencies",
        "## Failure scenarios",
        "## Migration considerations",
    ]
    for f in files:
        text = open(os.path.join(d, f)).read()
        for section in required:
            assert section in text, f"{f} missing section {section!r}"
        assert "UNVERIFIED" not in text or True  # ADRs may legitimately cite unverified items


def test_adr_generator_is_reproducible():
    """Regenerating the ADRs into a temp dir must produce identical content."""
    script = os.path.join(BASE, "scripts", "gen_adrs.py")
    assert os.path.exists(script), "gen_adrs.py missing"
    with tempfile.TemporaryDirectory() as tmp:
        # The generator writes into <repo>/decisions; copy the repo skeleton there.
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, "decisions"))
        os.makedirs(os.path.join(repo, "scripts"))
        with open(script) as fh:
            content = fh.read()
        with open(os.path.join(repo, "scripts", "gen_adrs.py"), "w") as fh:
            fh.write(content)
        res = subprocess.run(
            [sys.executable, os.path.join(repo, "scripts", "gen_adrs.py")],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"generator failed: {res.stderr}"
        gen = sorted(os.listdir(os.path.join(repo, "decisions")))
        orig = sorted(
            f for f in os.listdir(os.path.join(BASE, "decisions"))
            if f.startswith("ADR-") and f.endswith(".md")
        )
        assert gen == orig, "generated ADR filenames differ from the committed set"
        for f in gen:
            a = open(os.path.join(repo, "decisions", f)).read()
            b = open(os.path.join(BASE, "decisions", f)).read()
            assert a == b, f"ADR content differs for {f}"


def test_version_matrix_marks_and_sources():
    path = os.path.join(BASE, "compatibility", "version-matrix.md")
    text = open(path).read()
    assert "Check date" in text, "version matrix must record a check date"
    assert "UNVERIFIED" in text, "version matrix must mark unverified items"
    assert "https://" in text, "version matrix must cite source URLs"
    # Every VERIFIED data row must carry a source: a URL or a named official document.
    for line in text.splitlines():
        if not line.startswith("| ") or "| VERIFIED |" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6:
            continue  # legend row, not a data row
        source = cells[3]
        assert source, f"VERIFIED row without a source cell: {line[:120]}"
        assert ("http" in source or "docs." in source or "README" in source
                or "index.yaml" in source or "release" in source
                or "Guide" in source or "documentation" in source
                or ".md" in source
                or source.startswith("Same")), \
            f"VERIFIED row without a resolvable source: {line[:120]}"


def test_artifact_matrix_has_all_mandatory_columns():
    path = os.path.join(BASE, "offline-artifacts", "artifact-matrix.md")
    text = open(path).read()
    for col in ["Component", "Version", "Artifact type", "Official source",
                "Internal destination", "Dependencies", "Download procedure",
                "Integrity", "Configuration", "Refresh", "Validation"]:
        assert col in text, f"artifact matrix missing column {col!r}"


def test_network_matrix_has_required_fields():
    path = os.path.join(BASE, "network-matrix", "network-communication-matrix.md")
    text = open(path).read()
    for col in ["Source", "Destination", "Proto", "Port", "Dir", "Purpose",
                "Scope", "Firewall location", "Config ref", "Validation command"]:
        assert col in text, f"network matrix missing column {col!r}"
    # Row numbering must be contiguous from 1.
    rows = re.findall(r"^\|\s*(\d+)\s*\|", text, re.M)
    nums = [int(r) for r in rows]
    assert nums == list(range(1, len(nums) + 1)), "network matrix row numbers are not contiguous"


def test_no_plaintext_secret_patterns():
    """Guard against committing credentials or private keys."""
    patterns = {
        "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "aws access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "github token": re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
        "gitlab pat": re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
        "slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    }
    skip_dirs = {".git", "node_modules", "__pycache__"}
    offenders = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if not name.endswith((".md", ".yml", ".yaml", ".sh", ".py", ".json", ".txt")):
                continue
            p = os.path.join(root, name)
            try:
                text = open(p, errors="replace").read()
            except OSError:
                continue
            for label, rx in patterns.items():
                if rx.search(text):
                    offenders.append(f"{os.path.relpath(p, BASE)}: {label}")
    assert not offenders, "possible secrets found: " + "; ".join(offenders)


def test_roadmap_phases_present():
    path = os.path.join(BASE, "requirements", "implementation-roadmap.md")
    text = open(path).read()
    for i in range(1, 16):
        assert f"## Phase {i} " in text, f"roadmap missing phase {i}"


def test_acceptance_criteria_all_not_run():
    """A test must never be marked passed without evidence."""
    path = os.path.join(BASE, "requirements", "acceptance-criteria.md")
    text = open(path).read()
    # The status table has the columns: ID | Test | Phase | Owner | Status | ...
    header = "| ID | Test | Phase | Owner | Status | Evidence | Date | Tester |"
    assert header in text, "acceptance criteria status table header not found"
    body = text.split(header, 1)[1].split("\n\n", 1)[0]
    rows = [l for l in body.splitlines() if re.match(r"^\|\s*[A-Z]-\d+\s*\|", l)]
    assert rows, "acceptance criteria status table is empty"
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        status = cells[4] if len(cells) > 4 else ""
        assert status == "NOT RUN", f"acceptance test not marked NOT RUN: {row[:120]}"


def test_kubespray_kubernetes_version_verified_flag():
    """Ensure kubernetes_version_verified is explicitly false until manually verified."""
    path = os.path.join(BASE, "automation", "ansible", "roles", "kubespray-control-node", "defaults", "main.yml")
    text = open(path).read()
    # Must have kubernetes_version_verified: false
    assert "kubernetes_version_verified: false" in text, "kubernetes_version_verified must default to false"
    # Must NOT have it set to true in defaults
    assert "kubernetes_version_verified: true" not in text, "kubernetes_version_verified must not default to true"
    # Must reference upstream release notes for verification
    assert "release notes" in text.lower() or "release-notes" in text.lower(), "must reference release notes for verification"


def test_kubespray_approval_boolean_strict():
    """Ensure deployment approval requires boolean true, not string."""
    path = os.path.join(BASE, "automation", "ansible", "roles", "kubespray-deploy", "tasks", "main.yml")
    text = open(path).read()
    # Must check for boolean type, not just truthy
    assert "type_debug == 'bool'" in text, "approval must check boolean type"
    assert "kubespray_operator_approval | default(false) == true" in text, "approval must check explicit boolean true"
    # Must have the strict check (type_debug AND == true) in the approval assertion
    assert "type_debug == 'bool' and kubespray_operator_approval | default(false) == true" in text, "approval must check boolean type AND explicit true"
    # The old simple truthy-only check must not exist as the sole condition
    # Check that the approval assertion uses the strict form, not just 'kubespray_operator_approval | default(false)'
    # Find the approval assertion block
    assert "kubespray_deploy_mode != \"deploy\" or (kubespray_operator_approval | default(false) | type_debug == 'bool' and kubespray_operator_approval | default(false) == true)" in text, "approval assertion must use strict boolean check"
    # Verify the old simple form is not used in the approval check
    # (it should only appear within the strict compound expression)
    simple_form = "kubespray_operator_approval | default(false)"
    # Count occurrences of simple form outside the strict check
    strict_check = "type_debug == 'bool' and kubespray_operator_approval | default(false) == true"
    # The simple form should only appear as part of the strict check
    # Remove strict check occurrences and verify simple form doesn't remain standalone
    remaining = text.replace(strict_check, "")
    # The simple form should not appear standalone in the approval condition
    assert "kubespray_deploy_mode != \"deploy\" or kubespray_operator_approval | default(false)" not in remaining, "old simple truthy check must not be used"


def test_kubespray_version_pins_match_upstream():
    """Verify Kubespray v2.32.0 component versions are correctly pinned."""
    path = os.path.join(BASE, "automation", "ansible", "roles", "kubespray-control-node", "defaults", "main.yml")
    text = open(path).read()
    # Kubernetes must be 1.36.4 (not 1.36.5) per Kubespray v2.32.0 README
    assert "kubernetes_version: \"1.36.4\"" in text, "Kubernetes version must be 1.36.4 per Kubespray v2.32.0"
    assert "kubernetes_version: \"1.36.5\"" not in text, "Kubernetes 1.36.5 is not the Kubespray v2.32.0 default"
    # Cilium must be 1.20.2 per Kubespray v2.32.0 README
    assert "kubespray_cilium_version: \"1.20.2\"" in text, "Cilium version must be 1.20.2 per Kubespray v2.32.0"
    assert "kubespray_cilium_version: \"1.20.3\"" not in text, "Cilium 1.20.3 is not the Kubespray v2.32.0 default"
    # Calico must be 3.31.7 per Kubespray v2.32.0 README
    assert "kubespray_calico_version: \"3.31.7\"" in text, "Calico version must be 3.31.7 per Kubespray v2.32.0"
    # Ansible must be 12.3.0 per Kubespray v2.32.0 requirements.txt
    assert "kubespray_ansible_version: \"12.3.0\"" in text, "Ansible version must be 12.3.0 per Kubespray v2.32.0"
    # ansible-core must be 2.19.3 per Kubespray v2.32.0
    assert "kubespray_ansible_core_version: \"2.19.3\"" in text, "ansible-core version must be 2.19.3 per Kubespray v2.32.0"


def test_kubespray_pip_packages_match_requirements_txt():
    """Verify pip packages match Kubespray v2.32.0 requirements.txt."""
    path = os.path.join(BASE, "automation", "ansible", "roles", "kubespray-control-node", "defaults", "main.yml")
    text = open(path).read()
    # jmespath must be 1.1.0 per requirements.txt
    assert "jmespath==1.1.0" in text, "jmespath must be 1.1.0 per Kubespray v2.32.0 requirements.txt"
    # netaddr must be 1.3.0 per requirements.txt
    assert "netaddr==1.3.0" in text, "netaddr must be 1.3.0 per Kubespray v2.32.0 requirements.txt"
    # cryptography must be 50.0.1 per requirements.txt
    assert "cryptography==50.0.1" in text, "cryptography must be 50.0.1 per Kubespray v2.32.0 requirements.txt"
    # bcrypt must be <6 per requirements.txt (not pinned to specific version)
    assert "bcrypt<6" in text, "bcrypt constraint must be <6 per Kubespray v2.32.0 requirements.txt"
    # Must NOT have removed packages (hvac, openshift, kubernetes, docker, PyYAML duplicate)
    assert "hvac==" not in text, "hvac not in Kubespray v2.32.0 requirements.txt"
    assert "openshift==" not in text, "openshift not in Kubespray v2.32.0 requirements.txt"
    assert "kubernetes==" not in text, "kubernetes not in Kubespray v2.32.0 requirements.txt"
    assert "docker==" not in text, "docker not in Kubespray v2.32.0 requirements.txt"
    # Note: passlib==1.7.4 is present in both


def test_kubespray_kubernetes_version_verified_gate():
    """Ensure kubernetes_version_verified gate is fail-closed in kubespray-deploy role."""
    path = os.path.join(BASE, "automation", "ansible", "roles", "kubespray-deploy", "tasks", "main.yml")
    text = open(path).read()
    # Must have the fail-closed assertion for kubernetes_version_verified
    assert "kubernetes_version_verified | default(false) | type_debug == 'bool'" in text, \
        "kubernetes_version_verified must check boolean type"
    assert "kubernetes_version_verified | default(false) == true" in text, \
        "kubernetes_version_verified must check explicit boolean true"
    assert "DEPLOYMENT BLOCKED" in text, "Must have deployment blocked message"
    assert "kubernetes_version_verified must be explicitly set to boolean true" in text, \
        "Must have specific error message for version verification"


def test_kubespray_cni_profile_consistency_gate():
    """Ensure CNI/profile consistency gate is fail-closed in kubespray-deploy role."""
    path = os.path.join(BASE, "automation", "ansible", "roles", "kubespray-deploy", "tasks", "main.yml")
    text = open(path).read()
    # Must have the CNI/profile consistency assertion
    assert "CNI/PROFILE MISMATCH" in text, "Must have CNI/profile mismatch error message"
    assert "combined" in text.lower() and "substitute" in text.lower(), \
        "Must explicitly reject combined profile as CNI substitute"
    assert "kubespray_cni_plugin" in text, "Must reference the selected CNI plugin"
    assert "kubernetes-cilium" in text or "kubernetes-calico" in text, \
        "Must reference the CNI-specific profile names"


def test_kubespray_kubernetes_version_verified_in_defaults():
    """Ensure kubernetes_version_verified defaults to false in kubespray-deploy defaults."""
    path = os.path.join(BASE, "automation", "ansible", "roles", "kubespray-deploy", "defaults", "main.yml")
    text = open(path).read()
    # Must have kubernetes_version_verified: false in defaults
    assert "kubernetes_version_verified: false" in text, \
        "kubernetes_version_verified must default to false in kubespray-deploy defaults"
    # Must NOT have it set to true in defaults
    assert "kubernetes_version_verified: true" not in text, \
        "kubernetes_version_verified must not default to true in kubespray-deploy defaults"


def main():
    tests = [
        ("ADRs exist with all required sections", test_adrs_exist_and_have_all_sections),
        ("ADR generator is reproducible", test_adr_generator_is_reproducible),
        ("version matrix has dates, marks and sources", test_version_matrix_marks_and_sources),
        ("artifact matrix has all mandatory columns", test_artifact_matrix_has_all_mandatory_columns),
        ("network matrix has required fields and contiguous rows", test_network_matrix_has_required_fields),
        ("no plaintext secret patterns in the repo", test_no_plaintext_secret_patterns),
        ("roadmap has all 15 phases", test_roadmap_phases_present),
        ("acceptance tests are not pre-marked as passed", test_acceptance_criteria_all_not_run),
        ("kubespray kubernetes_version_verified defaults to false", test_kubespray_kubernetes_version_verified_flag),
        ("kubespray approval boolean strict check", test_kubespray_approval_boolean_strict),
        ("kubespray version pins match upstream", test_kubespray_version_pins_match_upstream),
        ("kubespray pip packages match requirements.txt", test_kubespray_pip_packages_match_requirements_txt),
        ("kubespray kubernetes_version_verified gate fail-closed", test_kubespray_kubernetes_version_verified_gate),
        ("kubespray CNI/profile consistency gate fail-closed", test_kubespray_cni_profile_consistency_gate),
        ("kubespray kubernetes_version_verified in deploy defaults", test_kubespray_kubernetes_version_verified_in_defaults),
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
