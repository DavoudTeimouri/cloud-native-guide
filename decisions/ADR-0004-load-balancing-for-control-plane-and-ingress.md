# ADR-0004 — Load balancing for control plane and ingress

- **Status**: Accepted (provisional pending Phase 1 review)
- **Date**: 2026-10-22
- **Deciders**: Platform Architect / SecOps / SRE
- **Supersedes / superseded by**: none

## Context

kube-apiserver, Rancher, Argo CD, Keycloak, and ingress all need stable virtual IPs that fail over.

## Requirements

See `requirements/requirements-and-assumptions.md` (R-01..R-14, D-01..D-14).

## Options considered

- 1. Hardware F5/HA pair.
- 2. Keepalived (VRRP) on a pair of nodes.
- 3. HAProxy in a small dedicated pair.

## Decision

Keepalived VRRP on two dedicated nodes for the control-plane API VIP, with an HAProxy or NGINX layer in front for TLS termination and upstream health checks. Hardware F5 only if the site already owns one.

## Rationale and trade-offs

- VRRP failover is in the second range, not instant.
- HAProxy is explicit and scriptable.
- Hardware gives the best support path.
- Keepalived is a small, well-understood dependency and can be managed by Ansible. Hardware is preferred where it exists.

## Security and operational implications

VRRP depends on multicast or unicast peer configuration on the network segment; a switched network with multicast filtering needs unicast peers. HAProxy and keepalived both need health checks against the real backends.

## Dependencies

VRRP protocol 112 (IP protocol), keepalived health-check ports, HAProxy frontend/backend ports. Verify against the installed versions.

## Failure scenarios

A VIP with no working failover is worse than no VIP: it hides a single point of failure behind a stable address. A split-brain VIP (both nodes think they are master) causes intermittent failures.

## Migration considerations

Migrating from keepalived to HAProxy or to hardware is a config change, not a data migration.
