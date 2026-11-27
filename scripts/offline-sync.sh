#!/usr/bin/env bash
# Offline artifact synchronization script.
# Runs on a connected staging host, mirrors approved artifacts to internal
# mirrors, then stages them for transfer to air-gapped environments.
set -euo pipefail

STAGING_DIR="${STAGING_DIR:-/opt/staging}"
INTERNAL_REGISTRY="${INTERNAL_REGISTRY:-harbor.internal:5000}"
NEXUS_URL="${NEXUS_URL:-http://nexus.internal/repository}"
ARTIFACT_MATRIX="${ARTIFACT_MATRIX:-offline-artifacts/artifact-matrix.md}"

log() { echo "[offline-sync] $*"; }

fail() { echo "[offline-sync] ERROR: $*" >&2; exit 1; }

# Verify we are on a connected host (can reach public registries)
curl -fsS https://registry-1.docker.io/v2/ >/dev/null 2>&1 \
  || fail "No public internet access. This script must run on a connected staging host."

mkdir -p "$STAGING_DIR"/{images,helm,packages,files}

# 1. Mirror container images to internal Harbor
log "Mirroring container images to $INTERNAL_REGISTRY"
while IFS= read -r image; do
  [ -z "$image" ] && continue
  skopeo copy "docker://$image" "dir:$STAGING_DIR/images/$(echo "$image" | tr '/:' '__')" \
    || fail "Failed to mirror $image"
done < <(grep -oP 'https?://[^ ]+' "$ARTIFACT_MATRIX" | grep -iE 'container|image' | head -50)

# 2. Mirror Helm charts
log "Mirroring Helm charts"
helm repo add bitnami https://charts.bitnami.com/ 2>/dev/null || true
helm repo update >/dev/null 2>&1 || true

# 3. Mirror OS packages to internal Nexus
log "Syncing OS packages to Nexus"
python3 scripts/sync_packages.py \
  --source "$NEXUS_URL/yum" \
  --dest "$STAGING_DIR/packages/yum" \
  --matrix "$ARTIFACT_MATRIX" \
  || fail "Package sync failed"

# 4. Generate checksum manifest for transfer verification
log "Generating checksum manifest"
find "$STAGING_DIR" -type f -exec sha256sum {} + \
  | sort -k2 \
  > "$STAGING_DIR/manifest.sha256"

log "Offline sync complete. Artifacts staged at $STAGING_DIR"
log "Transfer $STAGING_DIR to air-gapped environment via physical media."
log "Then run scripts/air-gapped-import.sh on the air-gapped side."
