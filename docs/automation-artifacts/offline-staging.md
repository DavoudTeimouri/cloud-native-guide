# Offline Staging Artifacts

## Purpose and scope

Scripts and schema for air-gapped artifact staging: download container images, Helm charts, OS packages, and documentation on a connected host, transfer via physical media, and import on disconnected nodes. All artifacts live under `automation/offline-staging/`.

## Directory layout

```text
automation/offline-staging/
├── README.md                 # Overview and workflow
├── scripts/
│   ├── stage_artifacts.py    # Connected host: download + package
│   ├── import_artifacts.py   # Air-gapped host: verify + import
│   ├── validate_manifest.py  # Validate manifest against schema
│   ├── check_readiness.py    # Check target is ready for offline install
│   └── test_offline_staging.py# Self-checks (15 tests)
└── schema/
    └── manifest-schema-v1.json # JSON Schema for offline manifests
```

## Customization points

### Manifest (manifest.json)

Describes what to stage. Edit components/versions to match your environment:

```json
{
  "profile": "production",
  "registry": "harbor.internal:5000",
  "components": [
    {
      "name": "harbor",
      "version": "2.10.0",
      "type": "helm-chart",
      "source_url": "https://helm.goharbor.io/harbor-2.10.0.tgz",
      "checksum_sha256": "..."
    },
    {
      "name": "nexus",
      "version": "3.66.0",
      "type": "docker-image",
      "source_url": "docker://sonatype/nexus3:3.66.0"
    }
  ],
  "os_packages": [
    {"name": "containerd", "version": "1.7.0", "repo": "internal-rpm"}
  ]
}
```

| Field | What it controls | Customize when |
| --- | --- | --- |
| `profile` | `production`, `staging`, `lab` | Your deployment profile differs |
| `registry` | Target internal registry | Your Harbor/Nexus address differs |
| `components[].version` | Pinned version | You pin different versions |
| `components[].source_url` | Download source | You use a different mirror |
| `os_packages` | OS packages to mirror | Your package list differs |

### Schema

`manifest-schema-v1.json` enforces required fields. Edit it only when you add new manifest fields.

### Readiness profile

`check_readiness.py --profile <name>` checks the target environment. Add profiles for `production`, `staging`, `lab` as needed.

## How to run (air-gapped workflow)

### Step 1 — Connected host: stage

```bash
python3 automation/offline-staging/scripts/stage_artifacts.py \
  --manifest manifest.json \
  --output /mnt/offline-media/
```

Result: tarballs + checksums on `/mnt/offline-media/` (physical media).

### Step 2 — Transfer via physical media

Carry `/mnt/offline-media/` to the air-gapped environment.

### Step 3 — Air-gapped host: import

```bash
python3 automation/offline-staging/scripts/import_artifacts.py \
  --media /mnt/offline-media/ \
  --target /opt/offline-mirror/
```

### Step 4 — Verify

```bash
python3 automation/offline-staging/scripts/check_readiness.py \
  --profile production
```

## Related

- [Automation Artifacts overview](index.md)
- [Air-gapped installation (docs section 03.3)](../03-repository-registry/3.3-installation-config.md)
- [Air-gapped client configuration (docs section 03.6)](../03-repository-registry/3.6-client-config.md)
