# Signature Verification

## A. Purpose and scope

Document signature and checksum verification: GPG signatures, SBOM verification, cosign verification, artifact integrity.

Cross-references `offline-artifacts/artifact-matrix.md`, `security/image-provenance.md`, `security/secret-delivery.md`.

## B. GPG signature verification

OS packages and software artifacts are verified with GPG signatures:

```bash
# Import signing key
gpg --import <vendor>-signing-key.asc

# Verify package signature
gpg --verify package.rpm.asc package.rpm

# Verify checksum
sha256sum -c package.sha256
```

## C. Cosign verification

Container images are verified with Cosign:

```bash
# Verify image signature
cosign verify --key cosign.pub registry.internal/:<tag>

# Verify SBOM
cosign verify sbom --key cosign.pub --sbom sbom.json registry.internal/:<tag>
```

## D. Artifact integrity

All artifacts in the artifact matrix must have verified integrity:

| Artifact type | Verification method | Frequency |
|---------------|-------------------|-----------|
| Container images | Cosign signature + SBOM | Every pull |
| OS packages | GPG signature + SHA256 | Every install |
| Helm charts | Cosign signature | Every install |
| Kubespray release | GPG signature + SHA256 | Every deploy |
| OS ISOs | GPG signature + SHA256 | Every download |

## E. Verification failure handling

If verification fails:

1. Do not deploy/install the artifact
2. Quarantine the artifact
3. Notify the security team
4. Document the failure
5. Replace with verified artifact from mirror

## F. Cross-references

- `offline-artifacts/artifact-matrix.md` — Artifact matrix with versions
- `security/image-provenance.md` — Image signing
- `security/secret-delivery.md` — Secret delivery
- `compatibility/version-matrix.md` — Version pins
