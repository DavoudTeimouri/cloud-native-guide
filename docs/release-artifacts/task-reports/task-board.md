# TASK 008.0 — Persistent Task Board Design and State

**Task:** TASK 008.0 Persistent Autonomous Engineering Runtime — Task Board

## 1. Kanban Database Schema (existing at /data/kanban.db)

The Kanban DB provides a durable task queue with the following tables:

| Table | Purpose |
|-------|---------|
| tasks | Task definitions: id, title, body, assignee, status, priority, assignee, workspace_path, branch_name, project_id, claim_lock, claim_expires, result, idempotency_key, consecutive_failures, max_runtime_seconds, last_heartbeat_at, block_kind, block_recurrences, reasoning_effort, completion_contract |
| task_links | Parent/child dependencies (prevents premature execution) |
| task_runs | Execution runs: status, claim_lock, worker_pid, max_runtime_seconds, last_heartbeat_at, outcome, error |
| task_events | Event log for audit trail |
| task_comments | Comments on tasks |
| task_attachments | File attachments |

## 2. Task Board Population

**Source:** TASK-007.x inventory — 56 remaining unique files from the 93-file reconciliation backlog.

**Task ID scheme:** TASK-008.0-P07 through TASK-008.0-P16 (Phases 7-16, ~7 files per phase at current rate)

**Task fields:**
- `id`: Unique task ID (e.g., TASK-008.0-P07-01)
- `title`: Human-readable task title
- `body`: Full task specification (scope, deliverables, acceptance criteria, validation commands)
- `status`: pending → in-progress → review-pending → completed → blocked → failed
- `priority`: 0-9 (higher = more urgent)
- `assignee`: Worker alias (Hermes-Worker) or agent slug
- `workspace_path`: Isolated worktree path
- `branch_name`: Git branch for the task
- `project_id`: TASK-008.0
- `completion_contract`: JSON defining acceptance criteria
- `max_runtime_seconds`: Per-task timeout
- `max_retries`: Bounded retry count
- `block_kind`: Reason if blocked

## 3. Remaining Tasks (56 files from inventory)

### Phase 7 Candidates (5 files)
| Task ID | File | Status | Dependencies |
|---------|------|--------|--------------|
| TASK-008.0-P07-01 | architecture/01-logical-diagram.md | pending | none |
| TASK-008.0-P07-02 | decisions/ADR-0015-identity-integration-layer.md | pending | TASK-008.0-P07-04 |
| TASK-008.0-P07-03 | decisions/ADR-0031-identity-integration-with-ldap-ad-federation.md | pending | TASK-008.0-P07-04 |
| TASK-008.0-P07-04 | kubernetes/control-plane/index.md | pending | none |
| TASK-008.0-P07-05 | kubernetes/addons/cert-manager.md | pending | TASK-008.0-P07-04 |

### Phase 8 Candidates (5 files)
| Task ID | File | Status | Dependencies |
|---------|------|--------|--------------|
| TASK-008.0-P08-01 | kubespray/group-vars-template.md | pending | none |
| TASK-008.0-P08-02 | kubespray/inventory-template.ini | pending | none |
| TASK-008.0-P08-03 | kubespray/multi-version-support.md | pending | none |
| TASK-008.0-P08-04 | kubespray/kubespray-deployment.md | blocked | version-matrix contradiction |
| TASK-008.0-P08-05 | lifecycle/upgrades/upgrade-procedures.md | pending | catalog/upgrades.json conflict |

### Phase 9 Candidates (5 files)
| Task ID | File | Status | Dependencies |
|---------|------|--------|--------------|
| TASK-008.0-P09-01 | network-matrix/firewall-rules-generation.md | pending | none |
| TASK-008.0-P09-02 | network-matrix/network-communication-matrix.md | pending | none |
| TASK-008.0-P09-03 | operating-systems/oracle-linux/baseline.md | pending | none |
| TASK-008.0-P09-04 | operating-systems/ubuntu/baseline.md | pending | none |
| TASK-008.0-P09-05 | secrets-management/pki/index.md | pending | BSL license review |

### Phase 10 Candidates (5 files)
| Task ID | File | Status | Dependencies |
|---------|------|--------|--------------|
| TASK-008.0-P10-01 | secrets-management/pki/root-ca-rotation.md | pending | TASK-008.0-P09-05 |
| TASK-008.0-P10-02 | secrets-management/vault/vault-architecture.md | pending | ADR-0016/0025 |
| TASK-008.0-P10-03 | security/host-baseline.md | pending | ALREADY RECONCILED in Phase 5 |
| TASK-008.0-P10-04 | service-mesh/evaluation.md | pending | ALREADY RECONCILED in Phase 6 |
| TASK-008.0-P10-05 | storage/ceph/cephadm-deployment.md | pending | ADR-0029 |

### Phase 11+ Candidates (remaining ~36 files)
| File | Area | Notes |
|------|------|-------|
| gpu-ai/* | GPU/AI | 5 files, depends on gpu-ai scheduling/monitoring |
| identity/* | Identity | sssd-realmd.md deleted on integration — do not restore |
| kubernetes/addons/* | K8s addons | Multiple files, some depend on control-plane |
| kubernetes/networking/* | Networking | cilium.md, metallb.md, ingress/* |
| kubernetes/security/* | Security | security-controls.md already reconciled |
| lifecycle/* | Lifecycle | backup-and-dr.md, disaster-recovery/index.md already reconciled |
| management-cluster/* | Management | rancher.md, keycloak/*, argocd/* |
| manifests/external-lb/* | External LB | compose, haproxy, keepalived |
| monitoring/* | Monitoring | prometheus.md, log-pipeline.md |
| platform/* | Platform | backstage/catalog-info.yaml already reconciled |
| requirements/* | Requirements | Multiple files, some depend on version-matrix |
| scripts/* | Scripts | Multiple scripts, some drive catalog generation |
| site/* | Site | app.js, data.json, modules/* depend on catalog |
| storage/* | Storage | cephadm-deployment.md, rook-ceph.md, alternatives |
| tests/* | Tests | test_site_render.py, acceptance/README.md |
| troubleshooting/* | Troubleshooting | Multiple troubleshooting guides |

## 4. Task Dependencies (task_links)

| Parent | Child | Reason |
|--------|-------|--------|
| kubernetes/control-plane/index.md | kubernetes/addons/cert-manager.md | cert-manager depends on control plane |
| kubernetes/control-plane/index.md | decisions/ADR-0002-kubernetes-control-plane-topology.md | ADR references control plane |
| secrets-management/pki/index.md | secrets-management/pki/root-ca-rotation.md | rotation depends on PKI architecture |
| architecture/00-overview.md | architecture/01-logical-diagram.md | diagram references overview |
| architecture/00-overview.md | architecture/02-deployment-topology.md | already reconciled Phase 5 |
| compatibility/version-matrix.md | kubespray/kubespray-deployment.md | version pin contradiction |
| catalog/catalog.json | lifecycle/upgrades/upgrade-procedures.md | catalog dependency conflict |

## 5. Status Definitions

| Status | Meaning |
|--------|---------|
| pending | Task created, dependencies not yet satisfied or not yet dispatched |
| in-progress | Task dispatched to worker, execution ongoing |
| review-pending | Implementation complete, awaiting independent Review |
| completed | Review passed, local commit created |
| blocked | Task cannot proceed due to external dependency or blocker |
| failed | Task execution failed, bounded retries exhausted |

## 6. Completion Contract (per task)

```json
{
  "scope": "Reconcile <file> from integration branch to worktree",
  "deliverables": ["<file> added to isolated worktree"],
  "acceptance_criteria": [
    "git diff --check exit=0",
    "File content matches integration branch verbatim",
    "No conflicts with PR #2 changes",
    "No dependencies on conflict files",
    "Cross-references resolve"
  ],
  "validation_commands": ["git diff --check", "File existence check", "Content diff vs integration branch"],
  "completion_condition": "File present in worktree, validated, committed after Review"
}
```

## 7. Current Kanban State

- Total tasks in DB: 0 (to be populated)
- Tasks by status: all pending (initial population)
- Tasks blocked: TASK-008.0-P08-04 (kubespray version contradiction), TASK-008.0-P09-05 (BSL license)
