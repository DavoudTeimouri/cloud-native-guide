# Section 8 — Supply-Chain Security

*Illustrative only — not production-committed configurations. Marked as such where indicated. No supply-chain controls are applied to a live cluster from this document.*

---\n\n## 8.1 Supply-Chain Security Overview

This section documents the controls and procedures for ensuring the integrity and provenance of images, artifacts, and dependencies across the Kubernetes platform. Supply-chain security is a layered concern — no single mechanism replaces the others, and all controls follow a build-verify-deploy pattern.

**Core principle**: Every image and artifact must be signed, scanned, and verified before it is permitted for deployment. Scanning and signing are complementary — a clean scan does not guarantee a safe runtime image, and a signed image does not guarantee freedom from vulnerabilities.

---\n\n## 8.2 Image Signing with Cosign

### Sign an Image

```bash
# Sign the image using a Cosign key
cosign sign --key cosign.key myimage@sha256:abc123def456example...

# Expected: signature attached to the image digest in the registry
# The public key (cosign.pub) can be distributed for verification
```

### Verify an Image Signature

```bash
# Verify the image carries a valid Cosign signature
cosign verify --key cosign.pub myimage@sha256:abc123def456example...

# Expected: key fingerprint printed; verification passes

# Verify fails for unsigned image
cosign verify --key cosign.pub myimage@sha256:abc123def456example... 2>&1
# Expected: ERROR: no signature found; exit code non-zero
```

### Cosign in CI Pipeline

```yaml
# GitHub Actions example — sign and verify in the same pipeline
- name: Sign image with Cosign
  run: |
    cosign sign --key cosign.key myimage@sha256:abc123def456example...

- name: Verify image signature
  run: |
    cosign verify --key cosign.pub myimage@sha256:abc123def456example...
  # Pipeline exits non-zero if verification fails
```

---\n\n## 8.3 Image Scanning with Trivy

### Scan an Image for Vulnerabilities

```bash
# Scan by digest (recommended)
trivy image --severity CRITICAL,HIGH myimage@sha256:abc123def456example...

# Expected: list of vulnerabilities by severity; exit code 0 if only low/negligible findings

# Gate promotion on critical/high findings
trivy image --severity CRITICAL,HIGH --exit-code 1 myimage@sha256:abc123def456example...
# Expected: pipeline exits non-zero if CRITICAL findings exist
```

### Scan a Chart or Helm Release

```bash
# Scan a Helm chart
trivy fs --severity CRITICAL,HIGH ./mychart/

# Expected: same vulnerability report format as image scanning
```

---\n\n## 8.4 Kyverno Image Provenance Verification

### Policy That Requires Image Digests

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-digest
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-digest
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment"]
      validate:
        message: "Images must be pinned by digest and come from harbor.internal"
        pattern:
          spec:
            containers:
              - image: "harbor.internal/*@sha256:*"
```

### Policy That Verifies Image Registry Source

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: allow-trusted-registries
spec:
  validationFailureAction: Enforce
  rules:
    - name: allow-only-trusted-registries
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment"]
      validate:
        message: "Image must come from a trusted registry"
        pattern:
          spec:
            containers:
              - image: "registry.internal/*"
              # Images from external registries are rejected
```

---\n\n## 8.5 SBOM and Provenance

### Generate SBOM during Build

```bash
# Generate an SBOM in SPDX format
cyclonedx-bom -o sbom.spdx myimage@sha256:abc123def456example...

# Or in CycloneDX format
cyclonedx-bom -o sbom.json myimage@sha256:abc123def456example...
```

### Sign the SBOM alongside the Image

```bash
# Sign the SBOM with Cosign
cosign sign --key cosign.key sbom.spdx

# Verify the signed SBOM
cosign verify --key cosign.pub sbom.spdx
```

---\n\n## 8.6 Registry Allowlisting

### Policy That Allows Only Approved Registries

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: registry-allowlist
spec:
  validationFailureAction: Enforce
  rules:
    - name: allow-only-approved-registries
      match:
        any:
          - resources:
              kinds: ["Pod", "Deployment"]
      validate:
        message: "Image must come from an approved registry"
        pattern:
          spec:
            containers:
              - image: "registry.internal/*@sha256:*"
              # external registries are rejected unless explicitly exempted
```

### Exempt Specific Workloads

```yaml
# For CI/CD canary deployments that use external registries:
parameters:
  exemptNamespaces: ["kube-system", "gatekeeper-system", "kube-public"]
  # Or use namespace-level annotations: kyverno.io/exceptions
```

---\n\n## 8.7 Supply-Chain Validation Checklist

- [ ] Every image signed with Cosign before promotion
- [ ] Every image scanned with Trivy CRITICAL/HIGH before promotion
- [ ] CI pipeline exits non-zero on CRITICAL findings or failed Cosign verification
- [ ] Kyverno policy enforces digest pinning (`@sha256:*`) for all images
- [ ] Kyverno policy restricts images to approved registries only
- [ ] SBOM generated and signed for each image build
- [ ] Image digest pinned — no mutable `:latest` or `:tag` references in deployment specs
- [ ] Image provenance (signature + SBOM) verified before deployment
- [ ] Registry allowlist enforced at admission time
- [ ] No images from untrusted registries admitted without documented exception

---\n\n## 8.8 Supply-Chain Troubleshooting

| Symptom | Expected Cause | Corrective Action |
|---|---|---|
| `cosign verify` fails — no signature found | Image was not signed during build | Sign the image in the CI pipeline; verify the signing key is available |
| `trivy image` finds CRITICAL findings | Known vulnerability in base image | Update base image to patched version; rebuild and re-sign |
| Pipeline fails on Cosign verification but image is signed | Key mismatch between sign and verify | Ensure the same key pair is used; distribute the public key to all verifiers |
| Trivy scan passes but image has new CVE between scan and deployment | New vulnerability disclosed after scan | Integrate Trivy into every deployment pipeline; consider runtime detection (Falco) |
| Image admitted despite `:latest` tag | Admission policy does not enforce digest pinning | Update Kyverno/Gatekeeper policy to reject non-digest images; transition to `@sha256:` pins |
| SBOM generation fails | SBOM tool not available in CI environment | Add SBOM generation step to the build pipeline; use `cyclonedx-bom` or `spdx-tools` |

---\n--- 

*End of Section 8 — Supply-Chain Security*