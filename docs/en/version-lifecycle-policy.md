# Version and Lifecycle Policy

This document defines how component versions are managed, pinned, and tracked throughout their lifecycle in the Cloud-Native Stack.

## Version Pinning Principles

1. **Exact Versions Only** — Production uses exact versions. No `latest` tags, no floating Git references, no unpinned Helm charts.
2. **Digest-Based Deployment** — Container images deployed by digest wherever the platform supports it.
3. **Single Source of Truth** — Every pin has a row in `compatibility/version-matrix.md` with a source URL and check date.
4. **Atomic Version Bumps** — A version bump is a single MR that updates the version matrix, the artifact matrix, and the component guide together.
5. **Compatibility First** — Upgrading a component to a version not in the version matrix requires passing the compatibility checks in the "Component-to-component compatibility constraints" table first.

## Version Categories

| Category | Description | Example |
|---|---|---|
| **VERIFIED** | Read from official source on check date; source linked | `v1.21.2` |
| **PINNED** | Exact version this platform deploys (chosen from VERIFIED set) | `v1.21.2` |
| **UNVERIFIED** | Not confirmed. Verification procedure stated; must not be used in deploy until confirmed | `v1.22.0` |
| **CANDIDATE** | Evaluated for future adoption, not yet pinned | `v0.162.0` |
| **RETIRED** | No longer supported; do not use | `v1.15.3` |

## Component Version Tracking

### Kubernetes & Cluster Lifecycle
- **Kubespray** is the primary Kubernetes deployment tool
- Five Kubespray releases supported in parallel (ADR-0026)
- Each release has its own pinned component versions
- Kubernetes version must be within Kubespray release's supported range
- Chart versions tracked separately from application versions

### Helm Charts
- Chart version is the pin, not the application version
- Application version tracked separately in version matrix
- Example: `cert-manager` chart `v1.21.2` (app `v1.21.2`), Vault chart `0.34.1` (app `2.0.4`)

### Container Images
- Deployed by digest wherever platform supports it
- Image digests recorded in `offline-artifacts/artifact-matrix.md`
- Image mirrors in `registry.internal:5000/...`

### Kubernetes Components
- CNI (Cilium), CSI (Rook-Ceph), Ingress (NGINX Gateway Fabric)
- Each tracked with chart version and application version
- Kubespray-managed vs platform-managed clearly distinguished

## Version Matrix Maintenance

### Authority
- **Source of truth**: `compatibility/version-matrix.md`
- **Check date**: Recorded at top of version matrix (e.g., "Check date: 2026-10-17")
- **Refresh procedure**: Run `scripts/fetch_versions.py`, `scripts/helm_chart_versions.py`, `scripts/github_latest_releases.py` in connected environment

### Update Process
1. Run fetch scripts in connected environment
2. Diff against current version matrix
3. Verify compatibility constraints
4. Open MR with:
   - Updated version matrix
   - Updated artifact matrix (`offline-artifacts/artifact-matrix.md`)
   - Updated component guide(s)
   - Check date in commit message

## Component-to-Component Compatibility

Critical constraints that must hold:

| Constraint | Rule | Verification |
|---|---|---|
| Kubespray → Kubernetes | Target K8s in Kubespray release's supported range | Kubespray release README |
| Kubespray → Ansible | ansible-core version per release | Kubespray `docs/ansible/ansible.md` |
| Kubespray → containerd | Use containerd version Kubespray ships | Kubespray release README |
| Kubespray → CNI | Cilium/Calico as shipped by release | Kubespray release |
| Rook → Ceph | `cephVersion.image` must match Rook release | Rook release notes |
| Vault chart → Vault binary | Chart's appVersion defines Vault binary | `helm show chart vault` |
| Argo CD chart → Argo CD image | Chart's appVersion defines image | `helm show chart argo-cd` |
| GPU Operator → driver | Operator's `driver.version` matches toolkit | GPU Operator release notes |
| MIG → driver | H100/H200 need driver ≥ 450.80.02 on CUDA 12 | NVIDIA MIG User Guide |
| vLLM → driver/CUDA | vLLM on CUDA version supported by driver | vLLM install docs |

## Version Lifecycle States

| State | Definition | Action |
|---|---|---|
| **Supported** | Actively tested, security patches available | Normal deployment |
| **Maintenance** | Only critical/security fixes | Plan migration |
| **Deprecated** | No longer recommended for new deployments | Plan migration within 6 months |
| **Retired** | No support, no patches | Must migrate immediately |
| **End-of-Life** | Upstream EOL | Must migrate immediately |

### Tracking EOL
- Tracked in `compatibility/version-matrix.md` "End-of-life and retirement watchlist"
- Review monthly during version refresh
- Plan migrations before EOL dates

## Helm Chart vs Application Version

| Component | Chart Version | App Version | Pin Type |
|---|---|---|---|
| cert-manager | v1.21.2 | v1.21.2 | Chart |
| Vault | 0.34.1 | 2.0.4 | Chart |
| Argo CD | 10.10.5 | v3.5.5 | Chart |
| Trivy Operator | 0.36.0 | v0.36.0 | Chart |
| OpenTelemetry Operator | v0.161.0 | v0.161.0 | Chart |

**Rule**: Chart version is the pin. Application version is informational but tracked for compatibility.

## Image Digests and Artifact Checksums

- Recorded in `offline-artifacts/artifact-matrix.md`
- Format: `sha256:<digest>`
- Verified during air-gap staging
- `skopeo inspect` used to verify digests

## Previous Versions Availability

- Previous supported versions remain in version matrix with status
- At least one previous version per component kept as fallback
- Deprecated versions marked but kept for reference
- Rollback procedures reference previous versions

## Upgrade Documentation

Each component upgrade documented in `lifecycle/upgrades/`:
- Upgrade path and prerequisites
- Step-by-step procedure
- Rollback procedure
- Breaking changes
- Migration notes
- Validation criteria

## Deprecated/Unsupported Version Identification

- Marked **RETIRED** or **DEPRECATED** in version matrix
- EOL dates tracked in "End-of-life and retirement watchlist"
- Migration path documented in component guide
- Not available for new deployments

## Version Refresh Procedure

```bash
# Run in connected environment
python3 scripts/fetch_versions.py
python3 scripts/helm_chart_versions.py
python3 scripts/github_latest_releases.py <owner/repo>
python3 scripts/kubespray_release_matrix.py release-2.28 release-2.29 release-2.30 release-2.31 release-2.32
python3 scripts/kubespray_ansible_matrix.py release-2.28 release-2.29 release-2.30 release-2.31 release-2.32

# Regenerate ADRs after editing generator
python3 scripts/gen_adrs.py

# Self-check
python3 tests/test_repo_tools.py
```

## Version Bump Checklist

- [ ] New version verified against official source
- [ ] Compatibility constraints verified
- [ ] Version matrix updated with new version and check date
- [ ] Artifact matrix updated with new image digests
- [ ] Component guide updated
- [ ] Acceptance criteria reviewed
- [ ] Tests updated if needed
- [ ] MR created with all changes together
- [ ] Check date recorded in commit message

## Enforcement

- CI validates version matrix format
- CI checks for unpinned versions in component guides
- CI verifies chart version vs app version consistency
- MR cannot merge without version matrix update for version changes

## Changelog

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-11-23 | 1.0 | Initial version lifecycle policy | Platform Team |