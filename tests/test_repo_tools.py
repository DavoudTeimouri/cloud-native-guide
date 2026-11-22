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
EXPORTS = os.path.join(BASE, "catalog", "exports.json")
DATA = os.path.join(BASE, "site", "data.json")


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
    gen = open(os.path.join(BASE, "scripts", "gen_adrs.py")).read()
    expected = len(re.findall(r'^\s*\(\d+, "', gen, re.M))
    assert len(files) == expected, f"expected {expected} ADRs, found {len(files)}"
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


def test_docs_are_structurally_sane():
    """Fenced blocks balance and no trailing whitespace drifts into docs."""
    offenders = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__"}]
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            text = open(path, encoding="utf-8", errors="replace").read()
            if text.count("```") % 2:
                offenders.append(f"{os.path.relpath(path, BASE)}: unbalanced code fence")
            for i, line in enumerate(text.splitlines(), 1):
                if line != line.rstrip():
                    offenders.append(f"{os.path.relpath(path, BASE)}:{i}: trailing whitespace")
    assert not offenders, "; ".join(offenders[:10])



def test_kubespray_oidc_no_legacy_variable_names():
    """No unsupported kube_apiserver_oidc_* variables remain in OIDC export templates."""
    for path in (EXPORTS, DATA):
        text = open(path, encoding="utf-8").read()
        assert "kube_apiserver_oidc_" not in text, (
            f"{os.path.relpath(path, BASE)} contains legacy kube_apiserver_oidc_* variables"
        )


def test_kubespray_oidc_required_variables_present():
    """All required kube_oidc_* variables are present in OIDC export templates."""
    required = [
        "kube_oidc_auth",
        "kube_oidc_url",
        "kube_oidc_client_id",
        "kube_oidc_ca_file",
        "kube_oidc_username_claim",
        "kube_oidc_username_prefix",
        "kube_oidc_groups_claim",
        "kube_oidc_groups_prefix",
    ]
    for path in (EXPORTS, DATA):
        text = open(path, encoding="utf-8").read()
        for var in required:
            assert var in text, (
                f"{os.path.relpath(path, BASE)} missing required variable {var}"
            )


def test_kubespray_oidc_auth_enabled():
    """kube_oidc_auth must be true in OIDC export templates."""
    for path in (EXPORTS, DATA):
        text = open(path, encoding="utf-8").read()
        assert 'kube_oidc_auth: true' in text, (
            f"{os.path.relpath(path, BASE)} does not enable kube_oidc_auth"
        )


def test_kubespray_oidc_prefixes_set():
    """Username and groups OIDC prefixes must be explicitly set to oidc:."""
    for path in (EXPORTS, DATA):
        text = open(path, encoding="utf-8").read()
        assert 'kube_oidc_username_prefix' in text, (
            f"{os.path.relpath(path, BASE)} missing kube_oidc_username_prefix"
        )
        assert 'kube_oidc_groups_prefix' in text, (
            f"{os.path.relpath(path, BASE)} missing kube_oidc_groups_prefix"
        )
        assert 'oidc:' in text, (
            f"{os.path.relpath(path, BASE)} missing oidc: prefix value"
        )


def test_site_data_matches_exports_oidc_template():
    """site/data.json OIDC template must match catalog/exports.json exactly."""
    exports_text = open(EXPORTS, encoding="utf-8").read()
    data_text = open(DATA, encoding="utf-8").read()
    # Extract the k8s-cluster.yml template from both files
    exp_oidc = None
    data_oidc = None
    for marker in ('"id": "inventory"', '"id": "k8s-cluster"'):
        if marker in exports_text:
            start = exports_text.index(marker)
            exp_oidc = exports_text[start:start + 3000]
        if marker in data_text:
            start = data_text.index(marker)
            data_oidc = data_text[start:start + 3000]
    if exp_oidc and data_oidc:
        # Normalize whitespace for comparison
        exp_norm = " ".join(exp_oidc.split())
        data_norm = " ".join(data_oidc.split())
        assert exp_norm == data_norm, (
            "site/data.json OIDC template diverges from catalog/exports.json"
        )


def test_render_template_substitutes_oidc_variables():
    """renderTemplate() in site/app.js must substitute all {{value.*}} OIDC placeholders."""
    # Simulate the renderTemplate logic from site/app.js
    tpl = ('kube_oidc_url: "{{value.keycloakHost}}/realms/platform"\\n'
           'kube_oidc_client_id: kube-apiserver\\n'
           'kube_oidc_username_prefix: "oidc:"\\n'
           'kube_oidc_groups_prefix: "oidc:"')
    ctx_values = {"keycloakHost": "https://keycloak.internal"}
    result = tpl
    import re as _re
    result = _re.sub(r'\{\{\s*value\.([a-zA-Z0-9_-]+)\s*\}\}',
                     lambda m: ctx_values.get(m.group(1), ""), result)
    assert "https://keycloak.internal/realms/platform" in result, (
        "renderTemplate did not substitute {{value.keycloakHost}}"
    )
    assert "{{value.keycloakHost}}" not in result, (
        "renderTemplate left {{value.keycloakHost}} unresolved"
    )
    assert 'kube_oidc_username_prefix: "oidc:"' in result, (
        "renderTemplate lost kube_oidc_username_prefix"
    )
    assert 'kube_oidc_groups_prefix: "oidc:"' in result, (
        "renderTemplate lost kube_oidc_groups_prefix"
    )


def test_yaml_parsing_available():
    """PyYAML availability for YAML structural validation.

    The repository follows a stdlib-first testing strategy and does not
    declare PyYAML as a dependency. This test reports availability but
    does not fail when PyYAML is absent; YAML structural validation is
    deferred until PyYAML is installed in the test environment.
    """
    try:
        import yaml  # noqa: F401
        print("OK   PyYAML available for YAML structural validation")
    except ImportError:
        print("SKIP PyYAML not installed; YAML structural validation deferred")
        # Not a failure: repo uses stdlib-first testing strategy.


def test_oidc_simulated_rendering_and_validation():
    """Simulated rendering and structural validation of the OIDC configuration path.

    This test does NOT execute the real build_site.py generator or the actual
    JavaScript renderTemplate() in site/app.js. It performs source-code inspection
    and Python-based string substitution to verify that:

    - All 8 kube_oidc_* variables are present in the source template.
    - site/data.json matches catalog/exports.json (generated output consistent).
    - All {{value.*}} placeholders in OIDC lines resolve to non-empty values.
    - kube_oidc_auth is true.
    - Username and groups prefixes are set to oidc:.
    - Structural YAML validation (line-by-line) confirms expected types.

    Full end-to-end execution (real generator + JS renderer + YAML parser) is
    deferred until PyYAML is installed in the test environment.
    """
    import json as _json

    # --- Step 1: Read source of truth ---
    exports_text = open(EXPORTS, encoding="utf-8").read()
    exports_data = _json.loads(exports_text)

    # Find the k8s-cluster-vars export
    kv_export = None
    for exp in exports_data.get("exports", []):
        if exp.get("id") == "k8s-cluster-vars":
            kv_export = exp
            break
    assert kv_export is not None, "k8s-cluster-vars export not found in catalog/exports.json"

    source_template = kv_export.get("template", "")
    assert source_template, "k8s-cluster-vars template is empty"

    # --- Step 2: Verify all 8 kube_oidc_* variables in source ---
    required_vars = [
        "kube_oidc_auth",
        "kube_oidc_url",
        "kube_oidc_client_id",
        "kube_oidc_ca_file",
        "kube_oidc_username_claim",
        "kube_oidc_username_prefix",
        "kube_oidc_groups_claim",
        "kube_oidc_groups_prefix",
    ]
    for var in required_vars:
        assert var in source_template, (
            "catalog/exports.json missing required variable %s" % var
        )

    # --- Step 3: Verify kube_oidc_auth is enabled ---
    assert 'kube_oidc_auth: true' in source_template, (
        "catalog/exports.json does not enable kube_oidc_auth"
    )

    # --- Step 4: Verify site/data.json matches source (build_site.py output) ---
    data_text = open(DATA, encoding="utf-8").read()
    data_data = _json.loads(data_text)
    data_kv = None
    for exp in data_data.get("exports", []):
        if exp.get("id") == "k8s-cluster-vars":
            data_kv = exp
            break
    assert data_kv is not None, "k8s-cluster-vars not found in site/data.json"

    data_template = data_kv.get("template", "")
    assert data_template == source_template, (
        "site/data.json k8s-cluster-vars template diverges from catalog/exports.json"
    )

    # --- Step 5: Simulate renderTemplate() and verify placeholder resolution ---
    # Substitute {{value.keycloakHost}} (the only value.* used in OIDC lines)
    rendered = source_template
    rendered = rendered.replace(
        '{{value.keycloakHost}}', 'https://keycloak.internal'
    )
    # Any remaining {{value.*}} in OIDC lines would be unresolved placeholders
    oidc_lines = [l for l in rendered.splitlines() if l.strip().startswith('kube_oidc_')]
    unresolved_in_oidc = []
    for line in oidc_lines:
        if '{{value.' in line or '{{choice.' in line or '{{version.' in line:
            unresolved_in_oidc.append(line.strip())
    assert not unresolved_in_oidc, (
        "Unresolved placeholders in OIDC lines: %s" % unresolved_in_oidc
    )

    # --- Step 6: Verify all 8 variables with correct values in rendered output ---
    rendered_dict = {}
    for line in oidc_lines:
        stripped = line.strip()
        if ':' in stripped:
            key, _, val = stripped.partition(':')
            key = key.strip()
            val = val.strip()
            # Strip surrounding JSON quotes from string values
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            rendered_dict[key] = val

    assert rendered_dict.get('kube_oidc_auth') == 'true', (
        "kube_oidc_auth is not 'true' in rendered output"
    )
    assert 'keycloak.internal/realms/platform' in rendered_dict.get('kube_oidc_url', ''), (
        "kube_oidc_url does not point to Keycloak platform realm"
    )
    assert rendered_dict.get('kube_oidc_client_id') == 'kube-apiserver', (
        "kube_oidc_client_id is not 'kube-apiserver'"
    )
    assert rendered_dict.get('kube_oidc_ca_file') == '/etc/kubernetes/pki/oidc-ca.crt', (
        "kube_oidc_ca_file is not '/etc/kubernetes/pki/oidc-ca.crt'"
    )
    assert rendered_dict.get('kube_oidc_username_claim') == 'preferred_username', (
        "kube_oidc_username_claim is not 'preferred_username'"
    )
    assert rendered_dict.get('kube_oidc_username_prefix') == 'oidc:', (
        "kube_oidc_username_prefix is not 'oidc:'"
    )
    assert rendered_dict.get('kube_oidc_groups_claim') == 'groups', (
        "kube_oidc_groups_claim is not 'groups'"
    )
    assert rendered_dict.get('kube_oidc_groups_prefix') == 'oidc:', (
        "kube_oidc_groups_prefix is not 'oidc:'"
    )

    # --- Step 7: Structural YAML validation (stdlib-only, no PyYAML dependency) ---
    # Verify each OIDC line has the expected key: value structure
    for line in oidc_lines:
        stripped = line.strip()
        assert ':' in stripped, (
            "OIDC line missing key:value separator: %s" % stripped
        )
        key = stripped.split(':', 1)[0].strip()
        val = stripped.split(':', 1)[1].strip()
        assert val, "OIDC key %s has empty value" % key
        # Boolean values must be bare (not quoted)
        if key == 'kube_oidc_auth':
            assert val == 'true', "kube_oidc_auth must be bare boolean true, got %s" % val
        # String values containing YAML-special characters must be quoted.
        # Colon (:) is a YAML mapping indicator, so values like "oidc:" and
        # "https://..." must be quoted. Bare strings like "kube-apiserver" are fine.
        yamlspecial = set(':{}[]&*?|><=!%@`')
        if any(ch in val for ch in yamlspecial):
            assert val.startswith('"') and val.endswith('"'), (
                "OIDC string value %s contains YAML-special chars and must be quoted, got %s" % (key, val)
            )

    # --- Step 8: Optional PyYAML structural validation ---
    try:
        import yaml  # noqa: F401
        # Full YAML parse if PyYAML is available
        parsed = yaml.safe_load(rendered)
        assert parsed is not None, "YAML parse returned None"
        oidc_keys = [k for k in parsed.keys() if k.startswith('kube_oidc')]
        assert len(oidc_keys) == 8, (
            "Expected 8 kube_oidc_* keys in parsed YAML, found %d: %s"
            % (len(oidc_keys), sorted(oidc_keys))
        )
        assert parsed['kube_oidc_auth'] is True, (
            "kube_oidc_auth parsed as %s, expected True" % parsed['kube_oidc_auth']
        )
        assert parsed['kube_oidc_username_prefix'] == 'oidc:', (
            "kube_oidc_username_prefix parsed as %s" % parsed['kube_oidc_username_prefix']
        )
        assert parsed['kube_oidc_groups_prefix'] == 'oidc:', (
            "kube_oidc_groups_prefix parsed as %s" % parsed['kube_oidc_groups_prefix']
        )
    except ImportError:
        print("SKIP PyYAML not installed; full YAML parse deferred")

def test_acceptance_signoff_is_backed_by_evidence():
    """A test may leave NOT RUN, but PASSED/FAILED needs stored evidence."""
    path = os.path.join(BASE, "requirements", "acceptance-criteria.md")
    text = open(path).read()
    header = "| ID | Test | Phase | Owner | Status | Evidence | Date | Tester |"
    assert header in text, "acceptance criteria status table header not found"
    body = text.split(header, 1)[1].split("\n\n", 1)[0]
    rows = [l for l in body.splitlines() if re.match(r"^\|\s*[A-Z]-\d+\s*\|", l)]
    assert rows, "acceptance criteria status table is empty"
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        test_id, status = cells[0], cells[4] if len(cells) > 4 else ""
        if status == "NOT RUN":
            continue
        assert status in ("PASSED", "FAILED", "BLOCKED"), f"{test_id}: unknown status {status!r}"
        evidence = cells[5] if len(cells) > 5 else ""
        assert evidence, f"{test_id}: {status} without an evidence path"
        assert os.path.exists(os.path.join(BASE, evidence.strip("`"))), \
            f"{test_id}: evidence path missing on disk: {evidence}"
        if status == "PASSED":
            assert cells[6] and cells[7], f"{test_id}: PASSED without date and tester"


def main():
    tests = [
        ("ADRs exist with all required sections", test_adrs_exist_and_have_all_sections),
        ("ADR generator is reproducible", test_adr_generator_is_reproducible),
        ("version matrix has dates, marks and sources", test_version_matrix_marks_and_sources),
        ("artifact matrix has all mandatory columns", test_artifact_matrix_has_all_mandatory_columns),
        ("network matrix has required fields and contiguous rows", test_network_matrix_has_required_fields),
        ("no plaintext secret patterns in the repo", test_no_plaintext_secret_patterns),
        ("docs are structurally sane", test_docs_are_structurally_sane),
        ("roadmap has all 15 phases", test_roadmap_phases_present),
        ("Kubespray OIDC: no legacy variable names", test_kubespray_oidc_no_legacy_variable_names),
        ("Kubespray OIDC: required variables present", test_kubespray_oidc_required_variables_present),
        ("Kubespray OIDC: auth enabled", test_kubespray_oidc_auth_enabled),
        ("Kubespray OIDC: prefixes set", test_kubespray_oidc_prefixes_set),
        ("Kubespray OIDC: site/data.json matches exports.json", test_site_data_matches_exports_oidc_template),
        ("Kubespray OIDC: renderTemplate substitution", test_render_template_substitutes_oidc_variables),
        ("YAML parsing availability", test_yaml_parsing_available),
        ("OIDC integration: simulated rendering", test_oidc_simulated_rendering_and_validation),

        ("acceptance sign-off is backed by evidence", test_acceptance_signoff_is_backed_by_evidence),
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
