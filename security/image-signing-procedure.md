# Image Signing Procedure

## A. Purpose and scope

Document the cosign key lifecycle, signing pipeline, and verification at deployment. Cross-references `security/image-provenance.md` §Image signing, `offline-artifacts/artifact-matrix.md`, and `compatibility/version-matrix.md`.

## B. cosign key generation

Generate a keypair offline and store the private key in a secrets manager. The public key is distributed to all verifiers.

```bash
# Generate ed25519 keypair (recommended for short keys, fast ops)
cosign key generate --key-type ed25519

# Output
# PUBLIC_KEY: cosign.pub   (share this)
# PRIVATE_KEY: cosign.key  (keep offline, encrypt, or store in SSM/Azure Key Vault/GCP Secret Manager)
```

**Never commit the private key to version control.** Use short-lived rotation and automate key rollover via CI pipeline parameters.

## C. signing pipeline

Sign images at build time as part of the CI/CD pipeline. The pipeline must have the private key available via a secrets manager (not checked in).

```yaml
# Example: GitHub Actions step — sign after build and push
- name: Sign image with cosign
  run: |
    cosign sign --key cosign.pub ${{ env.REGISTRY }}/${{ env.IMAGE }}:${{ env.TAG }}
```

**Pipeline requirements:**
- Private key fetched from secrets manager at runtime (AWS Secrets Manager, Azure Key Vault, or GCP Secret Manager)
- Key access logged and audited
- Signing step runs after container image push
- Soft fail disabled — pipeline stops on signing failure

## D. verification at deployment

Verify signatures before any deployment step. This is a gate — images without valid signatures are rejected.

```bash
# Verify image signature at deployment
cosign verify --key cosign.pub registry.internal/${{ env.IMAGE }}:${{ env.TAG }}

# Verify SBOM attachment
cosign verify sbom --key cosign.pub --sbom sbom.json registry.internal/${{ env.IMAGE }}:${{ env.TAG }}
```

**Deployment gate:** The CI pipeline must call `cosign verify` as a pre-deploy step. Failure blocks the entire deployment.

## E. Key rotation

Rotate cosign keys quarterly or after any suspected compromise. Old public keys remain in the verification registry until all workloads are updated.

```bash
# Generate new keypair
cosign key generate --key-type ed25519 --out keybundle.json

# Publish new public key to registry annotation
cosign sign --key keybundle.json registry.internal/image:tag

# Update deployment configs to reference new public key
# Deprecate old key after grace period
```

## F. Cross-references

- `security/image-provenance.md` §Image signing — provenance and SBOM details
- `offline-artifacts/artifact-matrix.md` — which images in the matrix are signed
- `compatibility/version-matrix.md` — version pins and signing requirements
- `offline-artifacts/signature-verification.md` — GPG and cosign verification patterns