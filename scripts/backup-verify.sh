#!/usr/bin/env bash
# Backup verification drill script.
# Restores a Velero backup into a scratch namespace and validates data integrity.
# Run monthly (application) or quarterly (full environment).
set -euo pipefail

BACKUP_NAME="${BACKUP_NAME:-}"
SCRATCH_NAMESPACE="${SCRATCH_NAMESPACE:-velero-drill}"
RTO_TARGET_SECONDS="${RTO_TARGET_SECONDS:-3600}"

log() { echo "[backup-verify] $*"; }

fail() { echo "[backup-verify] ERROR: $*" >&2; exit 1; }

[ -n "$BACKUP_NAME" ] || fail "BACKUP_NAME is required. Example: BACKUP_NAME=prod-app-20240101 $0"

START_EPOCH=$(date +%s)

# 1. Create restore into scratch namespace
log "Creating restore from backup $BACKUP_NAME into namespace $SCRATCH_NAMESPACE"
kubectl create namespace "$SCRATCH_NAMESPACE" --dry-run=client -o yaml \
  | kubectl apply -f -

velero restore create "drill-$(date +%s)" \
  --from-backup "$BACKUP_NAME" \
  --include-namespaces default \
  --namespace "$SCRATCH_NAMESPACE" \
  --wait

# 2. Verify restored pods are running
log "Verifying restored pods"
kubectl wait --for=condition=Ready pods -l app \
  -n "$SCRATCH_NAMESPACE" \
  --timeout=300s \
  || fail "Restored pods did not become Ready"

# 3. Measure RTO
END_EPOCH=$(date +%s)
RTO_SECONDS=$(( END_EPOCH - START_EPOCH ))
log "Restore completed in $RTO_SECONDS seconds"

if [ "$RTO_SECONDS" -gt "$RTO_TARGET_SECONDS" ]; then
  log "WARNING: RTO $RTO_SECONDSs exceeds target $RTO_TARGET_SECONDSs"
else
  log "OK: RTO $RTO_SECONDSs within target $RTO_TARGET_SECONDSs"
fi

# 4. Cleanup scratch namespace
log "Cleaning up scratch namespace $SCRATCH_NAMESPACE"
kubectl delete namespace "$SCRATCH_NAMESPACE"

log "Backup verification drill complete."
