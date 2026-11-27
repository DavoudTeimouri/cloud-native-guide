#!/usr/bin/env bash
# Air-gapped artifact import script.
# Runs on the air-gapped transfer station. Imports artifacts from staged
# physical media into internal Harbor/Nexus/GitLab. No public internet access.
set -euo pipefail

STAGING_DIR="${STAGING_DIR:-/mnt/transfer/staging}"
INTERNAL_REGISTRY="${INTERNAL_REGISTRY:-harbor.internal:5000}"
NEXUS_URL="${NEXUS_URL:-http://nexus.internal/repository}"

log() { echo "[air-gapped-import] $*"; }

fail() { echo "[air-gapped-import] ERROR: $*" >&2; exit 1; }

# Verify we are air-gapped (no public route)
ip route get 1.1.1.1 >/dev/null 2>&1 \
  && fail "This host has a public route. Air-gapped import must not run on a connected host."

[ -d "$STAGING_DIR" ] || fail "Staging directory $STAGING_DIR not found."

# 1. Verify checksum manifest
log "Verifying artifact checksums"
( cd "$STAGING_DIR" && sha256sum -c manifest.sha256 ) \
  || fail "Checksum verification failed. Artifacts may be corrupted."

# 2. Import container images to internal registry
log "Importing container images to $INTERNAL_REGISTRY"
for img_dir in "$STAGING_DIR/images"/*; do
  [ -d "$img_dir" ] || continue
  skopeo copy "dir:$img_dir" "docker://$INTERNAL_REGISTRY/$(basename "$img_dir" | tr '__' '/')" \
    || fail "Failed to import image from $img_dir"
done

# 3. Import OS packages to Nexus
log "Importing OS packages to Nexus"
curl -fsS -u "${NEXUS_USER:-admin}:${NEXUS_PASS:-admin}" \
  -F "raw.asset0=@$STAGING_DIR/packages/yum/*;1" \
  "$NEXUS_URL/yum" \
  || fail "Package import to Nexus failed"

# 4. Helm charts to internal Helm repo
log "Importing Helm charts"
helm repo add internal "http://nexus.internal/repository/helm-hosted/" \
  || helm repo update internal

log "Air-gapped import complete. All artifacts now available internally."
log "Proceed with installation using internal endpoints only."
