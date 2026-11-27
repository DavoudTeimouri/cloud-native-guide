# Choose Cluster Type

After selecting an OS (Phase 0), choose the cluster type and deployment path that
matches your environment. Each path links to its step-by-step deployment guide.

## 1. Standard Kubespray Cluster

**Use when:** You have network access to package repositories and container
registries, and want a standard Kubernetes deployment via Kubespray + Ansible.

| Component | Choice |
|-----------|--------|
| Orchestrator | Kubernetes via Kubespray |
| CNI | Cilium (kube-proxy-free) |
| Load Balancer | Keepalived + HAProxy (edge) |
| Ingress | NGINX Ingress Controller |
| Container Runtime | containerd |

**Step-by-step:** `docs/kubespray/kubespray-deployment.md`

## 2. Bare-Metal / Cloud-Init Cluster

**Use when:** You provision physical or VM hosts via cloud-init and want Kubespray
to configure the OS and cluster on first boot.

**Prerequisites:** cloud-init available on the OS image, DHCP or static IPAM ready.

**Step-by-step:** `docs/kubespray/baremetal-cloudinit-deployment.md`

## 3. Offline / Air-Gapped Cluster

**Use when:** The target environment has no outbound internet access. You must
mirror container images, OS packages, Helm charts, and Python packages to an
internal registry first.

**Prerequisites:** Internal Harbor/Nexus registry, internal package repo, version
pinned artifacts in `offline-artifacts/`.

**Step-by-step:** `docs/kubespray/airgapped-deployment.md`

**Checklist:** `docs/kubespray/offline-deployment-checklist.md`

## 4. Management Cluster (Rancher + Application Clusters)

**Use when:** You want a central management plane (Rancher) that registers and
operates multiple application clusters. The management cluster is deployed
separately and must NOT share worker nodes with application clusters.

**Components:** Rancher Management Cluster, Argo CD (GitOps), Keycloak (OIDC),
Vault (secrets), Harbor (registry).

**Step-by-step:** `docs/management-cluster/rancher/installation-ha.md`

## 5. Storage-First Cluster (Ceph / Rook-Ceph)

**Use when:** You need shared block, filesystem, or object storage as a foundation
before deploying applications.

**Options:**
- **Rook-Ceph:** Operator-managed, in-cluster storage (single-cluster scope).
- **cephadm (external):** Dedicated Ceph hosts outside Kubernetes, CSI integration
  for multi-cluster shared capacity.

**Step-by-step:** `docs/storage/ceph/cephadm-deployment.md`,
`docs/storage/rook-ceph/rook-ceph-deployment.md`

## 6. Path Selection Decision Matrix

| Your situation | Recommended path |
|----------------|------------------|
| Internet access, standard K8s | Path 1 — Standard Kubespray |
| Physical/VM hosts with cloud-init | Path 2 — Bare-Metal / Cloud-Init |
| No outbound internet | Path 3 — Offline / Air-Gapped |
| Multiple clusters, central management | Path 4 — Management Cluster (Rancher) |
| Shared storage foundation needed | Path 5 — Storage-First (Ceph / Rook-Ceph) |
| GPU workers needed | Any path + `gpu-node` inventory group |
| Air-gapped + management cluster | Path 3 + Path 4 (offline artifacts first) |

## 0.7 After Choosing a Path

1. Follow the step-by-step guide for your chosen path.
2. Validate each phase before proceeding to the next.
3. Once the cluster foundation is ready, proceed to Phase 2 — Management Layer.
