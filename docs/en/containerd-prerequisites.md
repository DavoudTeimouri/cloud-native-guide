#containerd Prerequisites

Install and configure containerd as the container runtime for Kubernetes nodes.

## Installation

### RHEL Family

```bash
# Install containerd from internal mirror
dnf install -y containerd.io

# Enable and start containerd
systemctl enable --now containerd

# Verify
crictl version
crictl info
```

### Debian Family

```bash
# Install containerd from internal mirror
apt-get update && apt-get install -y containerd.io

# Enable and start containerd
systemctl enable --now containerd

# Verify
crictl version
crictl info
```

## Configuration

```toml
# /etc/containerd/config.toml
version = 2

[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "harbor.internal/base/pause:3.9"
  max_container_log_line_size = 16384

  [plugins."io.containerd.grpc.v1.cri".containerd]
    snapshotter = "overlayfs"
    default_runtime_name = "runc"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
      runtime_type = "io.containerd.runc.v2"
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
        SystemdCgroup = true

  [plugins."io.containerd.grpc.v1.cri".cni]
    bin_dir = "/opt/cni/bin"
    conf_dir = "/etc/cni/net.d"

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://harbor.internal/library"]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry.k8s.io"]
  endpoint = ["https://harbor.internal/k8s"]

[plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal".tls]
  ca_file = "/etc/containerd/certs.d/harbor.internal/ca.crt"
```

### Verification

```bash
# Validate containerd configuration
containerd --config /etc/containerd/config.toml --validate

# Check service status
systemctl is-active containerd

# Check CRI endpoint
crictl info

# Verify registry mirrors
cat /etc/containerd/certs.d/*/hosts.toml
```

## Offline Workflow

- **No public downloads.** containerd packages and images come from the internal Nexus/Harbor mirror.
- **containerd 2.3.7** is the Kubespray release-2.32 pinned version.
- Registry mirrors point to internal Harbor for docker.io, registry.k8s.io.

## References

- [OS Preparation Guide](os-preparation.md)
- [RHEL Family Procedures](../../operating-systems/rhel-family-procedures.md)
- [Debian Family Procedures](../../operating-systems/debian-family-procedures.md)

---\n*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-25*
