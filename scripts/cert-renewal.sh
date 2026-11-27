#!/usr/bin/env bash
# Certificate renewal and rotation script.
# Renews in-cluster cert-manager certificates and external load balancer
# registry certificates. Run monthly or when cert-manager reports expiry < 14 days.
set -euo pipefail

NAMESPACE="${NAMESPACE:-cert-manager}"
WARNING_DAYS="${WARNING_DAYS:-14}"
PAGE_DAYS="${PAGE_DAYS:-7}"

log() { echo "[cert-renewal] $*"; }

# 1. Check cert-manager Certificate resources
log "Checking cert-manager Certificates in namespace $NAMESPACE"
kubectl get certificate -n "$NAMESPACE" -o json \
  | jq -r '.items[] | "\(.metadata.name) \(.spec.secretName) \(.status.expiry // "none")"' \
  | while read -r name secret expiry; do
    if [ "$expiry" = "none" ]; then
      log "Certificate $name: not yet issued"
      continue
    fi
    expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expiry" +%s 2>/dev/null)
    now_epoch=$(date +%s)
    days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
    if [ "$days_left" -le "$PAGE_DAYS" ]; then
      log "CRITICAL: Certificate $name expires in $days_left days (secret $secret)"
      kubectl annotate certificate "$name" -n "$NAMESPACE" "cert-manager.io/issue-temporary-certificate=true" --overwrite
    elif [ "$days_left" -le "$WARNING_DAYS" ]; then
      log "WARNING: Certificate $name expires in $days_left days (secret $secret)"
    else
      log "OK: Certificate $name expires in $days_left days"
    fi
  done

# 2. Check external load balancer certificates
log "Checking external load balancer certificates"
for lb in lb-1.internal lb-2.internal; do
  expiry=$(echo | openssl s_client -connect "$lb:443" 2>/dev/null \
    | openssl x509 -enddate -noout \
    | sed 's/notAfter=//')
  if [ -z "$expiry" ]; then
    log "WARNING: Could not retrieve certificate from $lb"
    continue
  fi
  expiry_epoch=$(date -d "$expiry" +%s)
  now_epoch=$(date +%s)
  days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
  if [ "$days_left" -le "$PAGE_DAYS" ]; then
    log "CRITICAL: LB $lb certificate expires in $days_left days"
  elif [ "$days_left" -le "$WARNING_DAYS" ]; then
    log "WARNING: LB $lb certificate expires in $days_left days"
  else
    log "OK: LB $lb certificate expires in $days_left days"
  fi
done

log "Certificate renewal check complete."
