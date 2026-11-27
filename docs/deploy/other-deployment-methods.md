# Other Deployment Methods

This page documents deployment methods beyond the standard Kubespray paths
covered in `docs/deploy/choose-cluster-type.md`. Use these when the standard
paths do not fit your environment.

## 1. Rancher-Managed Clusters

**Use when:** You want a central management plane (Rancher) that provisions,
registers, and operates multiple Kubernetes clusters without direct Kubespray
invocation per cluster.

**Components:** Rancher Management Cluster, RKE2 or K3s for application clusters,
Fleet for GitOps.

**Step-by-step:** `docs/management-cluster/rancher/installation-ha.md`

## 2. K3s (Lightweight / Edge)

**Use when:** You are deploying on edge devices, resource-constrained hosts, or
single-node clusters where full Kubernetes is too heavy.

**Prerequisites:**
- One or more Linux hosts (Oracle Linux 9 or Ubuntu 24.04).
- containerd is the default runtime (bundled with K3s).

**Step-by-step:**

```bash
# Server node
curl -sfL https://get.k3s.io | sh -s - server \
  --tls-san <server-ip> \
  --cluster-init

# Agent nodes
curl -sfL https://get.k3s.io | sh -s - agent \
  --server https://<server-ip>:6443 \
  --token <node-token-from-server>
```

```bash
# Verify
kubectl get nodes
kubectl get pods -A
```

## 3. RKE2 (Hardened / Air-Gapped)

**Use when:** You need a hardened, CIS-compliant Kubernetes distribution with
air-gapped installation support.

**Prerequisites:**
- RKE2 binaries downloaded to an internal mirror (Nexus).
- Container images mirrored to internal Harbor.

**Step-by-step:**

```bash
# Install RKE2 from internal mirror
curl -sfL https://get.rke2.io | sh -

# Configure air-gapped registries
mkdir -p /etc/rancher/rke2
cat > /etc/rancher/rke2/config.yaml <<'EOF'
tls-san:
  - <server-ip>
node-ip: <node-ip>
registry: |-
  toml:
    [host."https://harbor.internal"]
      capabilities = ["pull", "resolve", "mirror"]
    [host."https://harbor.internal".mirror]
      endpoint = ["https://harbor.internal"]
EOF

systemctl enable --now rke2-server.service

# Get kubeconfig
cp /etc/rancher/rke2/rke2.yaml ~/.kube/config
chmod 600 ~/.kube/config
```

## 4. Kubeadm (Manual / Educational)

**Use when:** You want full control over every Kubernetes component and are
comfortable troubleshooting manual control-plane bootstrap.

**Prerequisites:**
- containerd installed and configured on all nodes.
- `kubeadm`, `kubelet`, `kubectl` installed from internal repos.
- OS prerequisites from Phase 0 applied.

**Step-by-step:**

```bash
# Control plane
kubeadm init --control-plane-endpoint <lb-ip:6443> \
  --upload-certs \
  --pod-network-cidr=10.30.0.0/16 \
  --service-cidr=10.32.0.0/16

# Workers
kubeadm token create --print-join-command
# Run the printed command on each worker
```

## 5. Kind / Minikube (Local Development)

**Use when:** You need a local Kubernetes cluster on a laptop or CI runner for
development and testing only. Not for production.

```bash
# Kind
kind create cluster --name dev --config kind-config.yaml

# Minikube
minikube start --driver=docker
```

## 6. Path Selection Decision Matrix

| Your situation | Recommended method |
|----------------|-------------------|
| Standard production K8s, internet access | Kubespray (standard) |
| Production K8s, no internet | Kubespray (offline/air-gapped) |
| Bare metal / VMs with cloud-init | Kubespray (bare-metal/cloud-init) |
| Multi-cluster central management | Rancher |
| Edge / resource-constrained | K3s |
| Hardened / CIS / air-gapped | RKE2 |
| Full manual control | Kubeadm |
| Local development / CI | Kind / Minikube |

## 7. After Choosing a Method

Follow the step-by-step guide for your chosen method, then proceed to
Phase 1 validation and Phase 2 (Management Layer).
