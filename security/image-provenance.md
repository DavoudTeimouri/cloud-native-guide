# Image Provenance

## A. Purpose and scope

Document image provenance: image signing, cosign verification, SBOM, vulnerability scanning, Trivy integration.

Cross-references `security/host-baseline.md` §Container security, `offline-artifacts/artifact-matrix.md`, `security/secret-delivery.md`.

## B. Image signing with Cosign

Images are signed with Cosign at build time and verified at deployment:

```bash
# Sign an image
cosign sign --key cosign.key registry.internal/<image>:<tag>

# Verify a signature
cosign verify --key cosign.pub registry.internal/<image>:<tag>

# Verify SBOM attachment
cosign verify sbom --key cosign.pub registry.internal/<image>:<tag>
```

## C. SBOM generation

Every container image in the artifact matrix must have an SBOM:

```bash
# Generate SBOM with Trivy
trivy image --format spdx --output sbom.spdx.json registry.internal/<image>:<tag>

# Verify SBOM
cosign verify sbom --key cosign.pub --sbom sbom.spdx.json registry.internal/<image>:<tag>
```

## D. Vulnerability scanning

Images are scanned before deployment:

```bash
# Scan image
trivy image --severity HIGH,CRITICAL registry.internal/<image>:<tag>

# Scan running container
trivy config container registry.internal/<image>:<tag>
```

Critical/high vulnerabilities block deployment until fixed or accepted with a documented exception.

## E. Image pull policy

All images use `IfNotPresent` or `Never` in offline mode. `Latest` tag is never used.

## F. Cross-references

- `security/host-baseline.md` §Container security — Host CIS baseline
- `offline-artifacts/artifact-matrix.md` — Image matrix
- `security/secret-delivery.md` — Secret delivery to workloads
- `compatibility/version-matrix.md` — Version pins
