# SBOM Generation Pipeline

## A. Purpose and scope

Document automated SBOM generation, storage, and vulnerability correlation for container images and filesystem artifacts. Cross-references `security/host-baseline.md` §Container security, `offline-artifacts/artifact-matrix.md`, `security/image-provenance.md`.

## B. Automated SBOM Creation

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

## C. Storage

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

## D. Vulnerability Correlation

### Trivy Scan Validation

```bash
# Verify trivy scan results are not empty (indicates DB fetch failure)
if [ ! -s staging/trivy-fs.json ]; then
    echo "Trivy scan produced no results - check DB availability"
    exit 1
fi
```

### SBOM-Vulnerability Linkage

```bash
# Associate SBOM with vulnerability report by timestamp and component hash
SBOM_HASH=$(sha256sum /opt/artifacts/sboms/app-name-20240115.json | cut -d' ' -f1)
VULN_REPORT=$(ls /opt/artifacts/vuln-reports/app-name-20240115.json)
jq -r --arg hash "$SBOM_HASH" '. vulnerabilities[] | select(.sbom_hash == $hash)' "$VULN_REPORT" > /tmp/correlated-vulns.json
```

### Upstream Consumption

```bash
# Make SBOM available to security tools
ln -s /opt/artifacts/sboms/app-name-20240115.json /opt/sbom-current.json

# Expose via internal API endpoint
# Configure Trivy to fetch SBOM from: SBOM_URL=https://nexus.internal/repository/sboms/
```

## E. Workflow Summary

1. **Create**: Run `syft` or `trivy` to generate SBOM JSON from staged artifacts or OCI images
2. **Verify**: Validate SBOM schema, checksum, and signature integrity
3. **Store**: Persist SBOM to internal artifact repository with immutable permissions
4. **Correlate**: Link SBOM components with vulnerability reports for downstream consumption
5. **Distribute**: Make SBOM available to security teams, compliance teams, and downstream consumers

## F. Cross-references

- `security/host-baseline.md` §Container security — Host CIS baseline
- `offline-artifacts/artifact-matrix.md` — Per-component SBOM version records
- `security/image-provenance.md` — Image signing and SBOM attachment
- `signature-verification.md` — GPG/Cosign verification procedures