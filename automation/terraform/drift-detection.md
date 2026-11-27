# Terraform Drift Detection

## A. Purpose and scope

Document Terraform drift detection: terraform plan drift, remediation, state locking, state migration.

Cross-references `automation/terraform/vsphere.md`, `automation/terraform/state-management.md`.

## B. Drift detection

Drift is detected by comparing Terraform state with actual infrastructure:

```bash
# Plan without applying — shows drift
terraform plan -out=tfplan.binary

# Show plan details
terraform show tfplan.binary

# Detect drift in all resources
terraform plan -detailed-exitcode

# Exit codes:
# 0 = no changes, 1 = error, 2 = changes/drift detected
```

## C. Remediation

When drift is detected:

1. Review the drift — is it intentional?
2. If intentional, import the resource into state
3. If unintentional, apply to reconcile
4. Document the decision

```bash
# Import drifted resource into state
terraform import aws_instance.web i-0123456789

# Apply to reconcile drift
terraform apply -auto-approve
```

## D. State locking

State locking prevents concurrent modifications:

```bash
# Force unlock (only if lock is stale)
terraform force-LOCK <lock-id>
```

## E. State migration

State migration when moving between backends:

```bash
# Migrate state from local to S3
terraform init -migrate-state

# Pull state for backup
terraform state pull > terraform.tfstate.backup

# Push state after manual edit
terraform state push terraform.tfstate
```

## F. Cross-references

- `automation/terraform/vsphere.md` — vSphere Terraform
- `automation/terraform/state-management.md` — State management
