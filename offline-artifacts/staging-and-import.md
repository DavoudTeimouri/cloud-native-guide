# Staging and Import Procedure

This document describes the procedure for staging artifacts in a connected environment and importing them into the air-gapped production environment.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Air-Gap Deployment Workflow                      │
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

## Phase 1: Connected Staging Environment

### 1. Prerequisites

- Connected staging environment with internet access
- Staging Harbor (`staging-harbor.internal`)
- Staging Nexus (`staging-nexus.internal`)
- Staging GitLab (`staging-gitlab.internal`)
- Sufficient storage for mirrored artifacts

### 2. Mirror Container Images

```bash
#!/bin/bash
# scripts/mirror_images.sh

set -euo pipefail

IMAGES=(
    "registry.k8s.io/pause:3.9"
    "registry.k8s.io/kube-apiserver:v1.36.5"
    "registry.k8s.io/kube-controller-manager:v1.36.5"
    "registry.k8s.io/kube-scheduler:v1.36.5"
    "registry.k8s.io/kube-proxy:v1.36.5"
    "registry.k8s.io/coredns/coredns:v1.14.2"
    "registry.k8s.io/etcd:3.6.15"
    "docker.io/library/ubuntu:24.04"
    "docker.io/library/oraclelinux:9"
    "quay.io/cilium/cilium:v1.20.3"
    "docker.io/metallb/controller:v0.16.1"
    "docker.io/metallb/speaker:v0.16.1"
    "ghcr.io/nginx/nginx-gateway-fabric:2.8.0"
    "ghcr.io/jetstack/cert-manager-controller:v1.21.2"
    "ghcr.io/jetstack/cert-manager-webhook:v1.21.2"
    "ghcr.io/jetstack/cert-manager-cainjector:v1.21.2"
    "quay.io/metallb/metallb:v0.16.1"
    "docker.io/bitnami/nginx:1.28.0"
    "docker.io/aquasecurity/trivy-operator:0.36.0"
    "ghcr.io/open-telemetry/opentelemetry-operator:0.161.0"
    "docker.io/prometheus/prometheus:v3.15.1"
    "quay.io/prometheus/alertmanager:v0.34.1"
    "docker.io/grafana/grafana:13.2.4"
    "docker.io/grafana/loki:3.7.9"
    "docker.io/fluent/fluent-bit:5.1.5"
    "docker.io/velero/velero:v1.18.4"
    "docker.io/hashicorp/vault:2.2.0"
    "docker.io/hashicorp/vault-k8s:v1.7.6"
    "docker.io/keycloak/keycloak:26.8.1"
    "docker.io/rancher/rancher:v2.15.2"
    "quay.io/argoproj/argocd:v3.5.6"
    "docker.io/nvidia/k8s-device-plugin:v0.20.1"
    "docker.io/nvidia/gpu-operator:26.7.2"
    "docker.io/vllm/vllm-openai:v0.32.0"
)

for img in "${IMAGES[@]}"; do
    echo "Mirroring $img"
    skopeo copy --src-tls-verify=false \
        "docker://$img" \
        "docker://staging-harbor.internal/base/$(echo $img | sed 's|.*/||')"
done
```

### Mirror Helm Charts

```bash
#!/bin/bash
# scripts/mirror_charts.sh

CHARTS=(
    "oci://registry-1.docker.io/bitnami/nginx:15.0.0"
    "oci://registry-1.docker.io/bitnami/nginx-ingress-controller:2.8.0"
    "https://charts.jetstack.io/cert-manager-v1.21.2.tgz"
    "https://charts.cilium.io/cilium-1.20.3.tgz"
    "https://metallb.github.io/metallb/metallb-0.16.1.tgz"
    "https://charts.jetstack.io/argo-cd-10.10.5.tgz"
    "https://charts.jetstack.io/external-dns-1.23.0.tgz"
    "https://charts.jetstack.io/trivy-operator-0.36.0.tgz"
    "https://charts.jetstack.io/opentelemetry-operator-0.161.0.tgz"
    "https://charts.jetstack.io/kube-prometheus-stack-92.11.0.tgz"
    "https://charts.jetstack.io/loki-7.5.0.tgz"
    "https://charts.jetstack.io/promtail-7.5.0.tgz"
    "https://charts.jetstack.io/tempo-2.3.0.tgz"
    "https://charts.jetstack.io/velero-12.2.1.tgz"
    "https://charts.jetstack.io/vault-0.34.1.tgz"
    "https://charts.jetstack.io/rancher-2.15.2.tgz"
    "https://charts.jetstack.io/keycloak-24.0.0.tgz"
    "https://charts.jetstack.io/harbor-2.15.4.tgz"
    "https://charts.jetstack.io/rook-ceph-1.21.0.tgz"
)

mkdir -p ./charts-mirror

for chart in "${CHARTS[@]}"; do
    echo "Mirroring $chart"
    helm pull "$chart" --destination ./charts-mirror --untar=false
done

# Push to internal Helm repo
for chart in ./charts-mirror/*.tgz; do
    helm push "$chart" oci://staging-harbor.internal/charts
done
```

### Mirror OS Packages

```bash
# Ubuntu 24.04
apt-mirror /etc/apt/mirror.list

# Oracle Linux 9
reposync -n -p /mirror/ol9-baseos --repoid=ol9-baseos
reposync -n -p /mirror/ol9-appstream --repoid=ol9-appstream

# Python packages
pip download -r requirements.txt -d ./pypi-mirror --no-deps

# npm
npm pack --dry-run 2>/dev/null | tail -n +2 | while read pkg; do
    npm pack "$pkg" --pack-destination ./npm-mirror
done
```

### Generate Artifact Matrix

```bash
#!/bin/bash
# scripts/generate_artifact_matrix.py

import json
import subprocess
import hashlib
from pathlib import Path

def get_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_image_digest(image):
    result = subprocess.run(
        ["skopeo", "inspect", f"docker://{image}"],
        capture_output=True, text=True, check=True
    )
    import json
    return json.loads(result.stdout)["Digest"]

def main():
    matrix = {
        "images": [],
        "charts": [],
        "packages": [],
        "generated": "2026-11-23T00:00:00Z"
    }
    
    # Process images
    for img in IMAGES:
        digest = get_image_digest(f"staging-harbor.internal/base/{img.split('/')[-1]}")
        matrix["images"].append({
            "source": img,
            "internal": f"harbor.internal/base/{img.split('/')[-1]}",
            "digest": digest
        })
    
    # Write matrix
    with open("artifact-matrix.md", "w") as f:
        f.write("# Artifact Matrix\n\n")
        f.write(f"Generated: {matrix['generated']}\n\n")
        f.write("## Images\n\n")
        f.write("| Source | Internal | Digest |\n")
        f.write("|--------|----------|--------|\n")
        for img in matrix["images"]:
            f.write(f"| {img['source']} | {img['internal']} | {img['digest']} |\n")

if __name__ == "__main__":
    main()
```

## Verification

```bash
# Verify image digests
for img in $(cat artifact-matrix.md | grep "image:" | awk '{print $2}'); do
    expected=$(grep "$img" artifact-matrix.md | awk '{print $4}')
    actual=$(skopeo inspect "docker://harbor.internal/base/$(echo $img | cut -d'/' -f2-)" --format '{{.Digest}}')
    if [ "$expected" != "$actual" ]; then
        echo "MISMATCH: $img expected $expected got $actual"
    fi
done

# Verify chart digests
for chart in $(ls charts-mirror/*.tgz); do
    expected=$(grep "$chart" artifact-matrix.md | awk '{print $4}')
    actual=$(sha256sum "$chart" | awk '{print $1}')
    if [ "$expected" != "$actual" ]; then
        echo "MISMATCH: $chart expected $expected got $actual"
    fi
done
```

## Export to Air-Gap Media

```bash
#!/bin/bash
# scripts/export_airgap.sh

OUTPUT_DIR="/media/airgap/$(date +%Y%m%d)"

mkdir -p "$OUTPUT_DIR"

# Export Harbor
echo "Exporting Harbor..."
harbor-admin export --registry staging-harbor.internal --output "$OUTPUT_DIR/harbor-export.tar"

# Export Nexus
echo "Exporting Nexus..."
tar -czf "$OUTPUT_DIR/nexus-blobstore.tar.gz" /opt/sonatype-work/nexus3/blobs

# Export GitLab
echo "Exporting GitLab..."
gitlab-backup create STRATEGY=copy
tar -czf "$OUTPUT_DIR/gitlab-backup.tar.gz" /var/opt/gitlab/backups

# Export artifact matrix
cp artifact-matrix.md "$OUTPUT_DIR/"

# Generate checksums
cd "$OUTPUT_DIR"
sha256sum * > CHECKSUMS.sha256

echo "Export complete: $OUTPUT_DIR"
```

## Import to Air-Gap Production

```bash
#!/bin/bash
# scripts/import_airgap.sh

INPUT_DIR="/media/airgap/$(date +%Y%m%d)"

# 1. Verify checksums
cd "$INPUT_DIR"
sha256sum -c CHECKSUMS.sha256

# 2. Import Harbor
echo "Importing Harbor..."
harbor-admin import --registry harbor.internal --input "$INPUT_DIR/harbor-export.tar"

# 2. Import Nexus
echo "Importing Nexus..."
tar -xzf "$INPUT_DIR/nexus-blobstore.tar.gz" -C /opt/sonatype-work/nexus3/

# 3. Import GitLab
echo "Importing GitLab..."
tar -xzf "$INPUT_DIR/gitlab-backup.tar.gz" -C /var/opt/gitlab/backups
gitlab-backup restore BACKUP=timestamp

# 4. Verify against artifact-matrix.md
python3 scripts/verify_artifacts.py --matrix "$INPUT_DIR/artifact-matrix.md"
```

## Verification

```bash
#!/bin/bash
# scripts/verify_artifacts.py

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

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*