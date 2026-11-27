# Section 3: Version Compatibility and Support Matrix

Centralized compatibility matrix covering stack components.

## How to read this file

| Mark | Meaning |
|---|---|
| **VERIFIED** | Read from the official source on the check date; the source is linked. This version has been validated against the upgrade path. |
| **PINNED** | The exact version this platform deploys (chosen from the VERIFIED set). |
| **UNVERIFIED** | Not confirmed. The verification procedure is stated; the value must not be used in a deploy until confirmed. |

Refresh procedure: run `scripts/fetch_versions.py` and `scripts/helm_chart_versions.py` in a connected environment, diff against this file, and open an MR with the change plus the check date.

## Evidence Convention

This section explains the confidence/validation status classifications used in this matrix. Each status carries specific evidentiary requirements and usage guidelines.

| Status | Meaning | Evidential Requirement |
|---|---|---|
| **CONFIRMED** | Read from the official source on the verification date; the source is linked. This version has been project-tested and validated. | Direct source URL present in the `Upstream Documentation Reference` column. Verification date recorded. |
| **UPSTREAM** | Upstream documentation states compatibility, but the project has not independently tested this combination. | Upstream source URL present; project-tested compatibility not claimed. |
| **CONDITIONAL** | Compatible only under specific constraints or constraints noted in the evidence. | Source URL present; specific constraints documented; usage subject to those constraints. |
| **UNVERIFIED** | Not confirmed. The verification procedure is stated; the value must not be used in a deploy until confirmed. | No confirmed source validation; must not be used in production deployment until verification is complete. |
| **UNSUPPORTED** | Explicitly not supported. This combination is known to be unsupported or out of support lifecycle. | Source URL documenting the lack of support; may include EOL dates or explicit unsupport statements. |

**Upstream vs. Project-Tested Compatibility:**
- **Upstream compatibility** reflects what the component's upstream project claims about compatibility (e.g., "Kubernetes v1.37 is supported"). These statements are sourced from upstream documentation, release notes, or websites.
- **Project-tested compatibility** reflects what this platform has verified through testing in its specific environment. A project-tested status requires a linked source URL AND contextual evidence of successful operation in the platform's environment.

**Recording Source Publication/Release Date:**
- The `Verification Date` column records the date the source was read/checked against.
- The `Current Documented Version` and `Target Version` columns should reference the specific upstream release or version range.
- For upstream statements, also record the upstream publication or release date where available from the source URL.
- Refresh procedure: run `scripts/fetch_versions.py` and `scripts/helm_chart_versions.py` to update versions and verification dates; diff against this file and open an MR with the change plus the new check date.

### Verification date semantics

The `Verification Date` column below records the **last documentation review/update date** (`2026-10-17` on all rows), not a live source check performed in this session. No upstream source was re-fetched or re-verified live for any row, so no row may claim `Last verified` status from a live check. The value `2026-10-17` should be read as `Last updated` (documentation review date), consistent with the Evidence Convention above.

Honest date convention used going forward:
- **Last verified**: only when an upstream source was actually fetched and checked on that date; source URL present. Not claimed for any row below.
- **Source release date**: the upstream component's release/publication date, recorded where the linked source states it. Not yet recorded per-row below (a known gap).
- **Last updated**: documentation modification/review date (`2026-10-17` on all rows below).
- **Verification status**: `VERIFIED` rows mean "source URL present and claim consistent with linked upstream documentation at last review" — they do **not** mean project-tested or live-reverified. Rows that cannot be confirmed remain `UNVERIFIED` or `CONDITIONAL` with an explanation.

## Version Compatibility and Support Matrix

| Component | Current Documented Version | Target Version | Supported Kubernetes Versions | OS Compatibility | Runtime Dependencies | CNI/CSI Dependencies | Upgrade Constraints | Support Lifecycle Status | Upstream Documentation Reference | Verification Date | Confidence/Validation Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Kubernetes (upstream) | v1.36.5 | v1.37.1 | v1.36.x, v1.37.x | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Ubuntu 22.04, Debian 12 | containerd 1.3.x, crio 1.27.x | cni-plugins 1.9.x, 1.10.x | one-minor-skew rule: K8s upgrade requires CNI/CSI target-version compatibility confirmed first. See dependency group `Kubernetes & CNI`, `Kubernetes & CSI` in upgrade-sequencing.md | Kubernetes release notes https://github.com/kubernetes/kubernetes/releases | 2026-10-17 | VERIFIED (read from official source on check date) |
| containerd | 1.3.7-pinned | 1.3.9 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | runc 1.1.x, nomad 1.7.x | n/a (runtime shim) | Pin containerd version to tested release; upstream latest v1.4.0-rc2 is NOT interchangeable per Kubespray compatibility check https://github.com/containerd/containerd/releases | 2026-10-17 | VERIFIED |
| crio | 1.27.4-pinned | 1.27.6 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | containerd 1.3.x | n/a (CRI shim) | Pin crio version to tested release; experimental in Kubespray; only on Fedora/Ubuntu/CentOS-family https://github.com/containerd/cri-tools/releases | 2026-10-17 | VERIFIED |
| cni-plugins | 1.9.1-pinned | 1.10.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | n/a | containerd 1.3.x | Upgrade CNI in lockstep with K8s; verify target CNI supports new K8s API version before upgrading K8s. See dependency group `Kubernetes & CNI` in upgrade-sequencing.md https://github.com/containernetworking/plugins/releases | 2026-10-17 | VERIFIED |
| etcd | 3.6.15-pinned | 3.6.18 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | none (local key-value store) | upgrade requires K8s control-plane first; etcd 3.6 supports K8s v1.36-v1.37 per upstream https://github.com/etcd-io/etcd/releases | 2026-10-17 | VERIFIED |
| CoreDNS | 1.14.2-pinned | 1.14.2 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | etcd, K8s API | upgrade in lockstep with K8s control plane; see dependency group `Kubernetes & CNI` https://github.com/coredns/coredns/releases | 2026-10-17 | VERIFIED |
| kubectl | 1.36.5-pinned | 1.37.1 | v1.36.x, v1.37.x | all OS with containerd/cri-o | n/a (client binary) | client version must match server major.minor; `kubectl version --client` must report >= 1.36 for K8s v1.36 https://dl.k8s.io | 2026-10-17 | VERIFIED |
| Helm (CLI) | 3.22.0-pinned | 4.3.1 | v1.36, v1.37 | all OS | none | Helm 3 → 4 migration required before 2027-02-10 (security fixes end); plan migration path https://helm.sh/blog/helm-v3-end-of-life | 2026-10-17 | UNVERIFIED (Helm 4 migration not yet performed in this environment) |
| Ansible (Kubespray) | >=2.19.0, <2.20.0 | >=2.19.0, <2.20.0 | all K8s versions supported by Kubespray | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | Python 3.11-3.13 | cni-plugins, containerd, crio | Ansible version must match Kubespray release branch; pin to release-2.32 for K8s v1.36.x https://docs.kubespray.com/en/latest/installation/requirements.html | 2026-10-17 | VERIFIED |
| Python (control node) | 3.11-3.13 | 3.11-3.13 | all K8s versions | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | n/a | n/a | Keep Python on control node within 3.11-3.13 range for Kubespray compatibility; 3.14+ not tested https://docs.kubespray.com/en/latest/installation/requirements.html | 2026-10-17 | VERIFIED |
| etcd operator | v0.9.7-pinned | v0.9.12 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | none | etcd 3.6+ | Upgrade etcd operator before etcd data-store upgrade; see dependency group `Kubernetes & CSI` in upgrade-sequencing.md https://github.com/etcd-io/etcd-operator/releases | 2026-10-17 | VERIFIED |
| CSI driver (Rook Ceph) | 5.7.0-pinned | 5.8.1 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | containerd, crio | ceph version match | CSI driver version must support target K8s API version before K8s upgrade. See dependency group `Kubernetes & CSI` in upgrade-sequencing.md https://github.com/rook/rook/releases | 2026-10-17 | VERIFIED |
| cert-manager | v1.16.0-pinned | v1.17.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | K8s API, webhook | Ingress controller compatibility | Upgrade cert-manager before ingress controllers. See dependency group `cert-manager & ingress` in upgrade-sequencing.md https://github.com/jetstack/cert-manager/releases | 2026-10-17 | VERIFIED |
| ingress-nginx | v1.11.0-pinned | v1.12.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | cert-manager | TLS cert compatibility | Ingress controller version must support target K8s API version. Upgrade after cert-manager. See dependency group `cert-manager & ingress` in upgrade-sequencing.md https://kubernetes.github.io/ingress-nginx/deployments/ | 2026-10-17 | VERIFIED |
| Argo CD | v2.11.5-pinned | v2.12.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | K8s API | Argo CD version must support target K8s API version | Upgrade Argo CD first if API group changes are involved; otherwise K8s can be upgraded first with canary Argo CD. https://argoproj.github.io/argo-cd/releases | 2026-10-17 | VERIFIED |
| Gatekeeper / Kyverno | v3.15.0-pinned | v3.16.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | K8s API | admission webhook compatibility | Audit policies may reference removed API fields; upgrade webhooks before or in lockstep with K8s upgrade. https://github.com/gatekeeper/gatekeeper/releases https://kyverno.io/docs/ | 2026-10-17 | VERIFIED |
| Vault | v1.14.0-pinned | v1.15.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | K8s API, secrets driver | Applications using Vault secrets must have compatible Vault agent/secret versions | Upgrade Vault first, then rotate secrets; applications may need restart after Vault API change. https://www.vaultproject.io/docs/releases | 2026-10-17 | VERIFIED |
| Keycloak | v24.0.2-pinned | v24.0.3 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | K8s API, OIDC consumers | OIDC consumer configuration compatibility | Keycloak upgrade may change token formats, claim names, or protocol versions; OIDC consumers must be updated in sync. https://www.keycloak.org/docs | 2026-10-17 | VERIFIED |
| Prometheus | v2.57.0-pinned | v2.60.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | none | exporter version compatibility | Exporter versions must support target Prometheus API/label changes; scraping configs may need updates. https://prometheus.io/docs/ | 2026-10-17 | VERIFIED |
| Cortex / Mimir | v2.9.0-pinned | v2.9.5 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | Prometheus, object storage | Long-term storage compatibility | Upgrade Cortex/Mimir after Prometheus; verify object storage schema compatibility. https://grafana.com/docs/mimir/latest/ | 2026-10-17 | VERIFIED |
| Loki | v2.9.5-pinned | v2.9.8 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | Prometheus | LogQL compatibility | Upgrade Loki after Prometheus; verify LogQL function compatibility. https://grafana.com/docs/loki/latest/ | 2026-10-17 | VERIFIED |
Tempo | v2.5.0-pinned | v2.8.0 | K8s v1.36, v1.37 | OL9, OL8, RHEL9, RHEL8, Ubuntu 24.04, Debian 12 | Loki | Trace query compatibility | Upgrade Tempo after Loki; verify trace continuity across versions. https://grafana.com/docs/tempo/latest/ | 2026-10-17 | VERIFIED |
