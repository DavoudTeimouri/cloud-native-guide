# Terraform State Migration Procedure

## Overview

This procedure documents Terraform state migration operations: backend migration, state locking, and state import. These operations are essential when moving Terraform state between backends, preventing concurrent modifications, or adopting existing infrastructure into Terraform management.

## 1. Backend Migration

### 1.1 Migrate State from Local to S3

```bash
# Initialize with S3 backend (first time)
terraform init -backend=s3 -backend-config="bucket=my-tf-state" -backend-config="key=terraform-state" -backend-config="region=us-east-1"

# Migrate existing local state to S3
terraform init -migrate-state -backend=s3 -backend-config="bucket=my-tf-state" -backend-config="key=terraform-state" -backend-config="region=us-east-1"
```

### 1.2 Migrate State from Local to GCS

```bash
# Initialize with GCS backend
terraform init -backend=gcs -backend-config="bucket=my-tf-state" -backend-config="prefix=terraform"

# Migrate existing local state to GCS
terraform init -migrate-state -backend=gcs -backend-config="bucket=my-tf-state" -backend-config="prefix=terraform"
```

### 1.3 Migrate State Between Cloud Backends

```bash
# Phase 1: Pull state from source backend
terraform state pull > tfstate.backup

# Phase 2: Initialize with destination backend
terraform init -backend=NEW_BACKEND -backend-config="..."

# Phase 3: Push state to destination backend
terraform state push tfstate.backup
```

### 1.4 Manual Backend Transition

When switching backends without `terraform init -migrate-state`:

```bash
# 1. Export state from current backend
terraform state pull > tfstate.exported

# 2. Initialize new backend
terraform init -backend=NEW_BACKEND -backend-config="..."

# 3. Import state into new backend
terraform import terraform.state tfstate.exported
# Or: copy the state file directly and run terraform init
```

## 2. State Locking

### 2.1 Understanding State Locking

Terraform uses state locking to prevent concurrent operations from corrupting the state file. When `terraform apply`, `terraform plan`, or other state-modifying commands run, Terraform acquires a lock on the state file. If a lock is held from a crashed operation, subsequent operations will fail with a "state locked" error.

### 2.2 Check Lock Status

```bash
# Check if state is currently locked
terraform force-unlock 2>&1 || echo "No lock found or lock is valid"
```

### 2.3 Force Unlock (Use with Caution)

**Only use force-unlock if you are certain the previous operation did not complete and the state is consistent.** Force unlocking while another operation is in progress can corrupt the state.

```bash
# List locked operations
terraform force-unlock

# Or with specific lock ID
terraform force-unlock <lock-id>
```

### 2.4 Manual Lock Management

If the lock file is stale (e.g., from a crashed run without cleanup), manually remove the lock:

```bash
# Remove the lock file (platform-dependent)
# For S3 backend: remove the .tfstate.lock file from the bucket
# For local backend: remove .terraform.tfstate.lockfile

# Then re-run the operation
terraform apply
```

### 2.5 Recover from Lock Errors

```bash
# Wait for any in-progress operation to complete, then re-run
# Or force-unlock only if you've verified state consistency
```

## 3. State Import

### 3.1 Import Existing Resource into Terraform

```bash
# Import an existing AWS EC2 instance into Terraform state
terraform import aws_instance.web i-0123456789abcdef0

# After import, run terraform plan to verify
terraform plan

# Review and update the configuration as needed
```

### 3.2 Import Existing Resource with Specific Address

```bash
# Import and assign to a specific resource address
terraform import -index 0 aws_instance.web i-0123456789abcdef0

# Or import with explicit target name
terraform import 'aws_instance.web[i-0123456789abcdef0]' i-0123456789abcdef0
```

### 3.3 Import Resource Using Resource ID

```bash
# Import using full resource identifier
terraform import aws_instance.web i-0123456789abcdef0

# Verify in state
terraform state list
```

### 3.4 Import Multiple Resources

```bash
# Import multiple resources at once
terraform import aws_instance.web1 i-0123456789abcdef0
terraform import aws_instance.web2 i-0456789abcdef01

# Verify all imported
terraform state list
```

### 3.5 Post-Import Verification

```bash
# List all resources in state
terraform state list

# Show full state
terraform show

# Run plan to check for drift
terraform plan
```

## Cross-references

- `automation/terraform/drift-detection.md` — Terraform drift detection, remediation, state locking, state migration
- `automation/terraform/vsphere.md` — Terraform VM provisioning on vSphere and virtualization platforms
- `automation/terraform/ansible-integration.md` — Terraform provisions the VM; Ansible configures it
