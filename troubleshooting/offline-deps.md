# Offline Dependency Resolution Troubleshooting

## Symptoms

- `skopeo copy` fails with "manifest unknown" or "unauthorized"
- `apt` or `dnf` cannot find packages in offline repository
- Helm chart installation fails: "chart not found"
- Docker/containerd image pull fails in air-gapped environment
- Python pip cannot install from offline index

## Likely causes

- Image not mirrored to internal registry
- Repository metadata out of sync
- Missing artifact in offline-artifacts/artifact-matrix.md
- Registry authentication not configured
- Network policy blocking registry access

## Diagnostic commands

```bash
# Check if image exists in registry
skopeo inspect docker://registry.internal/platform/<image>:<tag>

# Check artifact matrix
cat offline-artifacts/artifact-matrix.md | grep <artifact-name>

# Check containerd images
crictl inspecti <image-digest>
ctr -n k8s.io images list | grep <image>

# Check apt/dnf repositories
apt-cache policy <package>
dnf repoinfo <repo>

# Check Helm charts
helm search repo <chart-name>

# Test registry authentication
skopeo inspect --creds <user>:<pass> docker://registry.internal/platform/<image>:<tag>
```

## Expected healthy state

- All required images present in internal registry
- `skopeo inspect` succeeds for all pinned images
- Artifact matrix lists all dependencies with versions
- Repository metadata current (repodata/repomd.xml present)
- Helm charts indexed and installable

## Remediation

- Mirror missing images per offline-artifacts/artifact-matrix.md
- Sync repository metadata: `reposync` or `apt-mirror`
- Update artifact matrix with new dependency versions
- Configure registry authentication in containerd (`hosts.toml`)
- Add network policy allowing registry access

## Risks

- Mirroring large images consumes significant storage
- Out-of-sync repository metadata can cause dependency resolution failures
- Wrong registry credentials can cause widespread pull failures

## Verification

```bash
skopeo inspect docker://registry.internal/platform/<image>:<tag>
ctr -n k8s.io images list | grep <image>
cat offline-artifacts/artifact-matrix.md | grep <artifact-name>```
