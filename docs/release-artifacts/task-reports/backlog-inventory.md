# TASK 008.1 — Backlog Inventory

**Task:** TASK 008.1 — Backlog Inventory

## Source

93-file reconciliation inventory from TASK-007.3 (`/workspace/release-artifacts/TASK-007.3-reconciliation-analysis/unique-files-inventory.csv`)

## Summary

| Metric | Count |
|--------|-------|
| Total unique files | 93 |
| Reconciled (committed, Phases 1-6) | 23 |
| Reconciled (uncommitted, Phases 7-8) | 8 |
| Reconciled (via dispatcher, Phases 9-11) | 34 |
| Total reconciled | 65 |
| Remaining pending | 1 |
| Remaining blocked | 4 |

## Disposition Summary

| Disposition | Count |
|-------------|-------|
| preserve | ~58 |
| adapt | 3 (CONTRIBUTING.md, README.md, platform/golden-paths/cloudnative-service.json) |
| consolidate | 2 (ADR-0004, ADR-0028) |

## High-Coupling Clusters (Blocked)

| Cluster | Files | Blocker |
|---------|-------|---------|
| Catalog system | catalog/catalog.json, catalog/exports.json, catalog/upgrades.json, scripts/cluster_methods.py, scripts/golden_path.py, site/app.js, site/data.json, site/modules/* | Version pin contradiction + conflict list |
| Kubespray deployment | kubespray/kubespray-deployment.md | v1.31.x vs 1.36.5 version pin contradiction |
| External LB | network-matrix/external-load-balancer.md | Conflict list |

## Blocked Tasks

| Task ID | File | Blocker |
|---------|------|---------|
| TASK-008.1-P09-17 | kubespray/kubespray-deployment.md | Version pin contradiction (v1.31.x vs 1.36.5) — architectural decision needed |
| TASK-008.1-P09-18 | lifecycle/upgrades/upgrade-procedures.md | catalog/upgrades.json conflict |
| TASK-008.1-P09-19 | scripts/cluster_methods.py | catalog/catalog.json conflict |
| TASK-008.1-P10-15 | site/data.json | catalog/catalog.json conflict |

## Pending Task

| Task ID | File | Blocker |
|---------|------|---------|
| TASK-008.1-P10-14 | site/app.js | Depends on P10-15 (site/data.json) which is blocked |

## Completed Tasks (65)

Phases 1-6 (committed): 23 files
Phases 7-8 (uncommitted, validated): 8 files
Phases 9-11 (via dispatcher, validated, uncommitted): 34 files
