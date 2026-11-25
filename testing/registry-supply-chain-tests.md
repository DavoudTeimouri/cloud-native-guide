# Section 7: Registry/Supply-Chain Integration Tests

**Purpose**: Cross-component tests for end-to-end registry and supply-chain behavior from external upstream sources through internal repository managers, reverse proxies, to Kubernetes and CI consumers. All tests are designed against ephemeral/lab clusters only — no live or shared clusters are used.

> **Important**: Static YAML/schema checks are NOT proof of runtime functionality. A valid manifest may fail at runtime due to registry rate limits, TLS trust issues, network policies, or authentication configuration. Always validate against a live (ephemeral or staging) registry when runtime behavior is the goal.

---

## 7.1 External Upstream Repository Access

| Field | Details |
|---|---|
| **Test ID** | REG-001 |
| **Scope** | Retrieval of packages/artifacts from external upstream repositories (PyPI, Maven, npm, Docker hub) without authentication requirements |
| **Positive Test** | |
| **Preconditions** | Network egress is permitted; upstream repository is publicly reachable; no internal proxy or mirror configured |
| **Test Command** | `pip install <package-name> --target /tmp/test_pull` (or equivalent for other package managers) |
| **Expected Output** | Package downloads successfully; checksums match; no TLS errors |
| **Failure Condition** | DNS resolution fails; connection timed out; 404 Not Found; TLS certificate validation error |
| **Remediation** | Verify network policies allow egress to upstream; check DNS configuration; confirm upstream availability |
| **Evidence** | `pip` download output; `curl` diagnostic to upstream URL; `dig` resolution |
| **Automated** | Yes — scripted package download with checksum verification |
| **Manual** | Yes — `curl`/`wget` from control machine to upstream URL |

---

## 7.2 Internal Repository Manager (Nexus) — OS Package Retrieval

| Field | Details |
|---|---|
| **Test ID** | REG-002 |
| **Scope** | OS package retrieval from Nexus Repository Manager (yum/dnf, apt, conda) |
| **Positive Test** | |
| **Preconditions** | Nexus is running; repository is configured as a remote proxy for upstream OS packages; TLS CA trust is established on the client |
| **Test Command** | `yum install --disablestars <package-name>` (or `apt-get update && apt-get install <package-name>`) |
| **Expected Output** | Package resolves from Nexus proxy; download progress shown; GPG signature verification optional based on config |
| **Failure Condition** | 404 Not Found from Nexus; TLS handshake failure due to missing CA; proxy timeout; repository not enabled |
| **Remediation** | Verify Nexus repository configuration; check TLS CA trust chain on client; ensure repository is not disabled or archived |
| **Evidence** | `yum` or `apt` output; Nexus download logs; TLS error details if applicable |
| **Automated** | Yes — package manager CLI scripted with exit code assertion |
| **Manual** | Yes — manual `yum`/`apt` invocation with log capture |

---

## 7.3 Internal Repository Manager (Harbor) — Container Image Retrieval

| Field | Details |
|---|---|
| **Test ID** | REG-003 |
| **Scope** | Container image retrieval from Harbor registry with TLS and authentication |
| **Positive Test** | |
| **Preconditions** | Harbor is running; image is stored in a project/namespace; TLS certificate is trusted (CA added to client trust store); credentials are configured in `docker config` or `~/.docker/config.json` |
| **Test Command** | `docker pull harbor-registry.example.com/project/image:tag` |
| **Expected Output** | Image digest is pulled; TLS handshake succeeds; authentication succeeds (if image has digest tag or library protection) |
| **Failure Condition** | TLS certificate rejected (unknown CA); authentication failed (invalid credentials); image not found; 503 Service Unavailable |
| **Remediation** | Add Harbor CA to client trust store; verify `docker login` credentials; check project/namespace and image tag availability |
| **Evidence** | `docker pull` output; TLS error details; `docker login` status |
| **Automated** | Yes — `docker pull` scripted with exit code and digest capture |
| **Manual** | Yes — `docker pull` from CLI with visual inspection |

---

## 7.4 Helm Chart Retrieval via Internal Registry

| Field | Details |
|---|---|
| **Test ID** | REG-004 |
| **Scope** | Helm chart retrieval from internal registry (OCI layout or traditional chart repository) |
| **Positive Test** | |
| **Preconditions** | Registry is running; chart is indexed; TLS is configured and trusted; authentication is configured if the chart repository requires it |
| **Test Command** | `helm repo add my-registry harbor-registry.example.com/charts && helm repo update && helm search repo my-chart --repo harbor-registry.example.com/charts` |
| **Expected Output** | Chart is listed; chart metadata (appVersion, version) is displayed; `helm pull` succeeds |
| **Failure Condition** | Chart not found; index update fails; TLS error; authentication rejected |
| **Remediation** | Verify chart is pushed to correct project; check TLS trust; re-index the repository if using OCI layout |
| **Evidence** | `helm search` output; `helm pull` output; repository index JSON |
| **Automated** | Yes — `helm repo update` + `helm search` scripted |
| **Manual** | Yes — `helm repo add` + `helm search repo` from CLI |

---

## 7.5 TLS/CA Trust Validation

| Field | Details |
|---|---|
| **Test ID** | REG-005 |
| **Scope** | TLS certificate chain validation for registry connections (self-signed CAs, intermediate CAs, expired certificates) |
| **Positive Test** | Client trust store contains the correct CA; certificate is within validity period |
| **Negative Test (REG-005-NEG)** | |
| **Preconditions** | Same as positive; TLS CA is deliberately missing from the client trust store or the certificate is expired |
| **Test Command** | Attempt `docker pull` or `curl` to registry with untrusted TLS certificate |
| **Expected Output** | TLS handshake failure; certificate verification error; exit code non-zero |
| **Failure Condition** | Traffic passes despite invalid/trusted certificate — indicates trust store misconfiguration |
| **Remediation** | Add the correct CA to the client trust store; use `--insecure-registry` only for testing; regenerate certificates if expired |
| **Evidence** | TLS error output; `openssl s_client -connect registry:443` diagnostic |
| **Automated** | Yes — scripted pull with expect/assert on "certificate signed by unknown authority" |
| **Manual** | Yes — manual `openssl s_client` and `docker pull` |

---

## 7.6 Proxy + Hosted Repository Behavior

| Field | Details |
|---|---|
| **Test ID** | REG-006 |
| **Scope** | Behavior when an internal reverse proxy (e.g.,nginx, Envoy) sits between the consumer and the repository manager |
| **Positive Test** | |
| **Preconditions** | Reverse proxy is configured and running; proxy forwards registry requests to upstream Harbor/Nexus; TLS termination occurs at proxy |
| **Test Command** | `docker pull http://proxy-host:port/project/image:tag` (or package manager through proxy) |
| **Expected Output** | Request proxies successfully; TLS at proxy level; registry response returned; cache behavior honored |
| **Failure Condition** | 502 Bad Gateway; proxy timeout; proxy does not forward TLS passthrough; cached responses stale or missing |
| **Remediation** | Verify proxy configuration upstream/backend URLs; check TLS passthrough vs termination; clear proxy cache |
| **Evidence** | Proxy access logs; `docker pull` output; proxy status metrics |
| **Automated** | Yes — scripted proxy-mediated pull with exit code assertion |
| **Manual** | Yes — manual `curl` through proxy endpoint |

---

## 7.7 Large Image/Artifact Transfer

| Field | Details |
|---|---|
| **Test ID** | REG-007 |
| **Scope** | Transfer of large container images or artifacts ( > 1GB) through the registry pipeline |
| **Positive Test** | |
| **Preconditions** | Large image is stored in registry; sufficient network bandwidth; storage capacity on consumer side |
| **Test Command** | `docker pull harbor-registry.example.com/large-image:tag` |
| **Expected Output** | Image layers stream progressively; digest verification completes; pull finishes without timeout |
| **Failure Condition** | Transfer timeout; insufficient storage; proxy cannot handle large payload; registry returns 503/504 |
| **Remediation** | Increase proxy timeout settings; verify storage capacity; check network path MTU; optimize image layers |
| **Evidence** | `docker pull` output with layer progress; transfer duration metrics; digest at completion |
| **Automated** | Yes — scripted pull with duration and digest capture; assert exit code 0 |
| **Manual** | Yes — manual `docker pull` with timing capture |

---

## 7.8 Digest Verification

| Field | Details |
|---|---|
| **Test ID** | REG-008 |
| **Scope** | Verification that pulled artifact matches its declared digest (SHA256) |
| **Positive Test** | |
| **Preconditions** | Image/artifact has been pulled; digest is known from registry API or `docker images` output |
| **Test Command** | `docker pull harbor-registry/example/image:sha256:<digest>` and verify `docker images --no-trunc` matches |
| **Expected Output** | Digest in `docker images` output matches the sha256 reference; image is immutable after pull |
| **Negative Test (REG-008-NEG)** | |
| **Preconditions** | Same as positive; but the pulled image has a mismatched digest (e.g., tampered layer) |
| **Test Command** | Attempt `docker pull` with corrupted intermediate layer or wrong digest reference |
| **Expected Output** | Pull fails with digest mismatch error; image is not stored |
| **Failure Condition** | Mismatched digest accepted — indicates registry or storage corruption |
| **Remediation** | Re-pull from clean source; verify registry storage integrity; re-index if using OCI layout |
| **Evidence** | `docker images --no-trunc` output; digest comparison script output |
| **Automated** | Yes — pull with digest capture and assert match |
| **Manual** | Yes — manual digest comparison with `sha256sum` or equivalent |

---

## 7.9 Image Scanning

| Field | Details |
|---|---|
| **Test ID** | REG-009 |
| **Scope** | Container image scanning for vulnerabilities after retrieval |
| **Positive Test** | |
| **Preconditions** | Image has been pulled to the lab cluster; scanning tool (Trivy, Anchore, etc.) is available |
| **Test Command** | `trivy image harbor-registry.example.com/project/image:tag` |
| **Expected Output** | Scan report generated; vulnerabilities listed by severity; exit code reflects severity threshold |
| **Failure Condition** | Scan tool unavailable; network timeout contacting vulnerability DB; false positives not filtered |
| **Remediation** | Update scanning tool signatures; adjust severity thresholds; filter known false positives |
| **Evidence** | Trivy/Anchore JSON/HTML report; vulnerability list with severities |
| **Automated** | Yes — trivy CLI scripted with JSON output and severity filtering |
| **Manual** | Yes — manual trivy scan with report review |

---

## 7.10 Image Signing and Signature Verification

| Field | Details |
|---|---|
| **Test ID** | REG-010 |
| **Scope** | Cosign or Notary signature verification on container images |
| **Positive Test** | |
| **Preconditions** | Image is signed with Cosign; public key or signing key is available in the trust store; Cosign CLI is available |
| **Test Command** | `cosign verify --key https://rekor.example.com/v1/repositories/index/docker/artifacts/signatures harbor-registry.example.com/project/image:tag` |
| **Expected Output** | Signature verification passes; image digest matches verified signature; exit code 0 |
| **Negative Test (REG-010-NEG)** | |
| **Preconditions** | Same as positive; but the image is unsigned or the signature is invalid |
| **Test Command** | Attempt `cosign verify` on unsigned or tampered image |
| **Expected Output** | Verification fails; "invalid signature" or "no signature found" error; exit code non-zero |
| **Failure Condition** | Invalid signature accepted — indicates Cosign configuration or trust store issue |
| **Remediation** | Ensure image is signed before push; add correct public key to trust store; re-sign if key rotation occurred |
| **Evidence** | `cosign verify` output; signature metadata; rekor entry reference |
| **Automated** | Yes — cosign verify scripted with exit code assertion |
| **Manual** | Yes — manual `cosign verify` with output capture |

> **Note**: Scanning (REG-009), signing (REG-010), and admission enforcement (REG-012) are NOT interchangeable. Scanning detects vulnerabilities; signing proves integrity/authorship; admission enforcement prevents deployment of unverified images. Each is a distinct control layer.

---

## 7.11 Admission Enforcement — Image Policy

| Field | Details |
|---|---|
| **Test ID** | REG-012 |
| **Scope** | K8s admission controller enforcement that rejects unsigned or scanned images |
| **Positive Test** | |
| **Preconditions** | Admission plugin (OPA Gatekeeper, Kyverno, or built-in) is configured to require image signature verification; Cosign signatures are set up on images |
| **Test Command** | Attempt `kubectl apply -f` or `helm install` with an image that has valid Cosign signature |
| **Expected Output** | admission review passes; resource is created successfully |
| **Negative Test (REG-012-NEG)** | |
| **Preconditions** | Same as positive; but the resource uses an image without a valid Cosign signature |
| **Test Command** | Attempt `kubectl apply -f` or `helm install` with an unsigned image |
| **Expected Output** | Admission review denies; "image signature verification failed" or similar error; resource not created |
| **Failure Condition** | Unsigned image accepted — indicates admission plugin misconfiguration |
| **Remediation** | Configure admission plugin to enforce signature verification; add image signing to CI pipeline; adjust policy exception rules |
| **Evidence** | Admission review logs (`kubectl get events`); policy decision output; resource status |
| **Automated** | Yes — `kubectl apply` scripted with assert on resource creation/denial |
| **Manual** | Yes — manual `kubectl apply` with observation of admission decision |

---

## 7.12 Offline Artifact Availability

| Field | Details |
|---|---|
| **Test ID** | REG-013 |
| **Scope** | Availability of artifacts in offline/mirrored repository configuration |
| **Positive Test** | |
| **Preconditions** | Offline repository mirror is complete; network egress is restricted or disabled; all required artifacts are present in the offline mirror |
| **Test Command** | Attempt `yum install` or `docker pull` with network egress disabled |
| **Expected Output** | Artifact resolves from offline mirror; no external network requests; pull succeeds |
| **Failure Condition** | External network request attempted even though artifact exists in offline mirror; pull fails due to egress restriction |
| **Remediation** | Ensure offline mirror is complete and up-to-date; synchronize mirror regularly; verify repository configuration prioritizes offline source |
| **Evidence** | Package manager/pull output; network capture showing no egress; mirror sync status |
| **Automated** | Yes — scripted pull with network monitoring (tcpdump/filte r) and assert no external requests |
| **Manual** | Yes — disable egress; attempt pull; observe behavior |

---

## 7.13 Failure Cases

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-001 |
| **Scope** | Upstream unavailable |
| **Preconditions** | Upstream repository (PyPI, Maven, Docker hub) is offline or network egress is blocked |
| **Test Command** | Scripted package/image pull with network block (iptables/nftables) or service offline |
| **Expected Output** | Pull fails gracefully; clear error message ("repository not found", "connection timed out"); no hang |
| **Failure Condition** | Pull hangs indefinitely; unclear error message; retries exhaust without backoff |

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-002 |
| **Scope** | Internal proxy unavailable |
| **Preconditions** | Reverse proxy (nginx, Envoy) is stopped or misconfigured |
| **Test Command** | Attempt proxy-mediated `docker pull` or package manager request |
| **Expected Output** | Connection refused or 502/503 from proxy; fallback to direct registry access if configured |
| **Failure Condition** | Traffic routes around proxy incorrectly; proxy error masks as registry error |

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-003 |
| **Scope** | Hosted repo unavailable (Nexus/Harbor down) |
| **Preconditions** | Nexus or Harbor instance is stopped or health-checked failure |
| **Test Command** | Attempt `yum install` or `docker pull` from hosted repository |
| **Expected Output** | Clear error ("repository not found", "503 Service Unavailable"); no silent fallback |
| **Failure Condition** | Request succeeds against downstream mirror; inconsistent behavior |

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-004 |
| **Scope** | Invalid certificate |
| **Preconditions** | TLS certificate has expired, wrong CN, or is signed by unknown CA |
| **Test Command** | `docker pull` or `curl` to registry with invalid cert; or `openssl s_client -connect registry:443` |
| **Expected Output** | Certificate verification error; TLS handshake failure; explicit error message |
| **Failure Condition** | Self-signed cert accepted without validation error; indicates trust store misconfiguration |

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-005 |
| **Scope** | Auth failure |
| **Preconditions** | Valid credentials are not provided or are revoked |
| **Test Command** | `docker pull` with invalid credentials; or `docker login` with wrong password |
| **Expected Output** | "authentication required" or "login failed" error; exit code non-zero |
| **Failure Condition** | Invalid credentials accepted — indicates authorization misconfiguration |

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-006 |
| **Scope** | Missing image digest |
| **Preconditions** | Image tag is referenced without a digest (latest tag or ambiguous tag) |
| **Test Command** | `docker pull harbor-registry/example/image:latest` without pinned digest |
| **Expected Output** | Image is pulled; digest is displayed in `docker images --no-trunc`; consumer should pin digest for reproducibility |
| **Failure Condition** | Digest is not captured or verified; reproducible builds are not guaranteed |

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-007 |
| **Scope** | Invalid image signature |
| **Preconditions** | Image is unsigned or Cosign signature is corrupted |
| **Test Command** | `cosign verify` on unsigned/tampered image |
| **Expected Output** | "invalid signature" or "no signature found"; exit code non-zero |
| **Failure Condition** | Invalid signature accepted — indicates Cosign or admission policy misconfiguration |

| Field | Details |
|---|---|
| **Test ID** | REG-FAIL-008 |
| **Scope** | Missing offline artifact |
| **Preconditions** | Artifact is not present in offline mirror; network egress is restricted |
| **Test Command** | `yum install` or `docker pull` with egress blocked and artifact absent from offline mirror |
| **Expected Output** | Clear error ("package not available", "image not found"); no silent network traversal |
| **Failure Condition** | Artifact somehow retrieved despite being missing from offline mirror and egress blocked |

---
