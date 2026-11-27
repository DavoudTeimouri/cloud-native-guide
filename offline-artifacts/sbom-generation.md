# SBOM Generation

## Purpose

Generate Software Bill of Materials (SBOM) for container images and filesystem artifacts using Syft and Trivy. This procedure covers SBOM creation, verification, storage, and distribution for offline environments.

## SBOM Creation

### Syft SBOM Generation

```bash
# SBOM for directory of staged artifacts
syft dir:./staging -o cyclonedx-json > staging/SBOM.json

# SBOM for OCI image
syft oci://registry.internal/app:tag -o cyclonedx-json > staging/SBOM-image.json
```

### Trivy SBOM and Vulnerability Scan

```bash
# SBOM from Syft output combined with Trivy vulnerability scanning
trivy fs --scanners vuln --format json ./staging > staging/trivy-fs.json

# Trivy image scan with SBOM inclusion
trivy image --input ./staging/oci/owner-repo.tar --format json --sbs SBOM.json > staging/trivy-image.json
```

### SBOM Verification

```bash
# Validate SBOM JSON schema
python3 -c "
import json
with open('staging/SBOM.json') as f:
    sbom = json.load(f)
assert 'bom' in sbom or 'components' in sbom, 'Invalid SBOM structure'
print('SBOM schema validated')
"

# Cross-check SBOM components against known good list
syft dir:./staging -o cyclonedx-json | jq -r '.components[].name' > /tmp/sbom-components.txt
sort /tmp/sbom-components.txt -u > /tmp/sbom-components-sorted.txt
```

## Verification

### SBOM Integrity

```bash
# Checksum verification
sha256sum staging/SBOM.json > staging/SBOM.checksum
sha256sum -c staging/SBOM.checksum

# Cosign signature verification (if SBOM is signed)
cosign verify sbom --key cosign.pub --sbom staging/SBOM.json registry.internal/app:tag
```

### Trivy Scan Validation

```bash
# Verify trivy scan results are not empty (indicates DB fetch failure)
if [ ! -s staging/trivy-fs.json ]; then
    echo "Trivy scan produced no results - check DB availability"
    exit 1
fi
```

## Storage

### SBOM Artifact Storage

```bash
# Store SBOM in internal artifact repository
mv staging/SBOM.json /opt/artifacts/sboms/app-name-$(date +%Y%m%d).json

# Store Trivy vulnerability report
mv staging/trivy-fs.json /opt/artifacts/vuln-reports/app-name-$(date +%Y%m%d).json

# Keep SBOM alongside related artifacts
cp staging/SBOM.json /opt/artifacts/staging-archives/
```

### Repository Layout

```
/opt/artifacts/
├── sboms/
│   ├── app-name-20240115.json
│   └── app-name-20240122.json
├── vuln-reports/
│   ├── app-name-20240115.json
│   └── app-name-20240122.json
└── staging-archives/
    └── (complete staging directories for rollback)
```

### Immutable Storage

```bash
# Write-once, reference-only after verification
chmod 444 /opt/artifacts/sboms/app-name-*.json
chmod 444 /opt/artifacts/vuln-reports/app-name-*.json
```

## Distribution

### Internal Distribution

```bash
# Publish SBOM to internal artifact registry
curl --upload-file /opt/artifacts/sboms/app-name-20240115.json \
    https://nexus.internal/repository/sboms/app-name-20240115.json

# Distribute via artifact matrix entry
# See offline-artifacts/artifact-matrix.md for per-component SBOM records
```

### Consumer Access

```bash
# Make SBOM available to security tools
ln -s /opt/artifacts/sboms/app-name-20240115.json /opt/sbom-current.json

# Expose via internal API endpoint
# Configure Trivy to fetch SBOM from: SBOM_URL=https://nexus.internal/repository/sboms/
```

### Downstream Sharing

```bash
# Package SBOM for external compliance reporting
cp /opt/artifacts/sboms/app-name-20240115.json /tmp/sbom-for-audit.json

# Generate SPDX from CycloneDX
jq -r '.components[] | {ref: .ref, name: .name, type: .type}' \
    /opt/artifacts/sboms/app-name-20240115.json > /tmp/sbom-spdx.json
```

## Workflow Summary

1. **Create**: Run `syft` or `trivy` to generate SBOM JSON from staged artifacts or OCI images
2. **Verify**: Validate SBOM schema, checksum, and signature integrity
3. **Store**: Persist SBOM to internal artifact repository with immutable permissions
4. **Distribute**: Make SBOM available to security tools, compliance teams, and downstream consumers

## Related Artifacts

- `offline-artifacts/artifact-matrix.md` — Per-component SBOM version records
- `signature-verification.md` — GPG/Cosign verification procedures
- `offline-artifact-architecture.md` — Repository and registry responsibilities
