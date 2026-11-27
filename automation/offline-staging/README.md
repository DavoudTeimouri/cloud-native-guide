# Offline Artifact Staging

This directory contains the offline artifact staging workflow for the Cloud-Native Guide.

## Structure

```
automation/offline-staging/
├── README.md                    # This file
├── schema/
│   └── manifest-schema-v1.json  # JSON Schema for manifest validation
├── manifests/                   # Generated manifests (gitignored)
├── config/                      # Configuration files
├── scripts/
│   ├── validate_manifest.py     # Manifest validator
│   ├── stage_artifacts.py       # Staging helper
│   └── check_readiness.py       # Profile readiness checker
└── examples/                    # Example manifests and usage
```

## Workflow

### 1. Connected Staging Environment

```bash
# Stage artifacts for kubespray-control-node profile
python3 automation/offline-staging/scripts/stage_artifacts.py \
  --staging-root /opt/offline-staging \
  --manifest /opt/offline-staging/manifests/kubespray-control-node.json \
  --profile kubespray-control-node \
  --artifact "python-package,ansible,12.3.0,pypi,https://pypi.org/project/ansible/,/path/to/ansible-12.3.0-py3-none-any.whl,python-packages/ansible-12.3.0-py3-none-any.whl,true" \
  --artifact "python-package,ansible-core,2.19.3,pypi,https://pypi.org/project/ansible-core/,/path/to/ansible_core-2.19.3-py3-none-any.whl,python-packages/ansible_core-2.19.3-py3-none-any.whl,true" \
  # ... repeat for all required packages

# Verify the manifest
python3 automation/offline-staging/scripts/validate_manifest.py \
  /opt/offline-staging/manifests/kubespray-control-node.json \
  --staging-root /opt/offline-staging

# Check readiness
python3 automation/offline-staging/scripts/check_readiness.py \
  /opt/offline-staging/manifests/kubespray-control-node.json \
  --profile kubespray-control-node
```

### 2. Transfer

Transfer the entire staging directory (`/opt/offline-staging/`) using approved process.

### 3. Restricted/Air-Gapped Environment

```bash
# Validate manifest and checksums
python3 automation/offline-staging/scripts/validate_manifest.py \
  /opt/offline-staging/manifests/kubespray-control-node.json \
  --staging-root /opt/offline-staging

# Check profile readiness
python3 automation/offline-staging/scripts/check_readiness.py \
  /opt/offline-staging/manifests/kubespray-control-node.json \
  --profile kubespray-control-node
```

## Artifact Categories

| Category | Description |
|----------|-------------|
| `python-package` | Python wheels/sdists for control node |
| `ansible-collection` | Ansible Galaxy collection archives |
| `kubespray-source` | Kubespray source archive (git tag) |
| `container-image` | Container images (as tar archives) |
| `os-package` | OS package files (.rpm, .deb) |
| `ca-certificate` | CA certificates |
| `other` | Other artifacts |

## Profiles

| Profile | Description |
|---------|-------------|
| `kubespray-control-node` | Control node Python deps, collections, Kubespray source |
| `kubernetes-cilium` | Container images for Kubernetes with Cilium CNI |
| `kubernetes-calico` | Container images for Kubernetes with Calico CNI |
| `combined` | Union of all above (not mutually exclusive CNIs) |

## Manifest Schema

See `schema/manifest-schema-v1.json` for the complete schema.

Key fields per artifact:
- `category`: Artifact category
- `name`: Artifact name
- `version`: Version string
- `source`: Source info (type, reference, fetched_at, verified)
- `destination`: Relative path within staging directory
- `sha256`: SHA-256 checksum (mandatory)
- `size_bytes`: File size
- `platform`: Platform/architecture
- `required`: Boolean, required for profile
- `feature`: Feature flag (cilium, calico, gpu, monitoring)

## Safety Properties

- **No internet access**: Scripts never download from internet
- **Path traversal protection**: Destinations must stay within staging root
- **Checksum verification**: SHA-256 mandatory and validated
- **No overwrite without --force**: Existing files protected
- **Idempotent**: Re-running produces same manifest
- **No secrets in manifest**: Only source references, no credentials

## Limitations

- **Full Air-Gap not yet ready**: Ansible collections/Python deps staging implemented but full integration with Kubespray deployment requires additional work
- **Container images**: Staging as tar archives; operator must load into internal registry
- **OS packages**: Not yet automated; documented as future work
- **Signature verification**: Not implemented; checksums only

## Integration with Kubespray Workflow

The deployment preflight can validate:
- Selected artifact profile
- Manifest schema version
- Required artifact presence
- Checksums
- Python wheelhouse readiness
- Ansible collection availability
- Kubespray source availability
- Container image inventory completeness for selected CNI
- Internal registry configuration
