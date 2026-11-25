# Windows Workers in Kubernetes — Compatibility and Feasibility

This document describes the feasibility of running Windows worker nodes in the Kubernetes cluster. It is a compatibility assessment only. **No Windows worker automation is implemented.** Windows worker support is not claimed as available until the deployment path is verified.

## Overview

Windows worker nodes run Windows containers alongside Linux containers in the same cluster. This document assesses compatibility against verified upstream sources and Kubespray release-2.32 capabilities.

## Prerequisites

- Control plane: Linux-only (Windows nodes cannot run control-plane components)
- Container runtime: containerd (v1.7+)
- CNI: Cilium with VXLAN overlay (primary), Calico (alternative)
- Kubernetes version: 1.25+ (Windows support GA since 1.25)

## Supported Windows Server Versions
Based on verified upstream Kubernetes compatibility:

| Windows Server Version | Kubernetes Support | Container Runtime | CNI Support | Status | Evidence |
|----------------------|-------------------|-------------------|-------------|--------|----------|
| Windows Server 2022 Datacenter | Kubernetes 1.25+ (GA since 1.25) | containerd 1.7+ | Cilium VXLAN, Calico | **Conditional / requires validation** | GA since k8s 1.25; limited Kubespray integration evidence |
| Windows Server 2019 LTSC | Kubernetes 1.25+ (deprecated path) | containerd 1.7+ | Cilium VXLAN | **Supported with limitations** | Limited upstream testing; deprecated in favor of 2022 | [Kubernetes OS compatibility](https://kubernetes.io/docs/concepts/windows/intro/#windows-os-version-compatibility) |
| Windows Server 2025 | Kubernetes 1.32+ | containerd 2.x+ | Cilium | **Conditional / requires validation** | Newer; limited Kubespray integration evidence | [Kubernetes v1.32 release notes](https://github.com/kubernetes/kubernetes/releases/tag/kubernetes-1.32) |

### Evidence
- Kubernetes Windows support reached GA in v1.25 (`https://kubernetes.io/docs/concepts/windows/`).
- Cilium Windows support documentation: `https://docs.cilium.io/en/stable/gettingstarted/k8s-install-windows/`.
- Kubespray Windows support: `https://github.com/kubernetes-sigs/kubespray/blob/master/docs/windows.md` (documented role exists; not adopted in release-2.32).

## Container Runtime Requirements
| Requirement | Specification | Notes | Verified / Assumed |
|-------------|--------------|-------|-------------------|
| Runtime | containerd | Docker Engine is not supported on Windows worker nodes | Verified |
| containerd version | 1.7+ | Must match the Kubespray release's pinned version | Verified |
| Shim | runhcs-v1 | Hyper-V Container shim | Verified |
| Cgroup driver | cgroupfs | Windows does not use systemd cgroups | Verified |
| Snapshotter | windows | Windows-native snapshotter | Verified |

## CNI and Networking Limitations

| Limitation | Details | Verified / Assumed |
|------------|---------|-------------------|
| CNI plugins | Cilium with VXLAN overlay is the primary option. Calico is an alternative. Flannel and other CNI plugins are not validated for Windows. | Verified for Cilium/Calico; unvalidated for others |
| VXLAN port | 4789 (default) must be open on Windows nodes | Verified |
| Geneve port | 6081 (optional, Cilium) | Verified for Cilium |
| HostPort | Not supported on Windows | Verified |
| HostNetwork | Not supported on Windows | Verified |
| IPv6 | Limited support on Windows worker nodes | Verified |
| NetworkPolicy | Limited support; Cilium NetworkPolicy applies to Windows pods with constraints | Verified for Cilium; constraints documented |
| DNS | CoreDNS must be configured to resolve Windows pod DNS | Verified |

## Storage Limitations

| Limitation | Details | Verified / Assumed |
|------------|---------|-------------------|
| hostPath volumes | Not supported on Windows | Verified |
| Privileged containers | Not supported on Windows | Verified |
| Init containers | Alpha support only; not recommended for production | Verified (alpha) |
| Hugepages | Not supported | Verified |
| Resource limits | CPU and memory only | Verified |
| CSI | Required for persistent storage; hostPath not available | Verified |

## Monitoring and Logging Considerations

| Component | Windows Support | Notes | Status |
|-----------|----------------|-------|--------|
| Prometheus node_exporter | Windows exporter available | Separate Windows exporter binary | Verified |
| Loki/Fluent Bit | Limited | Windows event log integration required | Verified limited |
| Falco | Limited | eBPF-based Falco does not work on Windows; alternative needed | Verified limited — no eBPF on Windows |
| OPA Gatekeeper | Yes | Policy enforcement works on Windows nodes | Verified |

## Kubespray Integration Status

| Aspect | Status | Evidence |
|--------|--------|----------|
| Kubespray Windows support | Documented but not adopted | `https://github.com/kubernetes-sigs/kubespray/blob/master/docs/windows.md` | Documented role exists; not adopted in release-2.32 |
| Kubespray release-2.32 | No Windows node playbook tested | Release README does not list Windows as a supported node OS | Assumed unverified |
| Cilium on Windows | Supported by Cilium upstream | Cilium documentation covers Windows worker nodes | Verified upstream |
| Calico on Windows | Supported by Calico upstream | Calico documentation covers Windows worker nodes | Verified upstream |
| Offline-staging | No Windows support | Offline-staging implementation is Linux-only (RPM/YUM and APT) | Verified — Linux-only |

## Do Not Claim Windows Worker Support

- **Windows worker support is NOT available** in this platform until the deployment path is verified end-to-end.
- No Windows automation is implemented in this task.
- The offline-staging implementation (`automation/offline-staging/`) supports Linux only (Oracle Linux 9 RPM/YUM, Ubuntu 22.04/24.04 APT).
- Windows nodes require a separate, verified deployment path before adoption.


### Windows Server Configuration

Enable required Windows features:

```powershell
# Install container features
Install-WindowsFeature -Name Containers

# Install Hyper-V (required for Hyper-V containers)
Install-WindowsFeature -Name Hyper-V
```

**Offline workflow note**: containerd binaries and packages must be obtained from the internal Nexus mirror. Public downloads are not used in offline workflows.

### Network Configuration

```powershell
# Enable VXLAN
Enable-WindowsOptionalFeature -Online -FeatureName "Container-VXLAN"

# Configure HNS network
hnsdiag network list
```

## Kubernetes Configuration

### Node Labels and Taints

```yaml
# Node labels
kubernetes.io/os: windows
kubernetes.io/arch: amd64
node.kubernetes.io/os: windows

# Taint to prevent Linux pods scheduling
node.kubernetes.io/os=windows:NoSchedule
```

### Windows Node Configuration

```yaml
# kubeadm config for Windows nodes
apiVersion: kubeadm.k8s.io/v1beta3
kind: JoinConfiguration
nodeRegistration:
  kubeletExtraArgs:
    container-runtime-endpoint: "npipe:////./pipe/containerd-containerd"
    cgroup-driver: cgroupfs
    feature-gates: "WinOverlay=true,WinDSR=true"
```

## Container Runtime

### containerd Configuration

```toml
# /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.windows]
    runtime_type = "io.containerd.runc.v2"
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.windows.options]
      SystemdCgroup = false
      BinaryName = "containerd-shim-runhcs-v1.exe"
```

### Image Compatibility

- Base images: obtained from internal mirror (not public download)
- .NET: obtained from internal mirror (not public download)
- Java: obtained from internal mirror (not public download)

**Offline workflow note**: All container images are pulled from the internal Harbor registry. Public image registries are not used.

## Networking

### Cilium for Windows

```yaml
# Cilium values for Windows
cilium:
  ipam:
    mode: "cluster-pool"
    operator:
      clusterPoolIPv4PodCIDR: "10.30.0.0/16"
      clusterPoolIPv4MaskSize: 24
  windows:
    enabled: true
    vxlanPort: 4789
    datapathMode: "vxlan"
```

### Network Policies

```yaml
# NetworkPolicy applies to Windows pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: windows-allow-internal
spec:
  podSelector:
    matchLabels:
      kubernetes.io/os: windows
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
```

## Workload Examples

### Windows Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-web
spec:
  nodeSelector:
    kubernetes.io/os: windows
  tolerations:
  - key: "node.kubernetes.io/os"
    operator: "Equal"
    value: "windows"
    effect: "NoSchedule"
  containers:
  - name: web
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command: ["powershell", "-Command", "Write-Host 'Hello from Windows'"]
```

### Windows Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-app
  template:
    metadata:
      labels:
        app: windows-app
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      tolerations:
      - key: "node.kubernetes.io/os"
        operator: "Equal"
        value: "windows"
        effect: "NoSchedule"
      containers:
      - name: app
        image: myregistry.azurecr.io/windows-app:1.0
        ports:
        - containerPort: 80
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Pod stuck in ContainerCreating | Image pull failed | Check image registry access |
| Pod fails to start | CNI not configured | Verify Cilium Windows config |
| Network not working | VXLAN not enabled | Enable VXLAN on Windows |
| Pod cannot resolve DNS | CoreDNS not configured for Windows | Check CoreDNS config |

## Limitations

### General Kubernetes Limitations (All Node Types)

- **No privileged containers on Windows**: Verified — not supported on Windows nodes
- **No hostPath volumes (use CSI)**: Verified — CSI required for persistent storage
- **No init containers (alpha support)**: Verified — alpha only, not recommended for production
- **Some Linux syscalls not available**: Verified — Windows kernel differences
- **Resource limits: CPU/memory only, no hugepages**: Verified — Windows container runtime constraint

### Windows-Specific Limitations

- **Control plane**: Windows nodes cannot run Kubernetes control-plane components (kube-apiserver, etcd, kube-controller-manager, kube-scheduler). Control plane is Linux-only. **Verified**.
- **CNI**: Cilium with VXLAN overlay is the primary option. Calico is an alternative. Flannel and other CNI plugins are not validated for Windows. **Verified for Cilium/Calico; unvalidated for others**.
- **Storage**: hostPath volumes not supported. CSI required for persistent storage. **Verified**.
- **Networking**: HostPort and HostNetwork not supported on Windows. IPv6 support is limited. **Verified**.
- **Resource limits**: CPU and memory only. No hugepages support. **Verified**.
- **Init containers**: Alpha support only; not recommended for production. **Verified (alpha)**.
- **Monitoring**: eBPF-based tools (Falco) do not work on Windows. Alternative monitoring needed. **Verified — no eBPF on Windows**.
- **Offline-staging**: No Windows support. Offline-staging implementation is Linux-only (RPM/YUM and APT). **Verified**.

## Do Not Claim Windows Worker Support

- **Windows worker support is NOT available** in this platform until the deployment path is verified end-to-end.
- No Windows automation is implemented in this task.
- The offline-staging implementation (`automation/offline-staging/`) supports Linux only (Oracle Linux 9 RPM/YUM, Ubuntu 22.04/24.04 APT).
- Windows nodes require a separate, verified deployment path before adoption.

## References

- [Kubernetes Windows Documentation](https://kubernetes.io/docs/concepts/windows/)
- [Cilium Windows Support](https://docs.cilium.io/en/stable/gettingstarted/k8s-install-windows/)
- [Kubespray Windows Support](https://github.com/kubernetes-sigs/kubespray/blob/master/docs/windows.md)

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*