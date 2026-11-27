# Section 10: Upgrade Sequencing and Dependency Graph

## Upgrade Dependency Model

The following dependency groups define explicit prerequisites that must be satisfied before upgrading any component in the group. Where upstream/downstream compatibility differs, the dependency is noted as directional — a universal order is not imposed.

### Dependency Groups

| Dependency Group | Prerequisite | Direction | Notes |
|-----------------|--------------|-----------|-------|
| **Kubernetes & CNI** | CNI plugin version must support the target Kubernetes API version. | CNI → Kubernetes | Upgrade CNI first, or ensure target CNI supports the new K8s version before upgrading K8s. |
| **Kubernetes & CSI** | CSI driver version must support the target Kubernetes API version. | CSI → Kubernetes | Same pattern as CNI; CSI operators often block K8s upgrade if unsupported. |
| **Kubernetes & Rancher** | Rancher version must support the target Kubernetes version. | Rancher → Kubernetes | Rancher upgrade may be required before K8s upgrade; check Rancher release notes for supported K8s versions. |
| **Ceph & Rook** | Rook operator version must support the target Ceph version; Ceph version must be supported by the Rook release. | Rook → Ceph (operator first) | Upgrade the Rook operator before changing `cephVersion.image`; both have hard version constraints. |
| **cert-manager & ingress** | Ingress controller version must support the target cert-manager API changes; cert-manager version must support the ingress controller's API requirements. | bidirectional — verify both directions | Typically cert-manager is upgraded first, then ingress, but check release notes for each direction. |
| **Vault & dependent applications** | Applications using Vault secrets must have compatible Vault agent/secret versions; API changes must not break secret rotation. | Vault → dependent apps | Upgrade Vault first, then rotate secrets; applications may need restart after Vault API change. |
| **Keycloak & OIDC consumers** | OIDC consumer configuration must be compatible with the target Keycloak version (realm settings, client registration). | Keycloak → OIDC consumers | Keycloak upgrade may change token formats, claim names, or protocol versions; OIDC consumers must be updated in sync. |
| **Prometheus & exporters** | Exporter versions must support the target Prometheus API/label changes; scraping configs may need updates. | exporters → Prometheus | Upgrade exporters first, or ensure target Prometheus version supports the existing exporter versions. |
| **Argo CD & Kubernetes API versions** | Argo CD version must support the target Kubernetes API version (custom resources, API group changes). | Argo CD → Kubernetes | Upgrade Argo CD first if API group changes are involved; otherwise Kubernetes can be upgraded first with canary Argo CD. |
| **Gatekeeper/Kyverno & admission webhook dependencies** | Admission webhook versions must support the target Kubernetes API version; policy definitions may break on API changes. | Gatekeeper/Kyverno → Kubernetes | Audit policies may reference removed API fields; upgrade webhooks before or in lockstep with K8s. |

### Recommended Upgrade Sequence (Illustrative — Version‑Dependent)

The sequence below respects the dependency groups above. **Each step must be verified against the actual installed versions before execution.** Parallelizable tasks are marked; serialized tasks must follow the order shown.

| Step | Component(s) | Prerequisites | Parallelizable? | Gates |
|------|--------------|---------------|-----------------|-------|
| 1 | **CNI plugins** (e.g., Cilium, Calico) | Target CNI version supports the current K8s version. | Yes — across different node pools | CNI version matrix check; no pending CNI-managed workloads. |
| 2 | **CSI drivers** (e.g., Rook/Ceph CSI, NetApp, EBS) | Target CSI version supports the current K8s version. | Yes — across different storage families | CSI version matrix check; no CSI‑backed pods in `Terminating`. |
| 3 | **Rook operator** (if managing Ceph/CSI) | Rook version supports the current Ceph version. | Yes — operator upgrade is independent of data-plane. | Operator release notes; supported Ceph version confirmed. |
| 4 | **Ceph daemons** (via Rook) | Rook operator at target version; Ceph upgrade path documented. | No — serialized per daemon type (mon → mgr → osd → mds → rgw). | Ceph upgrade notes; OSD map snapshot taken. |
| 5 | **Kubernetes control plane** | All CNI and CSI versions support the target K8s version; Rook operator upgraded. | No — control-plane first, then workers. | Compatibility sign‑off; offline artifacts pull‑verified. |
| 6 | **Kubernetes workers** | Control plane at target version; all pods drained per node. | Yes — across independent worker nodes | One node at a time; PDB compliance verified between nodes. |
| 7 | **Rancher** | Target K8s version supported by Rancher release notes. | Yes — if multiple Rancher instances. | Rancher supported versions matrix. |
| 8 | **cert-manager** | Ingress controller version compatible with target cert-manager API. | Yes — across multiple cert-manager installations. | Release notes; API compatibility check. |
| 9 | **Ingress controllers** (F5, ingress‑nginx) | cert-manager at target version; ingress API changes confirmed. | Yes — across different ingress families. | Controller release notes; TLS cert compatibility. |
| 10 | **Vault** | Dependent applications verified against new Vault API. | Yes — if isolated Vault instances. | Application compatibility; secret rotation plan. |
| 11 | **Keycloak** | OIDC consumers updated to target Keycloak version. | Yes — if multiple Keycloak realms/instances. | OIDC config review; token format compatibility. |
| 12 | **Prometheus stack** | Exporter versions compatible with target Prometheus. | Yes — across exporter types. | Exporter version matrix; scrape config updates. |
| 13 | **Argo CD** | Target K8s API version supported by Argo CD. | Yes — if multiple Argo CD instances. | Argo CD release notes; API group checks. |
| 14 | **Gatekeeper / Kyverno** | Target K8s API version supported by admission webhooks. | Yes — if multiple policy engines. | Policy audit; no failing validating webhooks. |

### Parallelizable vs Serialized Tasks

- **Parallelizable**: CNI upgrade across node pools, CSI driver upgrades across storage families, cert-manager across installations, Vault across isolated instances, Keycloak across realms, Prometheus exporters, Argo CD instances, Gatekeeper/Kyverno instances.
- **Serialized**: Kubernetes control‑plane upgrade (must be one at a time), Kubernetes worker nodes (one at a time with PDB checks), Ceph daemon upgrade (fixed order: mon → mgr → osd → mds → rgw), Rook operator → Ceph sequence (operator first, then Ceph), Gatekeeper/Kyverno audit after K8s API changes.

### Directional Dependency Note

> **Do not impose a universal order where upstream compatibility requirements differ.**
> Example: Upgrading Kubernetes before CNI is only safe if the new CNI version is installed *before* or *concurrently* with the K8s upgrade. Always verify the target CNI/CSI supports the target K8s version before proceeding. The dependency graph above marks the direction; the actual sequence must be adapted to the installed component versions.

---

## Upgrade Sequence Summary Diagram (Text-Based)

```
CNI → K8s control plane → K8s workers → Rancher
  ↑               ↑
CSI ──┘               ↑
  ↑                   ↑
Rook → Ceph (mon→mgr→osd→mds→rgw)
  ↑
cert-manager → Ingress
  ↑
Vault → Keycloak → OIDC consumers
  ↑
Prometheus → Exporters
  ↑
Argo CD → K8s API versions
  ↑
Gatekeeper/Kyverno → K8s API versions
```
