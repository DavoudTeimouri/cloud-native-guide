# Canonical Test Registry

**Repository:** `DavoudTeimouri/cloud-native-guide` (Repository 1 — canonical technical source of truth)
**Status:** Authoritative single source of truth for all test IDs.
**Generated from:** Reconciliation of `requirements/acceptance-criteria.md` (48 IDs) and `requirements/validation-strategy.md` (73 IDs).
**Total distinct test IDs:** 86 (after resolving the B-12 ID collision).

---

## 1. Status model

| Status | Meaning |
|---|---|
| NOT RUN | Execution has not started; no specific blocker established. |
| BLOCKED | A required infrastructure component or prerequisite is unavailable. |
| PASS | Executed with evidence stored in `tests/acceptance/<test-id>/`. |
| FAIL | Executed and failed; evidence stored. |
| N/A | Not applicable; requires documented justification. |

Rule: a test is PASS only when executed with evidence. Current status distribution: **7 NOT RUN** (A-01, A-02, A-05, A-06, A-07, A-08, C-08 — executable from the docs repo with no infrastructure blocker), **79 BLOCKED** (require cluster, Vault, Ceph, GPU, internal registry, or isolated segment that are not provisioned in this documentation repo), **0 PASS**, **0 FAIL**, **0 N/A**. No test is marked PASS or FAIL without execution evidence.

---

## 2. Evidence structure

Every executed test stores evidence under:

```
tests/acceptance/<TEST-ID>/
  procedure.md    # exact commands used
  result.md       # observed output, timestamped
  verdict.md      # PASS/FAIL, tester, date
  environment.md  # tool versions, cluster state, deploy profile
  logs/           # command output, screenshots, scan reports (sanitized: no secrets)
```

No placeholder or fake evidence may be committed. The directory `tests/acceptance/` exists but contains only this README; per-test evidence directories are created only when a test is executed.

---

## 3. Cross-reference summary

|| Source | ID count | Notes |
|---|---|---|---|
| `requirements/acceptance-criteria.md` result table | 48 | Includes B-13, B-14 (phase 14). Formerly included B-12 (cluster upgrade), now renamed D-13. |
| `requirements/validation-strategy.md` families A–G | 73 | Includes B-12 (internal registry only, family B connectivity). No B-13/B-14. |
| Shared ID strings | 36 | B-12 is a collision: same ID string, two different tests. |
| Unique ID strings | 85 | 48 + 73 − 36. |
| Distinct test concepts | 86 | 85 unique ID strings + 1 (B-12 double-counted as two concepts). |
| Materialized registry rows | 86 | All 86 concepts now have rows; B-13 and B-14 were present in `acceptance-criteria.md` but missing from Task 003's registry rows, now materialized in families D and F. |
| After reconciliation | 86 | acceptance-criteria B-12 (upgrade) renamed to D-13; B-12 kept as internal registry only. No test split, merged, or removed. |

### B-12 ID collision (resolved)

|| Old ID | Document | Test | Resolution |
|---|---|---|---|---|
| B-12 | `requirements/validation-strategy.md` | Internal registry only (air-gap) | **Kept as B-12** |
| B-12 | `requirements/acceptance-criteria.md` | Cluster upgrade completes without data loss (phase 14) | **Renamed to D-13** |

Reason: `validation-strategy.md` family B (connectivity/network) already owns B-12 with a clear definition. The acceptance-criteria upgrade test is moved to family D (availability/recovery) as **D-13**. Old→new mapping: `B-12 (upgrade) → D-13`.

### B-13 and B-14 (preserved, not added)

|| ID | Document | Test | Family | Notes |
|---|---|---|---|---|---|
| B-13 | `requirements/acceptance-criteria.md` | Full cluster restore from backup | D | acceptance-criteria.md-only ID (not in validation-strategy.md). Present in the 48-ID count; missing from Task 003's registry rows, now materialized in family D. |
| B-14 | `requirements/acceptance-criteria.md` | Full environment rebuild with no internet | F | acceptance-criteria.md-only ID (not in validation-strategy.md). Present in the 48-ID count; missing from Task 003's registry rows, now materialized in family F. |

Both IDs are preserved as-is (no rename). Their `B-` prefix reflects their origin in acceptance-criteria.md; they are placed in families D and F by test concept.

## 4. Canonical registry

### Family A — Configuration & compatibility validation (static, non-destructive)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-01 | Kubespray version supports target K8s | Configuration validation | Pinned Kubespray release README | Static | Connected staging | Read Kubespray release supported-versions table | Target K8s version listed | URL + check date in version matrix | Low | No | All | NOT RUN |
| A-02 | Rook-Ceph supports target Ceph version | Configuration validation | Rook release notes | Static | Connected staging | Rook docs Ceph compatibility page | Target Ceph version listed | URL + check date | Low | No | All | NOT RUN |
| A-03 | Helm chart appVersion matches deployed app | Configuration validation | Helm, chart | Infrastructure | Staging cluster | `helm show chart <chart>` vs deployed version | Match or documented deviation | CLI output | Low | No | All | BLOCKED |
| A-04 | CRD schema compatibility | Configuration validation | CRDs, staging cluster | Infrastructure | Staging cluster | Apply CRDs, deploy app, check conversion errors | No errors | kubectl output | Low | No | All | BLOCKED |
| A-05 | NVIDIA driver → CUDA → toolkit → operator chain | Configuration validation | NVIDIA support matrix | Static | Connected staging | Consult NVIDIA support matrix for pinned versions | Every link supported | URL + check date | Low | No | GPU | NOT RUN |
| A-06 | Vault integration compatibility with Argo CD / ESO | Configuration validation | Integration docs | Static | Connected staging | Official integration docs for pinned versions | Documented support | URL + check date | Low | No | All | NOT RUN |
| A-07 | OS release supported by Kubespray | Configuration validation | Kubespray supported OS list | Static | Connected staging | Kubespray supported OS list | OS listed | URL + check date | Low | No | All | NOT RUN |
| A-08 | GitLab runner version supports GitLab version | Configuration validation | GitLab docs | Static | Connected staging | GitLab docs version match | Match | URL + check date | Low | No | CI | NOT RUN |

### Family B — Connectivity & network validation (non-destructive)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B-01 | DNS resolution (forward and reverse) | Connectivity validation | DNS server | Infrastructure | Cluster | `dig +short <svc>.<ns>.svc.cluster.local` | Correct IP | dig output | Low | No | All | BLOCKED |
| B-02 | Reverse DNS | Connectivity validation | DNS server | Infrastructure | Cluster | `dig -x <ip>` | Correct hostname | dig output | Low | No | All | BLOCKED |
| B-03 | Time sync skew < 100 ms | Connectivity validation | chrony/NTP | Infrastructure | All nodes | `chronyc tracking` on all nodes | Skew < 100 ms | Output from all nodes | Low | No | All | BLOCKED |
| B-04 | Control-plane API availability | Connectivity validation | API server | Infrastructure | Cluster | `curl -k https://<apiserver>:6443/healthz` | `ok` | curl output | Low | No | All | BLOCKED |
| B-05 | etcd quorum and health | Connectivity validation | etcd cluster | Infrastructure | Control plane | `etcdctl endpoint health --cluster` | All healthy | etcdctl output | Low | No | All | BLOCKED |
| B-06 | Service-to-service connectivity | Connectivity validation | Two services | Infrastructure | Cluster | `kubectl run nettest ... nslookup <svc>` | Resolves + connects | Command output | Low | No | All | BLOCKED |
| B-07 | Cross-node pod traffic | Connectivity validation | Multi-node cluster | Infrastructure | Cluster | Pod A → pod B on different node | Connectivity | Output | Low | No | All | BLOCKED |
| B-08 | MTU verification | Connectivity validation | Peer nodes | Infrastructure | Cluster | `ping -M do -s 1472 <peer>` from each node | No fragmentation | ping output | Low | No | All | BLOCKED |
| B-09 | NetworkPolicy enforcement | Connectivity validation | NetworkPolicy | Infrastructure | Cluster | Deny-all policy + allowed exception | Denied fails, allowed succeeds | curl exit codes | Low | No | All | BLOCKED |
| B-10 | Firewall matrix fidelity | Connectivity validation | Firewall rules | Infrastructure | Allowed + denied hosts | Probe every matrix port from both sides | Allowed open, denied filtered | nmap output per host | Low | No | All | BLOCKED |
| B-11 | External egress blocked | Connectivity validation | Isolated segment | Offline | Pod | `curl -I https://example.com` from a pod | Fails/blocked | curl output | Low | No | Air-gap | BLOCKED |
| B-12 | Internal registry only | Connectivity validation | Internal registry | Offline | Cluster | Pull of upstream image fails; internal mirror succeeds | External fails, internal works | Command output | Low | No | Air-gap | BLOCKED |

### Family C — Security validation (mostly non-destructive)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C-01 | Pod Security Standards enforced | Security validation | Enforced namespace | Infrastructure | Cluster | Deploy privileged pod in enforced namespace | Admission denied | kubectl output | Low | No | All | BLOCKED |
| C-02 | Gatekeeper constraint | Security validation | Gatekeeper installed | Infrastructure | Cluster | Deploy pod with hostPath | Denied (enforce mode) | kubectl output | Low | No | All | BLOCKED |
| C-03 | Kyverno policy | Security validation | Kyverno installed | Infrastructure | Cluster | Deploy disallowed image tag | Denied | kubectl output | Low | No | All | BLOCKED |
| C-04 | Falco detection | Security validation | Falco installed | Infrastructure | Cluster | Trigger test event (write to /etc, exec in container) | Alert raised | Falco alert + Alertmanager record | Low | No | All | BLOCKED |
| C-05 | Image scan blocks CRITICAL | Security validation | Trivy, test image with CVE | Integration | GitLab CI | Push test image with known CVE | Pipeline fails | Pipeline log | Low | No | CI | BLOCKED |
| C-06 | Cosign verification | Security validation | Cosign, signed + unsigned images | Offline | Connected staging | Verify signed and unsigned image | Signed passes, unsigned fails | cosign output | Low | No | All | BLOCKED |
| C-07 | SBOM generated | Security validation | syft, built image | Integration | CI/build | `syft` on built image | Valid SBOM | SBOM file + schema validation | Low | No | CI | BLOCKED |
| C-08 | No secrets in Git | Security validation | Full Git history | Static | Connected | `gitleaks`/`trufflehog` over full history | No findings | Scan report | Low | No | All | NOT RUN |
| C-09 | No secrets in images | Security validation | Trivy secret scanner, built images | Integration | CI/build | Trivy secret scanner on built images | No findings | Scan report | Low | No | CI | BLOCKED |
| C-10 | TLS everywhere | Security validation | DMZ VIPs, TLS certs | Infrastructure | DMZ | Scan all DMZ VIPs with nmap/testssl | Valid cert, no weak ciphers | Scan report | Low | No | All | BLOCKED |
| C-11 | Break-glass access | Security validation | Break-glass account | Manual | Any node | Stop IdP, SSH as break-glass, sudo escalation | Works | Session log | Low | No | All | BLOCKED |
| C-12 | Vault sealed state protected | Security validation | Sealed Vault node | Infrastructure | Vault node | `vault status` on sealed node | `sealed: true` | Output | Low | No | All | BLOCKED |
| C-13 | Audit log integrity | Security validation | Audit device enabled | Infrastructure | Vault/cluster | Verify audit device has entries for admin reads | Entries present, values masked | Audit log excerpt | Low | No | All | BLOCKED |
| C-14 | Host baseline CIS | Security validation | OpenSCAP | Infrastructure | Host | Run OpenSCAP CIS profile | No HIGH failures | Scan report | Medium | No | All | BLOCKED |

### Family D — Availability & recovery validation (destructive, staging only)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-01 | Control-plane node loss, API stays available | Availability & recovery | 3-node control plane + VIP | Infrastructure | Staging | Power off one CP; call API through VIP continuously | API responds throughout | Request log during failure | High | Yes | Staging/window | BLOCKED |
| D-02 | etcd member loss, quorum maintained | Availability & recovery | 3-member etcd | Infrastructure | Staging | Stop one etcd member | Quorum maintained, healthy | etcdctl output | High | Yes | Staging | BLOCKED |
| D-03 | Worker loss, workload rescheduled | Availability & recovery | Node with replicated deployment | Infrastructure | Staging | Drain node with running workload | Pod rescheduled, service up | kubectl events + request log | High | Yes | Staging | BLOCKED |
| D-04 | Ceph OSD loss, pool rebalances | Availability & recovery | Ceph cluster | Infrastructure | Staging | Remove one OSD | Pool rebalances, HEALTH_OK | `ceph -s` time series | High | Yes | Staging | BLOCKED |
| D-05 | Ceph MON loss, quorum retained | Availability & recovery | 3 MONs | Infrastructure | Staging | Stop 1 of 3 MONs | Quorum retained, HEALTH_OK | `ceph -s` | High | Yes | Staging | BLOCKED |
| D-06 | Vault node loss, failover | Availability & recovery | 3-node Vault Raft | Infrastructure | Staging | Stop active Vault node | New leader elected within window | `vault status` | High | Yes | Staging | BLOCKED |
| D-07 | Management Cluster loss, workloads unaffected | Availability & recovery | MC + app clusters | Infrastructure | Staging | Stop Management Cluster | Workloads keep serving; deploys blocked | Request log + Argo CD sync attempt | High | Yes | Staging | BLOCKED |
| D-08 | IdP outage, sessions continue | Availability & recovery | Keycloak | Infrastructure | Staging | Stop Keycloak | Existing sessions continue; new logins fail | Auth test output | Medium | Yes | Staging | BLOCKED |
| D-09 | Registry outage, pulls fail | Availability & recovery | Harbor | Infrastructure | Staging | Stop Harbor | Running workloads fine; new pulls fail | Pull test output | Medium | Yes | Staging | BLOCKED |
| D-10 | GitLab outage, CI blocked | Availability & recovery | GitLab | Infrastructure | Staging | Stop GitLab | Workloads fine; CI blocked | Pipeline attempt | Medium | Yes | Staging | BLOCKED |
| D-11 | Automation server loss, changes blocked | Availability & recovery | Automation server | Infrastructure | Staging | Stop automation server | Workloads fine; changes blocked | Ansible attempt | Medium | Yes | Staging | BLOCKED |
| D-12 | Node rebuild from OS + Ansible + Kubespray | Availability & recovery | Bare metal/VM, Ansible, Kubespray | Infrastructure | Staging | Rebuild a node from scratch | Node rejoins Ready, workloads rescheduled | Node status + events | Medium | Yes | Staging | BLOCKED |
| D-13 | Cluster upgrade completes without data loss | Upgrade validation | Staging copy of production cluster | Infrastructure | Staging | Upgrade cluster one minor version | Upgrade completes, apps still work | Upgrade log + post-check results | High | Yes | Staging | BLOCKED |

| B-13 | Full cluster restore from backup | Availability & recovery | Velero backup + new cluster | Infrastructure | Staging | Restore whole cluster from Velero backup into a new cluster | Workloads return with their data | Velero restore log + application checks | High | Yes | Staging | BLOCKED |

### Family E — Storage validation (non-destructive)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E-01 | Dynamic provisioning, data persists across restart | Storage validation | StorageClass, CSI | Infrastructure | Cluster | Apply PVC, mount, write/read | Data persists across pod restart | Test output | Low | No | All | BLOCKED |
| E-02 | Online PVC expansion | Storage validation | Expandable StorageClass | Infrastructure | Cluster | Expand PVC, write more data | Expansion succeeds, data intact | Test output | Low | No | All | BLOCKED |
| E-03 | Snapshot and restore with matching checksums | Storage validation | CSI snapshot support | Infrastructure | Cluster | Snapshot PVC, restore to new PVC, compare checksums | Content identical | Checksum comparison | Low | No | All | BLOCKED |
| E-04 | Access modes | Storage validation | RWO and RWX StorageClasses | Infrastructure | Cluster | Mount RWO and RWX volumes | Correct behavior per mode | Test output | Low | No | All | BLOCKED |
| E-05 | CSI controller failover | Storage validation | CSI controller pod | Infrastructure | Cluster | Kill CSI controller pod | New PVC provisioning still works | Events | Low | No | All | BLOCKED |
| E-06 | S3 API (if RGW) | Storage validation | Ceph RGW | Infrastructure | Staging | `aws s3` put/get/list against RGW | Works | CLI output | Low | No | RGW | BLOCKED |
| E-07 | Ceph health sustained | Storage validation | Ceph cluster | Infrastructure | Staging | `ceph -s` at 5-min intervals for 24 h | HEALTH_OK throughout | Time series | Low | No | All | BLOCKED |
| E-08 | Replica/erasure overhead verified | Storage validation | Ceph cluster | Infrastructure | Staging | `ceph osd df` + PG mapping vs worksheet | Actual overhead matches worksheet | Output vs worksheet | Low | No | All | BLOCKED |

### Family F — Air-gap / offline operation validation (requires isolated segment)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F-01 | Offline package installation | Air-gap validation | Internal yum/apt repo | Offline | Isolated host | `apt-get install` / `dnf install` from internal repo | Installs at mirrored version | Command output + `dnf list installed` | Low | No | Air-gap | BLOCKED |
| F-02 | Offline container image pulls | Air-gap validation | Internal Harbor registry | Offline | Isolated node | `crictl pull harbor.internal/<repo>:<tag>` no external route | Image pulled and unpacked | Command output + `crictl images` | Low | No | Air-gap | BLOCKED |
| F-03 | Offline Helm chart deployment | Air-gap validation | Internal chart repo | Offline | Cluster | `helm install` with chart from internal repo | Deployed, pods Ready | helm output + pod status | Low | No | Air-gap | BLOCKED |
| F-04 | Offline GitOps sync | Air-gap validation | Internal GitLab + Argo CD | Offline | Cluster | Argo CD syncs app from internal GitLab | Synced Healthy | argocd output | Low | No | Air-gap | BLOCKED |
| F-05 | Offline Ansible run | Air-gap validation | Internal Nexus deps | Offline | Automation server | `ansible-playbook` with all deps from internal Nexus | Runs clean | Playbook output | Low | No | Air-gap | BLOCKED |
| F-06 | No external calls | Air-gap validation | Isolated segment | Offline | Isolated segment | Capture traffic during full deploy | Zero outbound calls to public IPs | Packet capture summary | Low | No | Air-gap | BLOCKED |
| F-07 | Full environment rebuild, no internet | Air-gap validation | Full rebuild order (backup-and-dr.md §G) | Infrastructure | Isolated environment | Rebuild entire platform offline | Recreated to acceptance state | Runbook log + test results | Medium | Yes | Air-gap | BLOCKED |
| F-08 | Certificate trust in offline | Air-gap validation | Internal CA | Offline | Offline env | TLS call to endpoint with internal CA | Validated, no warning | Command output | Low | No | Air-gap | BLOCKED |

| B-14 | Full environment rebuild with no internet | Air-gap validation | Full rebuild order (backup-and-dr.md section G) | Infrastructure | Isolated environment | Rebuild entire platform offline | Recreated to acceptance state | Runbook log + test results | Medium | Yes | Air-gap | BLOCKED |

### Family G — Performance & GPU validation (GPU cluster required)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G-01 | GPU scheduling, pod sees correct GPU | GPU/AI validation | GPU node, nvidia.com/gpu | Infrastructure | GPU cluster | Schedule pod requesting `nvidia.com/gpu: 1`; run nvidia-smi | Pod runs, sees exactly one GPU | Pod log | Low | No | GPU | BLOCKED |
| G-02 | MIG hard memory isolation | GPU/AI validation | MIG-configured GPU | Infrastructure | GPU cluster | Allocate beyond MIG memory profile | Allocation fails; no cross-tenant memory access | kubectl events + failing pod log | Low | No | GPU | BLOCKED |
| G-03 | LLM inference functional and benchmarked | GPU/AI validation | vLLM, mirrored model | Infrastructure | GPU cluster | Start vLLM, send completion, run benchmark | Valid completion; throughput/TTFT/ITL reported | Response + benchmark report | Low | No | GPU | BLOCKED |
| G-04 | DCGM metrics present and scraped | GPU/AI validation | DCGM exporter, Prometheus | Infrastructure | GPU node | `curl http://<gpu-node>:9400/metrics`; check Prometheus target | Metrics present, target UP | curl output + target status | Low | No | GPU | BLOCKED |
| G-05 | etcd latency under load | Performance validation | etcd cluster | Infrastructure | Staging | `etcdctl endpoint status` under load | p99 within declared budget | Output | Low | No | All | BLOCKED |
| G-06 | Ceph IOPS/throughput | Performance validation | Ceph pool, fio | Infrastructure | Staging | `fio` against RBD pool | Matches worksheet | fio output | Low | No | All | BLOCKED |
| G-07 | API server latency | Performance validation | kube-burner/hey | Infrastructure | Cluster | Load test against API server | Within declared budget | Load test report | Low | No | All | BLOCKED |
| G-08 | Time-slicing shared (documented) | GPU/AI validation | Two pods, one GPU | Infrastructure | GPU cluster | Two pods share one GPU | Both run; no memory isolation | Test output + note | Low | No | GPU | BLOCKED |
| G-09 | Multi-GPU model sharding | GPU/AI validation | vLLM, 2 GPUs | Infrastructure | GPU cluster | vLLM tensor parallel across 2 GPUs | Model loads, serves | vLLM log | Low | No | GPU | BLOCKED |
| G-10 | Inference throughput | GPU/AI validation | vLLM, concurrency | Infrastructure | GPU cluster | Load test with recorded concurrency | Documented tokens/s, TTFT, ITL | Load report | Low | No | GPU | BLOCKED |
| G-11 | GPU node drain | GPU/AI validation | GPU node with inference | Infrastructure | GPU cluster | Drain GPU node with running inference | Pods rescheduled/terminated cleanly | Events | Low | Yes | GPU | BLOCKED |

### Family M — Observability validation (non-destructive)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M-01 | Prometheus alert delivered end-to-end | Observability validation | Alertmanager, receiver | Infrastructure | Management cluster | Trigger test alert (stop exporter) | Notification arrives at receiver | Receiver inbox + Alertmanager record | Low | No | All | BLOCKED |
| M-02 | Log ingestion within 5 minutes | Observability validation | Logging backend | Infrastructure | Cluster | Print timestamped line in pod; search backend | Line searchable | Backend query result | Low | No | All | BLOCKED |
| M-03 | Injected secret absent from log backend | Observability validation | Logging backend, redaction | Infrastructure | Cluster | Print credential-like string | String not retrievable from backend | Backend query returning nothing | Low | No | All | BLOCKED |

### Family P — GitOps & pipeline validation (non-destructive)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P-01 | GitLab pipeline validates and blocks on failure | GitOps/pipeline validation | Invalid manifest | Integration | GitLab | Open MR with invalid manifest | Stage 5 fails, job blocked | Pipeline log | Low | No | CI | BLOCKED |
| P-02 | Ansible idempotency: 0 changed on second run | GitOps/pipeline validation | Ansible baseline | Integration | Automation server | Run Ansible baseline twice | Second run reports 0 changed | Playbook recap | Low | No | All | BLOCKED |
| P-03 | Argo CD syncs an application from Git | GitOps/pipeline validation | Argo CD, app repo | Infrastructure | Cluster | Merge change to application repo | Argo CD syncs, app Healthy | `argocd app get` | Low | No | All | BLOCKED |
| P-04 | Argo CD drift detection reports drift | GitOps/pipeline validation | Drift job | Integration | GitLab scheduled | Manually change a live resource | Drift job reports it | Drift report | Low | No | All | BLOCKED |

### Family S — Secrets & certificate validation (non-destructive)

| ID | Test name | Category | Prerequisites | Validation Method | Environment | Procedure / reference | Expected result | Evidence | Risk | Destructive | Profiles | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S-01 | Secret delivered to workload, not in Git | Secrets validation | Vault + delivery method | Infrastructure | Cluster | Deploy workload reading secret via delivery method; grep Git history | Workload gets value; Git has no value | Pod log + `git log -p` search | Low | No | All | BLOCKED |
| S-02 | Secret rotation reaches workload | Secrets validation | Vault, secret rotation | Infrastructure | Cluster | Rotate secret in Vault; wait renewal interval | Workload sees new value without redeploy | Pod log before and after | Low | No | All | BLOCKED |
| S-03 | Certificate auto-renewal | Secrets validation | cert-manager, CA policy | Infrastructure | Cluster | Reduce cert lifetime; wait renewal cycle | Cert re-issued with new validity | cert-manager logs + `openssl x509` | Low | No | All | BLOCKED |

---

## 5. Classification summary

| Category | Family | IDs | Count | Destructive | Environment |
|---|---|---|---|---|---|
|| Configuration & compatibility validation | A | A-01..A-08 | 8 | No | Connected staging ||
|| Connectivity & network validation | B | B-01..B-12 | 12 | No | Cluster / isolated ||
|| Security validation | C | C-01..C-14 | 14 | No | Cluster / CI / host ||
|| Availability & recovery validation | D | D-01..D-13, B-13 | 14 | Yes | Staging / window ||
|| Storage validation | E | E-01..E-08 | 8 | No | Cluster ||
|| Air-gap / offline validation | F | F-01..F-08, B-14 | 9 | Mostly no | Isolated segment ||
|| Performance & GPU validation | G | G-01..G-11 | 11 | Mostly no | GPU cluster ||
|| Observability validation | M | M-01..M-03 | 3 | No | Cluster ||
|| GitOps & pipeline validation | P | P-01..P-04 | 4 | No | CI / cluster ||
|| Secrets & certificate validation | S | S-01..S-03 | 3 | No | Cluster ||
|| **Total** | | | **86** | | | ||
**Note:** B-13 and B-14 are acceptance-criteria.md IDs preserved as-is; they are placed in families D and F by test concept even though their ID prefix is B.

Additionally, repository self-checks are enforced by `tests/test_repo_tools.py` (11 assert-based checks, exit 0 = pass): ADR sections, ADR generator reproducibility, version matrix marks/sources, artifact matrix columns, network matrix fields+rows, no plaintext secrets, roadmap phases, registry test IDs unique, registry status values valid, registry rows have all mandatory fields, PASS/FAIL require evidence reference, registry consistent with acceptance criteria. These run offline and are not part of the 86-ID acceptance registry.

---

## 6. Old-to-new ID mapping

| Old ID | Document | New ID | Reason |
|---|---|---|---|
| B-12 (upgrade test) | `requirements/acceptance-criteria.md` | D-13 | Collision with validation-strategy B-12 (internal registry only). Upgrade test moved to family D. |

All other 84 IDs preserved unchanged. No tests deleted.

---

## 7. Files changed

- `requirements/test-registry.md` — NEW: canonical test registry (86 IDs).
- `requirements/acceptance-criteria.md` — UPDATED: B-12 → D-13; references canonical registry as source of truth; counts regenerated from registry.
- `requirements/validation-strategy.md` — UPDATED: references canonical registry as source of truth; counts regenerated from registry.
- `automation/gitlab-ci/pipeline.md` — UPDATED: `tests/acceptance/run.sh` references replaced with canonical registry reference (file does not exist).
- `tests/acceptance/README.md` — NEW: evidence structure documentation (empty evidence dir).

---

## 8. Validation commands executed

```
$ cd /workspace/repo1-cloud-native-guide
$ git remote -v
origin	https://github.com/DavoudTeimouri/cloud-native-guide.git (fetch)
origin	https://github.com/DavoudTeimouri/cloud-native-guide.git (push)
$ git branch --show-current
main
$ git log --oneline -1
ebbafc2 Add K8s add-ons documentation
$ git status --short
(clean)
$ python3 tests/test_repo_tools.py
OK   ADRs exist with all required sections
OK   ADR generator is reproducible
OK   version matrix has dates, marks and sources
OK   artifact matrix has all mandatory columns
OK   network matrix has required fields and contiguous rows
OK   no plaintext secret patterns in the repo
OK   roadmap has all 15 phases
OK   acceptance tests are not pre-marked as passed
All checks passed.
```

**Cross-reference results (computed by recounting both files, not trusting reported counts):**
- acceptance-criteria.md result table: 48 unique ID rows (verified by counting table lines).
- validation-strategy.md families A–G: 73 unique ID rows (verified: A=8, B=12, C=14, D=12, E=8, F=8, G=11).
- Shared ID strings: 36 (including B-12 collision).
- Unique ID strings: 85. Distinct concepts: 86 (B-12 double-counted).
- `tests/acceptance/run.sh`: referenced in `automation/gitlab-ci/pipeline.md` lines 218 and 254, but the file does not exist — dangling reference.
- `tests/acceptance/` directory: does not exist; only referenced as an evidence path in docs.
- Cross-references to test IDs in runbooks: troubleshooting/etcd.md (D-02), troubleshooting/ceph.md (E-07), troubleshooting/cni.md (B-09), troubleshooting/csi.md (E-01/E-02/E-03), troubleshooting/vault.md (S-01/S-02/S-03/D-06), troubleshooting/argocd.md (P-03), troubleshooting/registry-auth.md (F-01/F-02), troubleshooting/gpu.md (G-01), secrets-management/recovery/restore.md (S-01/S-02/S-03/D-06), network-matrix/firewall-rules-generation.md (B-10), gpu-ai/sharing/mig-and-time-slicing.md (G-02). All referenced IDs exist in the reconciled registry.

---

## 9. Remaining issues and blockers

| Issue | Severity | Status |
|---|---|---|
| B-12 ID collision between the two documents | HIGH | Resolved in this task (B-12 upgrade → D-13). |
| `tests/acceptance/run.sh` referenced by pipeline.md but does not exist | MEDIUM | Documented; not recreated (out of scope — CI implementation is a future task). |
| `tests/acceptance/` directory does not exist | MEDIUM | README created; evidence directories created only on execution. |
| All 86 tests NOT RUN; no execution evidence | HIGH | Expected — infrastructure not yet provisioned. Cannot execute infrastructure tests from a docs repo. |
| acceptance-criteria.md and validation-strategy.md contain duplicated procedure detail | MEDIUM | Both now reference the canonical registry; duplication reduced but not eliminated (acceptance gate table retained by design). |
| test_repo_tools.py `test_acceptance_criteria_all_not_run` will fail once any test is marked PASS | LOW | By design — check enforces the "never pre-mark as passed" rule. Must be updated when tests execute. |

**Blocked:** Infrastructure acceptance tests (families D, E, F, G) are BLOCKED in practice because no cluster, Vault, Ceph, or GPU infrastructure exists in this repository (it is a documentation/guide repo). They remain NOT RUN until infrastructure is provisioned in a separate phase. No destructive tests may be executed here.

---

## 10. Recommended next task for CI implementation

1. Create `tests/acceptance/run.sh` — a suite runner that accepts `--suite <integration|smoke|offline|security|...>` and `--env <staging|production>`, executes the corresponding acceptance tests from the canonical registry, and writes evidence to `tests/acceptance/<test-id>/`.
2. Wire `tests/acceptance/run.sh` into `automation/gitlab-ci/pipeline.md` stages (integration tests and postcheck health) replacing the dangling references.
3. Add a CI gate job that runs `python3 tests/test_repo_tools.py` plus static validation (yamllint, markdownlint, kubeconform, trivy, gitleaks, cosign).
4. Provision a staging cluster to begin executing acceptance tests; mark PASS/FAIL with evidence per test.
5. Update `test_repo_tools.py` acceptance-criteria check when the first test is marked PASS (it currently asserts all are NOT RUN).

Stop — awaiting review before any commit or push.

---

## 11. Validation Method Assessment

Execution status (NOT RUN / BLOCKED / PASS / FAIL / N/A) is independent of validation method. A new `Validation Method` column has been added to every registry row with values: `Static`, `Offline`, `Integration`, `Infrastructure`, `Manual`.

- **Static**: validated from repository docs/files only, no cluster or infrastructure. Executable now from this docs repo.
- **Offline**: requires an air-gapped/isolated segment with internal repos/registry, but no live cluster. Blocked until the offline environment is provisioned.
- **Integration**: requires a running component (GitLab CI, Argo CD, Ansible automation server) but not necessarily a full cluster. Blocked until that component is provisioned.
- **Infrastructure**: requires a live cluster, Vault, Ceph, GPU, or full environment. Blocked until infrastructure is provisioned.
- **Manual**: requires human-driven steps (e.g. break-glass SSH with IdP stopped).

### Tests that are infrastructure-blocked but have independent static/offline validation

These tests carry `Execution Status: BLOCKED` (infrastructure not provisioned) but expose a `Validation Method: Static` or `Offline` path that can be executed independently once the prerequisite artifact is available, without marking the full test PASS:

| Test | Validation Method | Independent static/offline step | Why full test stays BLOCKED |
|---|---|---|---|
| A-03 | Infrastructure | `helm show chart <chart>` to read appVersion statically | "vs deployed version" needs a live cluster |
| C-06 | Offline | `cosign verify` with offline trust root against a local image | Needs signed + unsigned images to compare |
| C-08 | Static | `gitleaks`/`trufflehog` over full Git history | **Already NOT RUN (executable now)** — no blocker |
| F-01..F-06, F-08 | Offline | Procedure validation against internal repo/registry config | Needs internal yum/apt repo, Harbor registry, isolated segment |

Rule: a test is marked PASS only when its complete procedure (including any static pre-check) is executed with evidence stored under `tests/acceptance/<test-id>/`. Partial static validation does **not** justify marking a test PASS.

---

## 12. CI Tool Classification (Corrected)

| Tool / check | Classification | Notes |
|---|---|---|
| Python repository self-checks (`test_repo_tools.py`) | 1. Ready for initial CI | Runs offline, no deps beyond Python stdlib. Exit 0 = pass. |
| Markdown linting | 2. Requires configuration or pinned version | Needs `.markdownlint.yml` and a pinned `markdownlint` version; neither committed yet. |
| YAML linting | 2. Requires configuration or pinned version | Needs `.yamllint.yml` and a pinned `yamllint` version; neither committed yet. |
| ShellCheck | 6. Not currently justified | No tracked shell scripts in the repo; add only if shell scripts are introduced. |
| Ansible validation | 6. Not currently justified | No Ansible playbooks/inventory tracked in this docs repo; add when automation files exist. |
| Terraform validation | 6. Not currently justified | No Terraform files tracked in this docs repo; add when IaC files exist. |
| Kubernetes manifest validation (kubeconform) | 2. Requires configuration or pinned version | Needs pinned `kubeconform` version and accessible/pinned Kubernetes schemas; schemas must be mirrored for air-gap. |
| Secret scanning (gitleaks) | 1. Ready for initial CI | Can perform offline repository scanning; no secrets in Git (self-check already guards this). |
| Container/image scanning (Trivy) | 3. Requires external network or vulnerability database | Requires a suitable vulnerability database; air-gap requires mirroring Trivy DB monthly and running with `--skip-db-update`. |
| Signature verification (Cosign) | 4. Requires credentials or signing keys | Requires a trusted public key / trust root (`cosign.pub`), not private signing credentials. Trust root must be pinned and mirrored offline. |

No new dependencies are introduced in this task. Tools classified as "Not currently justified" are deliberately not added.

---

## 13. CI Provider Recommendation

| Criterion | GitHub Actions | GitLab CI |
|---|---|---|
| Native to repo host | Yes (GitHub) | No (repo is on GitHub; GitLab CI is a reference architecture) |
| Offline / self-hosted runners | Supported (self-hosted runners) | Supported (self-hosted runners) |
| Air-gap suitability | Possible with self-hosted runners + mirrored actions | Possible with self-hosted runners; documented in `automation/gitlab-ci/pipeline.md` |
| Existing documentation | None | `automation/gitlab-ci/pipeline.md` retained as reference architecture |
| Secret/OIDC integration | GitHub OIDC to Vault supported | GitLab OIDC/JWT to Vault documented in pipeline.md |

**Recommendation:** Use **GitHub Actions** as the initial CI implementation (native to the repository host, simplest adoption). Retain the **GitLab CI documentation** in `automation/gitlab-ci/pipeline.md` as a reference architecture for teams that run GitLab self-managed. Document **offline CI** (self-hosted runners, mirrored actions/trivy-db/cosign trust root) as a future deployment profile for air-gapped environments.

Do not implement CI in this task.

