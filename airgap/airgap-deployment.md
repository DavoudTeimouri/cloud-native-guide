# Air-Gap Deployment Architecture

This document describes the air-gap deployment architecture and operational procedures for the Cloud-Native Stack.

## Overview

The platform is designed for **fully air-gapped environments** — no outbound internet connectivity at runtime. All artifacts are mirrored to internal registries and repositories before deployment.

## Air-Gap Principles

1. **Design for Air-Gap First** — Air-gap support is designed into the installation process, not added as an afterthought.
2. **Complete Closure** — All transitive dependencies mirrored (images, charts, packages, binaries, CRDs).
3. **Integrity Verification** — Every artifact verified by digest/signature before import.
4. **No Runtime Internet** — No component requires internet at runtime.
5. **Staging Verification** — Full dry-run on throwaway cluster before production.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Air-Gap Environment                              │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Staging     │    │  Air-Gap     │    │  Production  │              │
│  │  (Connected) │───▶│  Transfer    │───▶│  (Air-Gapped)│              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│        │                   │                   │                        │
│        ▼                   ▼                   ▼                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              Artifact Staging & Verification                     │  │
│  │  1. Pull from upstream                                            │  │
│  │  2. Verify digests/signatures                                      │  │
│  │  3. Push to staging Harbor/Nexus/GitLab                           │  │
│  │ 4. Generate artifact-matrix.md with digests                        │  │
│  │ 5. Export to air-gap media                                         │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Artifact Categories

| Category | Examples | Mirroring Method |
|---|---|---|
| **Container Images** | `registry.k8s.io/pause:3.9`, `docker.io/library/ubuntu:24.04` | `skopeo copy` |
| **Helm Charts** | `jetstack/cert-manager`, `bitnami/nginx` | `helm pull` + `helm push` |
| **OS Packages** | `apt` (Ubuntu), `yum/dnf` (Oracle Linux) | `apt-mirror`, `reposync` |
| **Language Packages** | PyPI, npm, Maven, Go modules | `pip download`, `npm pack`, `mvn dependency:go-offline` |
| **Binaries** | `kubectl`, `helm`, `kubespray`, `ansible`, `terraform` | Direct download + checksum |
| **CRDs** | `cert-manager`, `external-dns`, `rook` CRDs | Included in Helm charts |
| **Operators** | `trivy-operator`, `opentelemetry-operator` | Helm charts + images |
| **AI/ML** | `vllm`, `llama.cpp`, model weights | Model mirroring scripts |

## Mirroring Procedure

### 1. Connected Staging Environment
```bash
# 1. Pull all images
skopeo copy --src-tls-verify=false \
  docker://registry.k8s.io/pause:3.9 \
  docker://staging-harbor.internal/base/pause:3.9

# 2. Pull Helm charts
helm pull oci://registry-1.docker.io/bitnami/nginx \
  --destination ./charts/
helm push ./charts/nginx-15.0.0.tgz oci://staging-harbor.internal/charts

# 3. Mirror OS packages
apt-mirror /etc/apt/mirror.list  # Ubuntu
reposync -n -p /mirror/ol9-baseos --repoid=ol9-baseos  # Oracle Linux

# 4. Generate artifact matrix
python3 scripts/generate_artifact_matrix.py --output artifact-matrix.md
```

### 2. Verify Integrity
```bash
# Verify image digests
skopeo inspect docker://staging-harbor.internal/base/pause:3.9 --format '{{.Digest}}'
# Compare with artifact-matrix.md

# Verify Helm chart digests
helm package ./charts/nginx-15.0.0.tgz --digest
# Compare with artifact-matrix.md

# Verify package checksums
sha256sum /mirror/ubuntu/pool/main/l/linux/linux-image-*.deb
# Compare with artifact-matrix.md
```

### 3. Export to Air-Gap Media
```bash
# Export Harbor registry
harbor-admin export --registry harbor.internal --output /media/airgap/harbor-export.tar

# Export Nexus
tar -czf /media/airgap/nexus-blobstore.tar.gz /opt/sonatype-work/nexus3/blobs

# Export GitLab
gitlab-backup create STRATEGY=copy
tar -czf /media/airgap/gitlab-backup.tar.gz /var/opt/gitlab/backups

# Export artifact matrix
cp artifact-matrix.md /media/airgap/
```

### 3. Import to Air-Gap Environment
```bash
# 1. Import Harbor
harbor-admin import --registry harbor.internal --input /media/airgap/harbor-export.tar

# 2. Import Nexus
tar -xzf /media/airgap/nexus-blobstore.tar.gz -C /opt/sonatype-work/nexus3/

# 3. Import GitLab
tar -xzf /media/airgap/gitlab-backup.tar.gz -C /var/opt/gitlab/backups
gitlab-backup restore BACKUP=timestamp

# 4. Verify against artifact-matrix.md
python3 scripts/verify_artifacts.py --matrix artifact-matrix.md
```

## Air-Gap Verification Checklist

| Check | Command | Expected |
|---|---|---|
| Image available | `crictl pull harbor.internal/base/pause:3.9` | Success |
| Chart available | `helm search repo nginx --repo oci://harbor.internal/charts` | Found |
| Package install | `apt-get install -y vim` | Success (from internal mirror) |
| Python package | `pip install requests --index-url https://nexus.internal/repository/pypi-proxy/simple/` | Success |
| Helm chart | `helm install nginx oci://harbor.internal/charts/nginx` | Deployed |
| External egress blocked | `curl -I https://example.com` from pod | Fails/blocked |
| Internal registry only | `docker pull nginx:latest` from pod | Fails; internal mirror succeeds |

## Runtime Connectivity Requirements

Even in air-gap, these internal connections are required:

| Connection | Protocol | Port | Purpose |
|---|---|---|---|
| K8s nodes → Harbor | HTTPS | 443 | Image pulls |
| K8s nodes → Nexus | HTTPS | 443 | Package installs |
| K8s nodes → GitLab | HTTPS | 443 | CI/CD, registry |
| K8s nodes → Ceph RGW | HTTPS | 443 | S3 object access |
| K8s nodes → Vault | HTTPS | 8200 | Secret retrieval |
| K8s nodes → Keycloak | HTTPS | 443 | OIDC authentication |
| K8s nodes → Internal DNS | UDP/TCP | 53 | Service discovery |
| K8s nodes → NTP | UDP | 123 | Time sync |
| K8s control plane → etcd | TCP | 2379/2380 | etcd clustering |
| Worker → Control plane | TCP | 6443 | kube-apiserver |

## Air-Gap Configuration Examples

### Container Runtime (containerd)
```toml
# /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://harbor.internal/library"]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry.k8s.io"]
  endpoint = ["https://harbor.internal/k8s"]

[plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal".tls]
  ca_file = "/etc/containerd/certs.d/harbor.internal/ca.crt"
```

### Kubernetes (Kubespray)
```yaml
# inventory/group_vars/k8s_cluster/k8s-cluster.yml
containerd_registries:
  - name: "harbor.internal"
    endpoint: "https://harbor.internal"
    ca_file: "/etc/containerd/certs.d/harbor.internal/ca.crt"
```

### ExternalDNS
```yaml
# addons/platform-addons.md
env:
  - name: EXTERNAL_DNS_RFC2136_HOST
    value: "10.10.0.53"
  - name: EXTERNAL_DNS_RFC2136_TSIG_SECRET
    valueFrom:
      secretKeyRef:
        name: externaldns-tsig-secret
        key: tsig-secret
```

## Air-Gap Verification Scripts

### verify_airgap.py
```python
#!/usr/bin/env python3
"""Verify all artifacts are available in air-gap environment."""

import subprocess
import sys

CHECKS = [
    ("harbor", ["crictl", "pull", "harbor.internal/base/pause:3.9"]),
    ("nexus-apt", ["apt-get", "update"]),
    ("nexus-yum", ["dnf", "makecache"]),
    ("gitlab", ["curl", "-f", "https://gitlab.internal/-/health"]),
    ("harbor-api", ["curl", "-f", "https://harbor.internal/api/v2.0/health"]),
    ("nexus-api", ["curl", "-f", "https://nexus.internal/service/rest/v1/status"]),
    ("gitlab-api", ["curl", "-f", "https://gitlab.internal/-/health"]),
    ("rgw", ["curl", "-f", "https://rgw.internal/minio/health/live"]),
    ("vault", ["curl", "-f", "https://vault.internal:8200/v1/sys/health"]),
    ("keycloak", ["curl", "-f", "https://keycloak.internal/health/ready"]),
]

def run_check(name, cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"FAIL {name}: {e}")
        return False

def main():
    all_pass = True
    for name, cmd in CHECKS:
        ok = run_check(name, cmd)
        status = "PASS" if ok else "FAIL"
        print(f"{status} {name}")
        if not ok:
            all_pass = False
    sys.exit(0 if all_pass else 1)

if __name__ == "__main__":
    main()
```

## Air-Gap Validation

### Acceptance Criteria (Phase 2)
- Every artifact in the matrix imports into the internal system
- A clean node can install packages, pull images, and deploy a Helm chart with no internet
- `skopeo inspect` and `apt-get update` succeed using internal sources only

### Verification Commands
```bash
# Verify all images available
for img in $(cat artifact-matrix.md | grep "image:" | awk '{print $2}'); do
  crictl pull $img || echo "MISSING: $img"
done

# Verify all charts available
for chart in $(cat artifact-matrix.md | grep "chart:" | awk '{print $2}'); do
  helm pull $chart --repo oci://harbor.internal/charts || echo "MISSING: $chart"
done

# Verify OS packages
apt-get update && apt-get install -y vim curl
dnf makecache && dnf install -y vim curl

# Verify no external egress
kubectl run test-egress --image=harbor.internal/library/curlimages/curl:latest --rm -it -- \
  curl -I https://example.com --max-time 10
# Should fail/timeout
```

## References

- [Artifact Matrix](../offline-artifacts/artifact-matrix.md)
- [Offline Artifact Architecture](../offline-artifacts/offline-artifact-architecture.md)
- [Staging and Import Procedure](../offline-artifacts/staging-and-import.md)
- [Network Communication Matrix](../network-matrix/network-communication-matrix.md)