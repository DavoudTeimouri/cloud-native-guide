# Repository and Registry Bootstrap (TASK 006)

## 1. Purpose
Define the Lab repository and registry architecture, integrating the existing two-tier design (`architecture/two-tier-repository-registry.md`), and the minimum bootstrap artifacts needed before Kubernetes deployment. All figures are placeholders pending the infrastructure inventory.

## 2. Two-tier design (existing, P11.2)
- **External Upstream layer**: controlled Internet egress, allowlisted upstreams, scheduled/on-demand sync, checksum and signature verification (cosign, notary), audit logging. Single host permitted to connect to public registries.
- **Internal Repository/Registry Manager**: Nexus (OS packages, artifacts, Helm charts), Harbor (OCI container images). Stable internal DNS endpoints. No direct public Internet access from internal nodes.
- **Trust boundary**: Internal nodes have no outbound Internet. All artifact retrieval flows through the Internal Repository/Registry Manager, which syncs from External Upstream.

This design is **not** full air-gap readiness. It assumes a connected staging path for artifact acquisition, with controlled transfer into the offline environment.

## 3. Network and endpoint requirements
| Endpoint | Service | Internal DNS | TLS | Auth | Notes |
|---|---|---|---|---|---|
| Nexus | Repository Manager | `<NEXUS_INTERNAL>` | Yes | Yes | RPM, deb, PyPI, npm, Helm |
| Harbor | Container Registry | `<HARBOR_INTERNAL>` | Yes | Yes | OCI images, project-based access |
| External Upstream host | Sync/proxy host | `<UPSTREAM_INTERNAL>` | Yes | — | Sole host with public egress |

Firewall: Internal nodes → Nexus/Harbor (443, 8081 for Nexus) only. Internal nodes → public Internet: denied.

## 4. Bootstrap dependency problem
**The chicken-and-egg problem**: Harbor and Nexus are themselves container images / services that need to run somewhere, but Kubernetes (where they'd run) needs images pulled from a registry to bootstrap.

**Safe bootstrap approach (no air-gap assumption)**:
1. Bootstrap a minimal bootstrap node (bare metal or VM) with OS from local media / internal mirror.
2. On the bootstrap node, run a lightweight local registry (e.g., Docker distribution or a minimal Harbor) populated from the External Upstream host via `skopeo`/`docker pull` → `docker push` over the internal network.
3. Use that local registry to pull images for Kubespray control-plane bootstrap (kube-apiserver, etcd, CoreDNS, Cilium, containerd images).
4. Once Kubernetes is up, deploy Harbor and Nexus into the management cluster (or on dedicated VMs) as the permanent internal registry/repository.
5. Point containerd on all nodes at Harbor; point package managers at Nexus.
6. Decommission the temporary bootstrap registry after Harbor/Nexus are operational.

Do not assume a complete air gap. The connected staging path is required for initial artifact acquisition.

## 5. Minimum Lab bootstrap artifacts (before Kubernetes deployment)
- OS images (Oracle Linux 9, Ubuntu 22.04/24.04) with cloud-init or kickstart, on the internal mirror.
- Container images for Kubespray control-plane: kube-apiserver, kube-controller-manager, kube-scheduler, etcd, kube-proxy, CoreDNS, Cilium, containerd — pinned to `compatibility/version-matrix.md` versions.
- Kubespray release-2.32 inventory and playbooks (`automation/ansible/`).
- SSH keys and BMC/IPMI access credentials for out-of-band installation.
- Internal DNS and NTP reachable from the bootstrap segment.
- TLS certificates (self-signed for Lab, or issued by internal CA) for Nexus/Harbor/Kubernetes API VIP.

## 6. Storage capacity
- Nexus: disk for RPM/deb/PyPI/Helm cache; plan for growth, retention policy.
- Harbor: disk for OCI image layers; plan for image count and retention; garbage collection configured.
- Both: underlying storage (disk or S3), PostgreSQL for Harbor, TLS certs, token service.

## 7. Open questions
1. Is there an existing internal mirror/registry the Lab can reuse, or must Nexus/Harbor be built from scratch?
2. What is the internet egress policy — direct, proxy, or restricted?
3. Who controls internal DNS and TLS certificate issuance for the Lab?
4. Is a bootstrap node available, or must one be provisioned from physical media?
