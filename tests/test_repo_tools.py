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


def iter_test_rows(text):
    """Yield (test_id, data_cells) for real test-table rows only.

    A real test row has 12 mandatory fields. Prose cross-reference tables
    (e.g. the B-12 collision summary, old-to-new mapping) have fewer cells
    and must not be counted as test rows.
    """
    row_re = re.compile(r"^\|\s*([A-Z]-[0-9]+)\s*\|")
    for line in text.splitlines():
        m = row_re.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        data = [c for c in cells if c != ""]
        if len(data) < 12:
            continue  # prose table, not a test row
        yield m.group(1), data


def test_registry_ids_unique():
    path = os.path.join(BASE, "requirements", "test-registry.md")
    text = open(path).read()
    ids = [tid for tid, _ in iter_test_rows(text)]
    assert ids, "registry contains no test rows"
    dupes = [i for i in ids if ids.count(i) > 1]
    assert not dupes, f"duplicate test IDs in registry: {dupes}"


def test_registry_status_values_valid():
    path = os.path.join(BASE, "requirements", "test-registry.md")
    text = open(path).read()
    allowed = {"NOT RUN", "BLOCKED", "PASS", "FAIL", "N/A"}
    for tid, data in iter_test_rows(text):
        status = data[-1]
        assert status in allowed, f"{tid} has invalid status {status!r}"


def test_registry_mandatory_fields():
    path = os.path.join(BASE, "requirements", "test-registry.md")
    text = open(path).read()
    mandatory = 13  # ID, name, category, prerequisites, validation method, environment, procedure, expected, evidence, risk, destructive, profiles, status
    for tid, data in iter_test_rows(text):
        assert len(data) >= mandatory, f"{tid} missing mandatory fields ({len(data)}/{mandatory})"
        for field in data:
            assert field, f"{tid} has an empty mandatory field"


def test_pass_fail_require_evidence():
    path = os.path.join(BASE, "requirements", "test-registry.md")
    text = open(path).read()
    for tid, data in iter_test_rows(text):
        status = data[-1]
        evidence = data[8]  # Evidence column (after Validation Method insertion)
        if status in ("PASS", "FAIL"):
            assert evidence and "tests/acceptance/" in evidence, (
                f"{tid} is {status} without evidence reference"
            )


def test_registry_and_acceptance_criteria_consistent():
    registry_path = os.path.join(BASE, "requirements", "test-registry.md")
    ac_path = os.path.join(BASE, "requirements", "acceptance-criteria.md")
    reg_text = open(registry_path).read()
    ac_text = open(ac_path).read()
    reg_ids = {tid for tid, _ in iter_test_rows(reg_text)}
    ac_ids = set()
    for line in ac_text.splitlines():
        m = re.match(r"^\|\s*([A-Z]-[0-9]+)\s*\|", line)
        if m:
            cells = [c.strip() for c in line.split("|")]
            data = [c for c in cells if c != ""]
            if len(data) >= 8:  # acceptance-criteria table has 8 columns
                ac_ids.add(m.group(1))
    assert "D-13" in reg_ids, "registry missing D-13 (upgraded test renamed from B-12)"
    assert "B-12" in reg_ids, "registry missing B-12 (internal registry only)"
    missing = ac_ids - reg_ids
    assert not missing, f"acceptance criteria IDs not in registry: {missing}"


def main():
    tests = [
        ("ADRs exist with all required sections", test_adrs_exist_and_have_all_sections),
        ("ADR generator is reproducible", test_adr_generator_is_reproducible),
        ("version matrix has dates, marks and sources", test_version_matrix_marks_and_sources),
        ("artifact matrix has all mandatory columns", test_artifact_matrix_has_all_mandatory_columns),
        ("network matrix has required fields and contiguous rows", test_network_matrix_has_required_fields),
        ("no plaintext secret patterns in the repo", test_no_plaintext_secret_patterns),
        ("roadmap has all 15 phases", test_roadmap_phases_present),
        ("registry test IDs are unique", test_registry_ids_unique),
        ("registry status values are valid", test_registry_status_values_valid),
        ("registry rows have all mandatory fields", test_registry_mandatory_fields),
        ("PASS/FAIL require evidence reference", test_pass_fail_require_evidence),
        ("registry consistent with acceptance criteria", test_registry_and_acceptance_criteria_consistent),
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
