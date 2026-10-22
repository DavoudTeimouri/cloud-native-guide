# ADR-0007 — Ingress controller and Gateway API

- **Status**: Accepted (provisional pending Phase 1 review)
- **Date**: 2026-10-22
- **Deciders**: Platform Architect / SecOps / SRE
- **Supersedes / superseded by**: none

## Context

L7 traffic entry, TLS termination, and routing.

## Requirements

See `requirements/requirements-and-assumptions.md` (R-01..R-14, D-01..D-14).

## Options considered

- 1. NGINX Ingress Controller.
- 2. Traefik.
- 3. Istio ingress gateway.

## Decision

NGINX Ingress Controller with Gateway API support, one deployment per cluster, fronted by the site load balancer. Gateway API objects preferred; Ingress retained for compatibility.

## Rationale and trade-offs

- F5-maintained, most widely deployed, mature TLS handling.
- Traefik is simpler and label-driven.
- Istio brings mesh coupling.
- NGINX is the enterprise default and pairs with the Gateway API standard.

## Security and operational implications

NGINX must be hardened: no unnecessary modules, explicit worker/connection limits, and admission webhooks that do not permit annotation-based arbitrary configuration from untrusted namespaces.

## Dependencies

NGINX controller, webhook, and metrics ports; the Gateway API CRDs are client-side only. Verify against the pinned release.

## Failure scenarios

Ingress controller failure affects all external traffic to the cluster, but internal ClusterIP traffic is unaffected.

## Migration considerations

Moving from Ingress to Gateway API is incremental: both can coexist. Changing the controller is a helm swap with a brief traffic interruption.
