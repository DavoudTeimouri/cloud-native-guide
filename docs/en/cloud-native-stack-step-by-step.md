# Cloud-Native Stack — Step-by-Step Deployment Guide (English)

Single ordered flow for an enterprise-ready, on-premises or air-gapped cloud-native stack. Every step lists purpose, prerequisites, actions, and validation. All versions are pinned from `compatibility/version-matrix.md` (check date 2026-10-26). All paths are relative to the repository root.

```
Order of work: Step 00 -> Step 01 -> ... -> Step 10. Do not start step N+1 until step N validation passes.
```

## Repo facts used by this guide

| Item | Value | Source |
|---|---|---|
| OS | Oracle Linux 9, Ubuntu Server 24.04 LTS | `operating-systems/host-configuration.md` |
| Orchestrator | Kubernetes via Kubespray v2.32.0 (branch `release-2.32`) | `kubespray/kubespray-deployment.md` |
| Kubernetes | 1.36.5 (Kubespray default), floor 1.34.0 | `compatibility/version-matrix.md` |
| Control node | Python 3.12, ansible-core 2.19.x, Ansible 12 | `compatibility/version-matrix.md` |
| Container runtime | containerd 2.3.7 | `compatibility/version-matrix.md` |
| CNI | Cilium 1.20.3, kube-proxy replacement strict, Hubble | `compatibility/version-matrix.md` |
| etcd | 3.6.15, stacked on control plane | `compatibility/version-matrix.md` |
| Helm | 3.22.0 (security fixes end 2027-02-10) | `compatibility/version-matrix.md` |
| Storage | Ceph Tentacle 20.2.4 (cephadm dedicated hosts) or Rook v1.21.0 (in-cluster) | `compatibility/version-matrix.md` |
| Ingress | F5 NGINX IC chart 2.8.0 + NGINX Gateway Fabric + Envoy Gateway v1.9.2 | `compatibility/version-matrix.md` |
| Retired | `kubernetes/ingress-nginx` — do not adopt | `compatibility/version-matrix.md` |
| MetalLB | v0.16.1 | `compatibility/version-matrix.md` |
| Management cluster | Rancher v2.15.2, Argo CD v3.5.6, Keycloak 26.8.1 | `compatibility/version-matrix.md` |
| Secrets | Vault v2.2.0 (chart 0.34.1), cert-manager v1.21.2, External Secrets v2.13.0 | `compatibility/version-matrix.md` |
| Backup | Velero v1.18.4 | `compatibility/version-matrix.md` |
| GitLab CE | 19.5.1 | `compatibility/version-matrix.md` |
| Harbor | v2.15.4; Nexus release-3.97.1-02 | `compatibility/version-matrix.md` |
| Gate rules | No phase starts until previous phase acceptance passes; destructive actions need explicit `yes` | README.md Working rules |

Provisional CIDRs (verify against site plan before build; full port matrix: `network-matrix/network-communication-matrix.md`):
- mgmt 10.10.0.0/24, control-plane 10.20.0.0/24, pod 10.30.0.0/16, service 10.32.0.0/16, storage 10.40.0.0/24 + 10.41.0.0/24, gpu 10.50.0.0/24, dmz 10.60.0.0/24.

ADRs that govern choices: `decisions/ADR-0001..ADR-0031` (control-plane topology ADR-0002/0003, CNI ADR-0006, ingress ADR-0007, storage ADR-0008/0029, secrets ADR-0016/0025, Kubespray multi-release ADR-0026, external LB ADR-0028, no mesh initially ADR-0030).

Validation commands (run offline from repo root):
```
python3 tests/test_repo_tools.py   # 8 repository self-checks
python3 scripts/check_links.py     # 0 broken links required
python3 scripts/validate_catalog.py
```

---

<a id="step-00"></a>
## Step 00 — Overview & architecture {#step-00}

**Purpose**: Confirm target topology, failure domains, and decision records before any infrastructure is touched.

**Prerequisites**: Stakeholder agreement on cluster count (management cluster + application clusters), site network segments, and air-gap requirement.

**Actions**:
1. Read `docs/architecture/00-overview.md` — layers (physical, offline distribution, automation, identity & secrets, storage, Kubernetes, GitOps, management) and control/data plane split.
2. Read `docs/architecture/02-deployment-topology.md` and `docs/architecture/03-failure-domains.md` — node roles, failure domains, and the management cluster / application cluster split (no shared workers; ADR-0010/ADR-0011).
3. Pin versions in `compatibility/version-matrix.md`; every row used in a deploy must be `VERIFIED` or `PINNED` with a source URL and check date.
4. Record applicable ADRs from `decisions/` as accepted for this site.

**Validation**:
- Topology diagram and CIDR table reviewed against the site plan.
- Every version this guide will use is listed as VERIFIED/PINNED in `compatibility/version-matrix.md`.

**Next**: Step 01 (`#step-01`).

<a id="step-01"></a>
## Step 01 — Offline artifact infrastructure

**Purpose**: Stand up internal artifact distribution so no node needs outbound internet at runtime (Harbor for images/OCI charts, Nexus for packages, GitLab for source, file mirrors for OS packages and Helm charts).

**Prerequisites**: Step 00 complete; VMs or bare-metal hosts for Harbor/Nexus/GitLab; internal CA for TLS.

**Actions**:
1. Deploy Harbor v2.15.4 (images and OCI charts) with its CA certificate trusted on every node.
2. Deploy Nexus release-3.97.1-02 (RPM/DEB/APT mirrors).
3. Deploy GitLab CE 19.5.1 for source and pipeline storage.
4. Mirror all artifact categories from `offline-artifacts/artifact-matrix.md`: Kubernetes components, Cilium/Calico images, containerd, add-on charts (metrics-server, cert-manager, etc.), Kubespray collections.
5. Verify with `skopeo inspect` and `apt-get update` / `dnf repolist` using internal sources only.
6. Distribute the Harbor CA cert to `/etc/ssl/certs/` on every target node.

**Validation**:
- A clean node installs packages and pulls images from internal mirrors with no internet.
- `skopeo inspect docker://harbor.internal/<image>` succeeds from every node.
- Harbor CA is trusted: `curl -sf https://harbor.internal/` returns 200.

**Next**: Step 02 (`#step-02`).

<a id="step-02"></a>
## Step 02 — Foundational infrastructure

**Purpose**: Provide DNS, NTP, internal PKI, load balancing, and firewall rules before cluster nodes are provisioned.

**Prerequisites**: Step 01 complete (internal registry reachable); network segments allocated (see provisional CIDRs above).

**Actions**:
1. DNS: CoreDNS with forwarders; `management.internal`, `harbor.internal`, `nexus.internal`, `gitlab.internal`, control-plane VIP resolvable from all nodes.
2. NTP: chrony on all nodes; clock skew < 100 ms across the cluster.
3. PKI: internal CA; certs for `management.internal`, registry, Vault, identity.
4. Load balancer: keepalived + HAProxy (L4) and Nginx (L7) on host network via Docker Compose; active/active edge with two VIPs balanced by router ECMP/BGP (single VRRP VIP is active/standby, not active/active — ADR-0028).
5. Firewall: generate rules from `network-matrix/port-requirements.md`; verify with `nmap`/`ss` from allowed and denied hosts.

**Validation**:
- Forward and reverse DNS resolve for all service names.
- `chronyc tracking` shows synchronized on every node.
- CA certificate distributed and trusted on every node.
- LB VIP fails over between nodes.
- Firewall matrix evidenced: allowed ports open, denied ports blocked.

**Next**: Step 03 (`#step-03`).

<a id="step-03"></a>
## Step 03 — OS baseline (per host)

**Purpose**: Harden every node: repo config, sysctl, kernel modules, security baseline, local accounts, break-glass access, TLS trust, logging agents.

**Prerequisites**: Step 02 complete (DNS, NTP, internal CA, package mirrors reachable).

**Actions**:
1. Select OS per host: Oracle Linux 9 (kernel 5.14, preferred) or Ubuntu Server 24.04 LTS (kernel 6.8+ GA / 6.11+ HWE). OL8 and Ubuntu 20.04 are below Kubespray's 4.19 minimum and are not supported.
2. Apply the host baseline from `operating-systems/host-configuration.md`: admin user, SSH port and password policy, sudo, timezone, locale, NTP, DNS, search domain, kernel arguments, swap off, transparent huge pages, max pods, file descriptors, SELinux/AppArmor, firewall backend, audit retention, unattended updates, CA bundle.
3. Local accounts only — nodes are never joined to a directory (ADR-0015).
4. Install Python 3 and containerd prerequisites; confirm `ansible all -m ping` returns pong from the control node.
5. Install break-glass local account; verify it works with the directory unreachable.

**Validation**:
- `ansible all -m setup` idempotent (0 changed on second run).
- Break-glass account authenticates with directory unreachable.
- `auditd`/journald shipping verified; package install works offline.

**Next**: Step 04 (`#step-04`).

<a id="step-04"></a>
## Step 04 — Container engine and offline images

**Purpose**: Install containerd 2.3.7 and configure registry mirrors so all images resolve to the internal Harbor.

**Prerequisites**: Step 03 complete (OS baseline, containedor repo reachable).

**Actions**:
1. Install containerd 2.3.7 (Kubespray-managed, pinned; do not substitute containerd 2.4.x).
2. Configure `containerd_registries_mirrors`: docker.io and the internal registry `{{ registry_addr }}` with basic-auth header.
3. Stage all required images on the connected staging host and load them into internal Harbor: Kubernetes components (kube-apiserver, kube-controller-manager, kube-scheduler, kube-proxy, etcd, coredns, pause), CNI (Cilium/Calico, Hubble, operator), containerd, add-ons (metrics-server, local-path-provisioner).
4. Verify each image with `skopeo inspect` against the internal registry.

**Validation**:
- `crictl info` reports containerd 2.3.7 on every node.
- `skopeo inspect docker://harbor.internal/<image>` succeeds for every required image.
- containerd pulls from the internal mirror when docker.io is unavailable.

**Next**: Step 05 (`#step-05`).

<a id="step-05"></a>
## Step 05 — Storage — Ceph

**Purpose**: Provide block and file storage: cephadm on dedicated storage hosts (preferred) or Rook-Ceph v1.21.0 in-cluster.

**Prerequisites**: Step 04 complete (containerd, internal registry); storage hosts provisioned with dedicated OSD disks (local SSD for etcd, dedicated NVMe for Ceph OSD DB/WAL; never shared virtual disks for Ceph OSDs in VMs).

**Actions — cephadm dedicated-host model (ADR-0008/0029)**:
1. One node group per role: MON, MGR, OSD, MDS, RGW; no role shares a host.
2. Bootstrap cephadm on the first MON; add every role host with its label; apply the service spec; wait for `HEALTH_OK`.
3. Create pools and StorageClasses for the application cluster.

**Actions — Rook-Ceph in-cluster alternative**:
1. Deploy Rook operator v1.21.0 (chart 1.21.0) from the internal Helm repository.
2. Read the Ceph version paired with Rook v1.21.0 from its release notes before setting `cephVersion.image` (the most common Rook upgrade failure cause).
3. Use the ceph-csi image tag named in Rook v1.21.0's `cluster.yaml`.

**Validation**:
- `ceph -s` shows `HEALTH_OK`; MON/MGR/OSD/MDS/RGW roles healthy.
- StorageClass created; a test PVC binds and a pod can write to it.
- Squid 19.2.7 is EOL 2026-10-31 — do not start a new deployment on Squid; use Tentacle 20.2.4.

**Next**: Step 06 (`#step-06`).

<a id="step-06"></a>
## Step 06 — Kubernetes via Kubespray v2.32.0

**Purpose**: Deploy the application cluster: 3 control-plane nodes with stacked etcd, 3+ workers, Cilium CNI with kube-proxy replacement, v1.36.5.

**Prerequisites**: Steps 01–05 complete (mirrors, OS baseline, containerd, storage, DNS/NTP, internal registry).

**Actions**:
1. Checkout Kubespray release-2.32 on the control node; pin `kubespray/VERSION` to release-2.32; Python venv 3.11–3.13, ansible-core 2.19.x, Ansible 12.
2. Create `inventory/<cluster>/hosts.ini` with groups `control-plane` (3), `etcd` (same 3 hosts, stacked), `k8s-node` (3+ workers), optional `kube_gpu` for GPU workers (NVIDIA H100/H200, MIG for production multi-tenancy, time-slicing dev-only).
3. Write `inventory/<cluster>/group_vars/k8s_cluster/k8s-cluster.yml`:
   - `kube_version: v1.36.5`
   - `kube_network_plugin: cilium`, `kube_proxy_mode: ""`
   - `kube_pods_subnet: 10.30.0.0/16`, `kube_service_addresses: 10.32.0.0/16`
   - `k8sServiceHost: <control-plane VIP>`, `k8sServicePort: 6443`
   - Cilium: tunneling mode vxlan, Hubble enabled, IPAM cluster-pool, operator image overridden to `{{ registry_host }}/cilium/operator-generic:v1.20.3`
4. Write `inventory/<cluster>/group_vars/all/offline.yml`: `kube_image_repo`, `gcr_image_repo`, etc. set to `{{ registry_host }}`; `github_url`, `dl_k8s_io_url`, etc. pointed at the file mirror; containerd registry mirrors; `cilium_install_extra_flags: --repository {{ files_repo }}/helm.cilium.io/`.
5. Run preflight: `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml --syntax-check`; `ansible -i inventory/<cluster>/hosts.ini all -m ping`; `ansible-playbook ... cluster.yml -b --check --diff --limit control-plane`.
6. Deploy control plane one node at a time (`--limit k8s-cp-1`, then cp-2, cp-3) to preserve etcd quorum; verify `kubectl get nodes` Ready after each.
7. Deploy workers: `ansible-playbook ... cluster.yml -b --limit k8s-node`; verify all nodes Ready.
8. Install Cilium 1.20.3 chart from internal Helm repo with `cilium_install_extra_flags` mirror; verify `cilium status`: KubeProxyReplacement True, `kubeProxyReplacementError: none`, Cluster CIDR 10.30.0.0/16, Service CIDR 10.32.0.0/16; run `cilium connectivity test`.

**Validation**:
- `kubectl get nodes` — all nodes Ready, version v1.36.5.
- `kubectl get --raw='/readyz?verbose'` — all ok.
- etcd endpoint healthy on all 3 members.
- Cilium connectivity test passes; kube-proxy replaced.
- CoreDNS running; DNS resolution from a test pod succeeds.

**Next**: Step 07 (`#step-07`).

<a id="step-07"></a>
## Step 07 — Management cluster

**Purpose**: Build a dedicated management cluster (3 control-plane + 3 infra workers, no application workloads) running Rancher, Argo CD, Keycloak, Vault.

**Prerequisites**: Step 06 complete (application cluster healthy); `management.internal` DNS and TLS certs ready.

**Actions**:
1. Deploy a second Kubespray cluster (`inventory/mgmt/hosts.ini`, release-2.32) with its own control plane and worker pool; do not share nodes with application clusters (ADR-0010/ADR-0011).
2. Install Rancher v2.15.2 (chart 2.15.2 from releases.rancher.com stable index) — management plane only.
3. Install Argo CD v3.5.6 (chart 10.10.5) + ApplicationSet chart 1.12.1 for GitOps (ADR-0014: GitLab CI builds, Argo CD declares cluster state).
4. Install Keycloak 26.8.1 as OIDC/LDAP broker for Rancher, Harbor, GitLab, Argo CD, Vault, Kubernetes API (no host-level AD join).
5. Install Vault v2.2.0 on dedicated hosts outside every cluster (chart 0.34.1, app 2.0.4); OpenBao v2.7.1 only if legal rejects the BSL (ADR-0016/0025).

**Validation**:
- Rancher API reachable; no app workloads scheduled on management workers.
- Argo CD syncs a sample application from GitLab.
- Keycloak issues tokens; OIDC login works for Rancher/Harbor/Argo CD.
- Vault seals/unseals with offline shares; backup snapshot created and verified.

**Next**: Step 08 (`#step-08`).

<a id="step-08"></a>
## Step 08 — Traffic edge (LB and ingress)

**Purpose**: External active/active edge plus in-cluster load balancing and L7 ingress.

**Prerequisites**: Step 07 complete (management cluster reachable); MetalLB chart mirrored to internal registry.

**Actions**:
1. External edge: HAProxy (L4, active health checks) + Nginx (L7, TLS) on host network via Docker Compose; Keepalived with unicast peers; Tier 2 = two VIPs balanced by router ECMP/BGP; Tier 3 = DNS/GSLB.
2. In-cluster: MetalLB v0.16.1 pool (e.g. 10.61.0.10–10.61.0.30).
3. Ingress: install F5 NGINX Ingress Controller chart 2.8.0 (`nginx-ingress` 2.8.0) with offline image digests, `controller.service.type=LoadBalancer`, Gateway API enabled, snippets disabled (security hardening). Install NGINX Gateway Fabric 2.8.0 and Gateway API CRDs v1.6.3.
4. Do NOT install `kubernetes/ingress-nginx` — retired March 2026, no security fixes.

**Validation**:
- Edge VIP failover between nodes; `curl -vk https://<ingress-vip>/healthz` returns 200 with valid certificate chain.
- MetallB assigns a VIP to the ingress service.
- `kubectl get gatewayclass` lists nginx; `kubectl get gateway,httproute -A` works.

**Next**: Step 09 (`#step-09`).

<a id="step-09"></a>
## Step 09 — Platform services and add-ons

**Purpose**: Observability, logging, GitOps delivery, secrets injection, admission policy, runtime detection, GPU support.

**Prerequisites**: Step 08 complete (ingress, Gateway API).

**Actions**:
1. Observability: Prometheus/Grafana/Alertmanager/Thanos; Loki/Fluent Bit for logging.
2. Add-ons (from `addons/platform-addons.md`, exactly the add-ons whose values files exist — a missing chart is reported, never downloaded): cert-manager v1.21.2 (Vault PKI or bootstrap issuer), Metrics Server, VPA (recommendation or auto), Descheduler (dry-run or eviction), external-dns (RFC2136 or CoreDNS etcd), Trivy Operator, OpenTelemetry Collector.
3. Secrets: External Secrets Operator v2.13.0 reading Vault; cert-manager issues workload certs from the internal CA or Vault PKI.
4. Security: Pod Security Standards, OPA Gatekeeper or Kyverno (one policy engine, ADR-0020), Falco runtime detection, Trivy image scanning; Cosign/Syft for image provenance and signing.
5. GPU: NVIDIA DCGM, vLLM for LLM serving (primary), llama.cpp for small/quantized models; MIG for production multi-tenancy.

**Validation**:
- Prometheus targets scrape; Grafana dashboards load; Loki receives Fluent Bit logs.
- cert-manager issues a certificate; ESO injects a secret from Vault into a namespace.
- Trivy Operator scans workloads; Gatekeeper/Kyverno admits or rejects per policy.
- `nvidia-smi` visible on GPU workers; vLLM deployment serves a model.

**Next**: Step 10 (`#step-10`).

<a id="step-10"></a>
## Step 10 — Validation, backup, upgrade, disaster recovery

**Purpose**: Prove the stack is healthy, protect it, and define the ordered upgrade path.

**Prerequisites**: Steps 01–09 complete.

**Actions**:
1. Acceptance: `kubectl get nodes -o json` — all Ready; `kubectl api-versions` non-empty; `kubectl get pods -A` all system pods Running; `etcdctl endpoint health --cluster` healthy; `cilium status` healthy; Ceph `HEALTH_OK`; Velero v1.18.4 backup created and restored in a test namespace.
2. Backup: Velero schedules for cluster resources; Ceph RGW snapshots for object data; `etcd` snapshots as the authoritative control-plane backup.
3. Upgrade: component-by-component via the ordered upgrade walkthrough (`lifecycle/upgrades/upgrade-procedures.md`); gate markers between phases; rollback statement per component; Kubespray release changes follow ADR-0026 (five releases in parallel; oldest leaves when a sixth successor ships).
4. Disaster recovery: `lifecycle/backup/backup-and-dr.md` — control-plane node reset one at a time (preserve etcd quorum), full cluster reset (workers first, then control-plane, one at a time), etcd snapshot restore.

**Validation**:
- `./deploy.sh --dry-run` then `./deploy.sh` succeeds end to end; every phase idempotent.
- `50-verify.sh` acceptance checks pass: nodes, pods, metrics API, Ceph health, cert-manager, Argo CD.
- Rollback procedure tested on a non-production node: kubespray reset + redeploy restores Ready state.
- No secrets in Git (sanitized examples only; `[REDACTED]` placeholders).

**Next**: Step 11 — Day-2 Operations (`journey/step-11-day-2-operations.md`).

**End of guide.** Re-run from Step 00 when any pinned version changes: edit `compatibility/version-matrix.md`, then `python3 scripts/build_site.py` and `python3 scripts/validate_catalog.py`.
