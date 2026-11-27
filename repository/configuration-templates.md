# Repository Configuration Templates

## 🎯 Purpose

Document reproducible configuration templates for deployments, config maps, and version consistency checks across the cloud-native-guide repository. This file ensures all infrastructure and application configurations can be regenerated consistently and validated automatically.

## 📋 Template Categories

### Deployment Templates

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: application
  labels:
    app: application
spec:
  replicas: 3
  selector:
    matchLabels:
      app: application
  template:
    metadata:
      labels:
        app: application
    spec:
      containers:
        - name: application
          image: registry/app:latest
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: application-config
      readinessProbe:
        httpGet:
          path: /healthz
          port: 8080
        initialDelaySeconds: 5
        periodSeconds: 10
      livenessProbe:
        httpGet:
          path: /healthz
          port: 8080
        initialDelaySeconds: 15
        periodSeconds: 20
```

#### Helm Chart Values
```yaml
replicaCount: 2

image:
  repository: registry/app
  tag: "latest"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

### ConfigMaps

#### Application Configuration ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: application-config
  labels:
    app: application
data:
  # Application Settings
  LOG_LEVEL: "info"
  APP_ENV: "production"
  API_VERSION: "v1"

  # Database Settings
  DATABASE_HOST: "postgresql-service"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "application"

  # Cache Settings
  CACHE_HOST: "redis-service"
  CACHE_PORT: "6379"
  CACHE_TTL: "3600"

  # Feature Flags
  FEATURE_A: "true"
  FEATURE_B: "false"
```

#### TLS Configuration ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tls-config
  labels:
    app: infrastructure
data:
  tls.crt: "-----BEGIN CERTIFICATE-----\n...\nEND CERTIFICATE-----"
  tls.key: "<PRIVATE_KEY_BLOCK_PLACEHOLDER>"
  ca.crt: "-----BEGIN CERTIFICATE-----\n...\nEND CERTIFICATE-----"
```

### Version Consistency Checks

#### Version Reference Document
```yaml
# Version Consistency Matrix
# All version references in this repository must be consistent with catalog/catalog.json

services:
  api-service:
    version: "2.3.1"
    image: "registry/api:2.3.1"
    last_updated: "2026-11-20"

  web-frontend:
    version: "1.7.4"
    image: "registry/web:1.7.4"
    last_updated: "2026-11-15"

  database:
    version: "15.4"
    image: "registry/db:15.4"
    last_updated: "2026-11-18"

validation_rules:
  - "All version strings must follow Semantic Versioning (MAJOR.MINOR.PATCH)"
  - "No wildcard versions (e.g., 'latest') in production configs"
  - "Image tags must match declared service versions"
  - "Version bumps require catalog/catalog.json update"
  - "Cross-reference all version links with duplicate-detection.md"
```

#### Terraform Version Constraints
```hcl
# Terraform version requirements
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# Provider version constraints
provider "aws" {
  version = "~> 5.0"
}

provider "kubernetes" {
  version = "~> 2.0"
}
```

### Template Validation Procedures

#### Pre-Commit Validation
Run these checks before committing any configuration template changes:

```bash
# 1. Run link validation
python3 scripts/check_links.py

# 2. Validate Terraform syntax
terraform init
terraform validate

# 3. Validate Kubernetes manifests
kubectl apply --dry-run=client -f kubernetes/

# 4. Check for version consistency
python3 scripts/validate_catalog.py

# 5. Run acceptance tests
python3 scripts/acceptance_status.py
```

#### CI/CD Validation Gates
```yaml
# GitHub Actions - Template Validation
name: Validate Templates

on:
  push:
    paths:
      - '**/configuration-templates.md'
      - '**/**.yaml'
      - '**/**.yml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run link check
        run: python3 scripts/check_links.py
        continue-on-error: false

      - name: Terraform Validate
        if: always()
        run: |
          terraform init -backend=false
          terraform validate

      - name: Kubernetes Validate
        if: always()
        run: |
          kubectl apply --dry-run=client -f repository/

      - name: Catalog Consistency
        run: python3 scripts/validate_catalog.py
```

## 🔍 Validation Checklist

| Item | Description | Command |
|------|-------------|---------|
| File existence | Every referenced file must exist on disk | `check_links.py` |
| Anchor validity | Every `#anchor` reference must match a heading or explicit ID | `check_links.py` |
| No duplicate version claims | No two documents should claim the same version without a shared source | `validate_catalog.py` |
| Catalog consistency | `catalog/catalog.json` must reflect all documented docs | `validate_catalog.py` |
| Terraform syntax | All Terraform files must pass `terraform validate` | `terraform validate` |
| Kubernetes validity | All manifests must be parseable by kubectl | `kubectl apply --dry-run` |
| Version consistency | All version references must match catalog entries | Custom check |

## 🛠️ Adding New Templates

When adding a new configuration template:

1. **Place the template** in the appropriate directory (`kubernetes/`, `helm/`, `terraform/`, etc.)
2. **Add to navigation-index.md** if it should appear in the central navigation
3. **Run `check_links.py`** after creation to verify all internal links resolve
4. **Update catalog** if the template should appear in `catalog/catalog.json`
5. **Add cross-reference audit checklist item** in `duplicate-detection.md` if the template contains links to other repository files
6. **Document version consistency** rules in the Version Reference section

## 📊 Current Status

```bash
$ python3 scripts/check_links.py
0 broken link(s) in /workspace/project/github/public-repository/cloud-native-guide
```

All cross-references currently resolve with 0 broken links.

## 🔄 Maintenance

- **Regular runs**: Run `check_links.py` before merging any pull request that modifies docs
- **Anchor updates**: When renaming a heading, update all anchor references to point to the new heading, or add explicit `<a id="old-anchor">` for backward compatibility
- **File moves**: Update all relative links if a markdown file is moved to a new path
- **Catalog sync**: After adding/removing docs, run `validate_catalog.py` to keep `catalog/catalog.json` in sync
- **Template reviews**: Review new configuration templates for security and compliance before merging

---

**Configuration Templates Agent**: DevOps Automator
**Last validated**: `check_links.py` reports 0 broken links
**Related**:
- `scripts/check_links.py` — Link validation script
- `scripts/validate_catalog.py` — Catalog consistency validation
- `repository/navigation-index.md` — Central navigation index
- `duplicate-detection.md` — Cross-reference audit guidelines
- `catalog/catalog.json` — Service catalog and version registry