# 10 · Air-Gapped Upgrade

## Purpose and scope
Upgrade procedures for fully disconnected environments.

## Steps
1. Stage new artifacts on connected staging host
2. Transfer artifacts to air-gapped environment via transfer station
3. Import artifacts to internal Harbor/Nexus/GitLab
4. Upgrade components using internal mirrors only
5. Verify no public internet dependency

## Implementation
```bash
# On connected staging host
skopeo copy docker://<image> dir:/tmp/staging/<image>
helm pull <chart> --version <new-version>
# Transfer /tmp/staging to air-gapped environment via physical media

# On air-gapped environment
skopeo copy dir:/tmp/staging/<image> docker://harbor.internal/<image>
helm upgrade <release> <chart> --version <new-version> -n <namespace>
```

## Validation
- All artifacts available internally
- No public internet access during upgrade
- Components healthy after upgrade

## Related
- [01 · Overview (1.4 Air-Gapped & Disconnected Environments)](../01-overview-and-architecture/1.5-deployment-environments.md)
- [03 · Repository & Registry Management (3.4 Air-Gapped)](../03-repository-registry/3.4-repository-catalog.md)
- [Shared version & compatibility matrix](../shared/matrices/version-matrix/index.md)
