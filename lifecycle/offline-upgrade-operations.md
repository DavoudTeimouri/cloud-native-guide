# Section 13: Offline and Restricted-Network Upgrade Operations

*Illustrative only — not production-committed configurations. No live system is upgraded from this document. All examples are version-dependent and labeled as such.*

## 13.1 Integration with two-tier repository/registry architecture

Offline upgrades use the two-tier repository/registry architecture established in TASK 004-P11.2:

- **External Upstream** — acquires approved artifacts from public sources (OS repos, container registries, Helm charts).
- **Internal Repository/Registry Manager** — provides Proxy/cached repos (Nexus) and hosted OCI registry (Harbor) reachable by internal nodes via stable endpoints (`nexus.internal`, `harbor.internal`).

No internal node requires direct public Internet access to retrieve approved artifacts during an upgrade.

## 13.2 External upstream acquisition

Before an offline upgrade:

1. Define the artifact allowlist (exact OS package versions, container image digests, Helm chart versions).
2. External Upstream host syncs selected artifacts from approved public sources (validate checksums and signatures where available — see `operations/registry-identity-secrets-recovery.md` Section 7).
3. Record sync status and audit events.

## 13.3 Controlled artifact synchronization

Transfer approved artifacts from External Upstream to the internal environment through the controlled process:

- OS packages (RPM/DEB): `curl --upload-file` to Nexus or internal repo sync tool.
- Container images: `skopeo copy` from public registry to internal Harbor.
- Helm charts: `helm pull` then `helm push` to internal chart repo.
- OCI artifacts: verify digest-based references (`@sha256:<digest>`).

Enforce artifact allowlists at the transfer step — only allowlisted versions/names are transferred.

## 13.4 Internal Nexus and Harbor availability

Before starting the upgrade window, verify internal services are reachable:

```bash
# Illustrative — verify internal repo and registry
curl -I https://nexus.internal/service/rest/v1/status
# Expected: 200 OK

curl -k -H "Authorization: Bearer <token>" https://harbor.internal/api/v2.0/projects
# Expected: JSON project list

crictl pull harbor.internal/oci/pause:3.9
# Expected: image pulled successfully
```

## 13.5 Image digest and signature verification

- Use digest-based OCI image references: `harbor.internal/oci/owner-repo@sha256:<digest>`.
- Verify image signatures (Cosign) before deploying upgraded workloads.
- `cosign verify --key <public-key> harbor.internal/oci/owner-repo@sha256:<digest>`.

## 13.6 Package repository snapshots

Snapshot internal DNF/YUM and APT repository metadata before the upgrade window:

- `repomd.xml` checksums for DNF/YUM repos.
- `Packages`/Release file checksums for APT repos.
- Verify checksums after sync (`sha256sum`).

## 13.7 Helm chart and OCI artifact availability

- Mirror required Helm charts to the internal chart repo before upgrade.
- `helm pull <chart> --version <version>` then `helm push` to internal repo.
- Verify OCI artifact availability via `helm search repo <chart> --versions`.

## 13.8 Ansible collection and Python dependency pinning

Kubespray upgrades require pinned Ansible and Python versions:

- Ansible: pinned per `version-compatibility-matrix.md` (>=2.19.0, <2.20.0 for release-2.32).
- Python: 3.11-3.13 on the control node.
- Pin Ansible collections: `ansible-galaxy collection install <collection>==<version>`.

Verify dependencies before starting the upgrade:

```bash
ansible --version
python3 --version
```

## 13.9 Version-specific artifacts

All artifacts must be version-specific and match `lifecycle/version-compatibility-matrix.conf`:

- OS packages: exact version, not `latest`.
- Container images: digest-pinned (`@sha256:<digest>`), not `latest`.
- Helm charts: exact chart version.
- Ansible collections: exact collection version.

## 13.10 Checksums and provenance

- Verify SHA-256 checksums of all downloaded artifacts before staging.
- Verify signatures (Cosign, GPG, apt-key) where available.
- Record sync status and audit events (artifact name+version, upstream URL, SHA-256, signature status, timestamp, result, target path).

## 13.11 Upgrade bundle preparation

Prepare an offline upgrade bundle containing:

- Pinned OS packages (RPM/DEB).
- Digest-pinned container images.
- Pinned Helm charts.
- Pinned Ansible collections and Python dependencies.
- Checksum and signature verification results.

Store the bundle in the internal repository; verify it is complete before starting the upgrade window.

## 13.12 Air-gapped validation

In a lab/staging environment that mirrors production (no public Internet access):

1. Perform the full upgrade using only internal artifacts.
2. Verify all workloads come up and are reachable via stable endpoints.
3. Confirm CNI/CSI/container runtime compatibility.
4. Validate rollback procedures (see `lifecycle/rollback-and-recovery.md`).

This avoids discovering missing artifacts during an actual upgrade window.

## 13.13 Limitations

- No internal node may require direct public Internet access.
- Air-gapped validation must be performed before production upgrade windows.
- Missing artifacts discovered during the window require aborting and rescheduling.

---

*SND 004-P11.6 — Offline and Restricted-Network Upgrade Operations (illustrative)*
