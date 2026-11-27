# Kubespray Version Contradiction — Findings

**Status**: READ-ONLY — findings document. Do not modify `offline-upgrade-test.md` or `version-matrix.md`.

## Contradiction

The offline upgrade test script references two incompatible Kubespray versions that fall below the platform's supported floor:

| File | Line | Referenced Version | Status |
|------|------|-------------------|--------|
| `docs/offline-artifacts/offline-upgrade-test.md` | 101 | `kubespray_version=v2.27.0` | **UNSUPPORTED** — below 2.28 floor |
| `docs/offline-artifacts/offline-upgrade-test.md` | 191 | `kubespray_version=v2.26.0` | **UNSUPPORTED** — below 2.28 floor |

These appear in different test phases:

- **Line 101** — Test 2, step 1: the online Kubespray offline upgrade playbook execution uses `kubespray_version=v2.27.0`.
- **Line 191** — Test 4, step 2: the rollback validation failure scenario uses `kubespray_version=v2.26.0` to simulate reverting to an older Kubespray release.

## Supported Versions (per `compatibility/version-matrix.md`)

The version matrix defines five parallel Kubespray release lines, all supported:

| Release | Kubernetes (default) | Status |
|---------|----------------------|--------|
| `release-2.28` | 1.32.13 | Supported (oldest) |
| `release-2.29` | 1.33.10 | Supported |
| `release-2.30` | 1.34.12 | Supported |
| `release-2.31` | 1.35.9 | Supported |
| `release-2.32` | 1.36.5 | **Supported (default)** |

- **Pinned version**: Kubespray v2.32.0 (line 19 of `version-matrix.md`), image `quay.io/kubespray/kubespray:v2.32.0`
- **Minimum Kubernetes**: v1.34.0 (line 21)
- **Supported set**: release-2.28 through release-2.32 inclusive (lines 216-220)
- **Floor**: v2.28 — versions v2.26.0 and v2.27.0 are **below the supported floor**

## Risk Assessment

Using Kubespray versions v2.26.0 or v2.27.0 outside the supported matrix carries the following risks:

1. **Component incompatibility** — Ansible, Python, containerd, Cilium, and other platform components are pinned to the release-2.32 matrix. unsupported Kubespray versions may not be compatible with these pinned versions.

2. **Missing security fixes** — Kubespray releases between v2.28 and v2.32 include cumulative bug fixes and security patches not present in v2.26.0/v2.27.0.

3. **Undefined upgrade behavior** — The offline upgrade playbook and rollback procedures have been tested against the supported release set. Using unsupported versions may produce unpredictable results, failed upgrades, or unsuccessful rollbacks.

4. **Policy violation** — The platform's version pinning policy (line 273-276 of `version-matrix.md`) requires production to use exact versions with no floating references. Deliberately using versions below the floor violates this policy.

5. **Cascade failures** — An unsupported Kubespray version may trigger failures in dependent components (CNI, storage, GitOps tools) that are themselves pinned to the supported matrix, compounding the risk.

## Resolution Options

The following options are presented for human decision and authorization. **No action is taken automatically**; the user must select one.

### Option A: Update test to v2.32.0
- **Action**: Modify `offline-upgrade-test.md` lines 101 and 191 to use `kubespray_version=v2.32.0` instead of v2.27.0 and v2.26.0.
- **Pros**: Aligns the test with the supported/default version; no changes to the version compatibility matrix; uses the currently pinned Kubespray image.
- **Cons**: Requires modifying `offline-upgrade-test.md` (the test asserts a specific version; changing it may affect test semantics for the air-gapped upgrade path).
- **Impact**: Low — test remains within the supported matrix.

### Option B: Extend support matrix to include 2.26-2.27
- **Action**: Add Kubespray release branches `release-2.26` and `release-2.27` (or individual version pins) to `compatibility/version-matrix.md`, and document their supported component sets.
- **Pros**: Formalizes support for the older versions referenced in the test; provides a path to keep the test as-is.
- **Cons**: Requires verifying that all dependent components (Ansible, Python, containerd, Cilium, etc.) are compatible with v2.26.0 and v2.27.0; increases the maintenance surface of the version matrix; may require additional test infrastructure for older release branches.
- **Impact**: Medium-High — extends the matrix but does not guarantee tested compatibility.

### Option C: Keep blocked pending human decision
- **Action**: Leave both `offline-upgrade-test.md` entries as-is and block any upgrade execution that uses kubespray_version v2.26.0 or v2.27.0 until an explicit decision is authorized.
- **Pros**: Preserves the existing test unchanged; maintains the integrity of the supported version floor; no immediate changes to any files.
- **Cons**: The test cannot be executed in its current form until a decision is made; creates a blocking state for offline upgrade validation.
- **Impact**: Low — test is blocked but no technical debt is added.

---

## Decision Required

Please authorize one of the three options above. Once authorized, the appropriate follow-up action will be taken:

- **If Option A**: The test will be updated to `kubespray_version=v2.32.0` and the upgrade playbook can proceed using the default/pinned Kubespray release.
- **If Option B**: The version matrix will be extended to include release-2.26 and release-2.27, with verified component compatibility, and the test entries will remain unchanged.
- **If Option C**: The test will remain blocked; a separate decision process will determine whether to update the test or the matrix at a later date.

---

*Findings generated from `offline-upgrade-test.md` lines 101 and 191 versus `compatibility/version-matrix.md` lines 19 and 216-220. Check date: 2026-10-26.*
