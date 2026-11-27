#!/usr/bin/env python3
"""
TASK-008.7 Autonomous Engineering Supervisor

Implements the continuous engineering loop:
1. Query Kanban Board for Ready tasks
2. If Ready empty, perform backlog discovery
3. Assign tasks to domain agents
4. Delegate via agency_agents_delegate
5. Track execution, validate, integrate

This script manages Kanban state (query/create/move tasks) and records
execution state. Agent implementation work is dispatched via
agency_agents_delegate from the cron job supervisor agent.

Run via cronjob_manage every 30 minutes.
"""

import sqlite3
import json
import time
import os
import sys
import uuid

KANBAN_DB = "/data/kanban.db"
PROJECTS_DB = "/data/projects.db"
PROJECT_ID = "cloud-native-stack"
ORG_DIR = "/workspace/release-artifacts/TASK-008.7-autonomous-organization"
STATE_DIR = os.path.join(ORG_DIR, "state")
LOGS_DIR = os.path.join(ORG_DIR, "logs")
EVIDENCE_DIR = os.path.join(ORG_DIR, "evidence")

REPO_DIR = "/workspace/project/github/public-repository/cloud-native-guide"

# WIP limits from board configuration
WIP_LIMITS = {"In Progress": 3, "Review": 2, "Testing": 2}

DISPATCH_QUEUE_PATH = os.path.join(STATE_DIR, "dispatch_queue.json")
WORKER_TRACKER_PATH = os.path.join(STATE_DIR, "worker-tracker.json")

# Domain to agent slug mapping
DOMAIN_AGENT_MAP = {
    "kubernetes-platform": "sre-site-reliability-engineer",
    "monitoring-observability": "sre-site-reliability-engineer",
    "networking": "sre-site-reliability-engineer",
    "kubespray": "devops-automator",
    "automation-iaac": "devops-automator",
    "gitops-platform-engineering": "devops-automator",
    "storage-ceph": "database-reliability-engineer",
    "disaster-recovery": "database-reliability-engineer",
    "security": "cloud-security-architect",
    "secrets-identity": "cloud-security-architect",
}

# Epic prefix to domain mapping
EPIC_DOMAIN_MAP = {
    "TASK-008.7-E01": "kubernetes-platform",
    "TASK-008.7-E02": "kubespray",
    "TASK-008.7-E03": "gitops-platform-engineering",
    "TASK-008.7-E04": "storage-ceph",
    "TASK-008.7-E05": "disaster-recovery",
    "TASK-008.7-E06": "networking",
    "TASK-008.7-E07": "kubespray",
    "TASK-008.7-E08": "automation-iaac",
    "TASK-008.7-E09": "secrets-identity",
    "TASK-008.7-E10": "monitoring-observability",
    "TASK-008.7-E11": "gitops-platform-engineering",
    "TASK-008.7-E12": "security",
    "TASK-008.7-E13": "kubernetes-platform",
    "TASK-008.7-E14": "kubernetes-platform",
}


def now_ts():
    return int(time.time())


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(message):
    ts = now_iso()
    line = f"[{ts}] {message}"
    print(line)
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(os.path.join(LOGS_DIR, "supervisor.log"), "a") as f:
        f.write(line + "\n")


def kanban_connect():
    return sqlite3.connect(KANBAN_DB)


def get_queue_state(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT status, COUNT(*) FROM tasks WHERE project_id = ? GROUP BY status",
        (PROJECT_ID,),
    )
    state = {}
    total = 0
    for status, count in cur.fetchall():
        state[status] = count
        total += count
    for s in ["Backlog", "Ready", "In Progress", "Review", "Testing", "Blocked", "Done"]:
        state.setdefault(s, 0)
    return state, total


def get_ready_tasks(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, body, priority, assignee, created_at
        FROM tasks
        WHERE project_id = ? AND status = 'Ready'
        ORDER BY priority ASC, id ASC
        """,
        (PROJECT_ID,),
    )
    return cur.fetchall()


def get_in_progress_tasks(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, assignee, worker_started_at
        FROM tasks
        WHERE project_id = ? AND status = 'In Progress'
        """,
        (PROJECT_ID,),
    )
    return cur.fetchall()


def create_task(conn, tid, title, body, epic_id, priority=5, workstream=None,
                dependencies=None, assignee=None):
    cur = conn.cursor()
    contract = json.dumps({
        "epic": epic_id,
        "workstream": workstream or epic_id,
        "kanban_source": "ASK-008.7 backlog discovery",
        "dependencies": dependencies or [],
        "definition_of_done": "Implementation complete, validated, evidence recorded",
        "acceptance_criteria": "Task-specific acceptance criteria met",
        "validation_requirements": "check_links.py passes, validate_catalog.py passes",
        "assigned_agent": assignee,
    })
    cur.execute(
        """
        INSERT OR IGNORE INTO tasks
        (id, title, body, status, priority, assignee, created_by, created_at,
         workspace_kind, tenant, project_id, completion_contract)
        VALUES (?, ?, ?, 'Ready', ?, ?, 'system', ?, 'kanban',
                'cloud-native-guide', ?, ?)
        """,
        (tid, title, body, priority, assignee, now_ts(), PROJECT_ID, contract),
    )
    if epic_id != tid:
        cur.execute(
            "INSERT OR IGNORE INTO task_links (parent_id, child_id) VALUES (?, ?)",
            (epic_id, tid),
        )
    conn.commit()
    return cur.rowcount > 0


def move_task(conn, tid, new_status, evidence=None, assignee=None):
    cur = conn.cursor()
    updates = ["status = ?"]
    params = [new_status]
    if new_status == "In Progress":
        updates.append("worker_started_at = ?")
        params.append(now_ts())
    if assignee is not None:
        updates.append("assignee = ?")
        params.append(assignee)
    if new_status == "Done":
        updates.append("completed_at = ?")
        params.append(now_ts())
    if evidence is not None:
        updates.append("result = ?")
        params.append(json.dumps(evidence))
    params.append(tid)
    cur.execute(
        f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    cur.execute(
        """
        INSERT INTO task_events (task_id, kind, payload, created_at)
        VALUES (?, 'status_change', ?, ?)
        """,
        (tid, json.dumps({"to": new_status, "evidence": bool(evidence)}), now_ts()),
    )
    conn.commit()


def record_event(conn, tid, kind, payload):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO task_events (task_id, kind, payload, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (tid, kind, json.dumps(payload), now_ts()),
    )
    conn.commit()


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, "organization-state.json")
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def load_state():
    path = os.path.join(STATE_DIR, "organization-state.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def get_in_progress_count(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status = 'In Progress'",
        (PROJECT_ID,),
    )
    return cur.fetchone()[0]


def get_review_count(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status = 'Review'",
        (PROJECT_ID,),
    )
    return cur.fetchone()[0]


def get_testing_count(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status = 'Testing'",
        (PROJECT_ID,),
    )
    return cur.fetchone()[0]


def select_eligible_tasks(conn, max_dispatch=3):
    """
    Select Ready tasks eligible for dispatch, respecting WIP limits.
    Returns list of task tuples.
    """
    in_progress_count = get_in_progress_count(conn)
    available_slots = WIP_LIMITS["In Progress"] - in_progress_count

    if available_slots <= 0:
        log(f"WIP limit reached: {in_progress_count}/{WIP_LIMITS['In Progress']} In Progress")
        return []

    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, body, priority, assignee, created_at
        FROM tasks
        WHERE project_id = ? AND status = 'Ready' AND (assignee IS NULL OR assignee = 'None')
        ORDER BY priority ASC, id ASC
        """,
        (PROJECT_ID,),
    )
    candidates = cur.fetchall()

    eligible = candidates[:min(max_dispatch, available_slots)]
    log(f"Selected {len(eligible)} eligible tasks for dispatch (WIP slots available: {available_slots})")
    return eligible


def agent_for_task(task_id, title, body):
    """Determine the appropriate agent slug based on task epic/domain."""
    # Handle test/parallel tasks by scanning body for domain keywords
    body_lower = (body or "").lower()
    title_lower = (title or "").lower()
    if "ceph" in body_lower or "ceph" in title_lower or "storage" in body_lower:
        return "database-reliability-engineer"
    if "vault" in body_lower or "vault" in title_lower or "security" in body_lower or "secret" in body_lower:
        return "cloud-security-architect"
    if "k8s" in body_lower or "kubernetes" in body_lower or "k8s" in title_lower or "kubernetes" in title_lower:
        return "sre-site-reliability-engineer"
    # Normal task ID mapping
    epic_prefix = task_id.split("-G")[0] if "-G" in task_id else task_id
    domain = EPIC_DOMAIN_MAP.get(epic_prefix, "kubernetes-platform")
    return DOMAIN_AGENT_MAP.get(domain, "devops-automator")


def load_worker_tracker():
    if os.path.exists(WORKER_TRACKER_PATH):
        with open(WORKER_TRACKER_PATH) as f:
            return json.load(f)
    return {"active_workers": [], "completed_workers": [], "failed_workers": []}


def save_worker_tracker(tracker):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(WORKER_TRACKER_PATH, "w") as f:
        json.dump(tracker, f, indent=2)


def register_worker(tracker, task_id, agent_slug, session_id, dispatched_at):
    worker = {
        "task_id": task_id,
        "agent": agent_slug,
        "session_id": session_id,
        "dispatched_at": dispatched_at,
        "started_at": dispatched_at,
        "completed_at": None,
        "status": "active",
        "result": None,
    }
    tracker["active_workers"].append(worker)
    save_worker_tracker(tracker)
    return worker


def complete_worker(tracker, session_id, result=None, status="completed"):
    for w in tracker["active_workers"]:
        if w["session_id"] == session_id:
            w["status"] = status
            w["completed_at"] = now_iso()
            w["result"] = result
            tracker["completed_workers"].append(w)
            tracker["active_workers"] = [x for x in tracker["active_workers"] if x["session_id"] != session_id]
            save_worker_tracker(tracker)
            return w
    return None


def fail_worker(tracker, session_id, error=None):
    for w in tracker["active_workers"]:
        if w["session_id"] == session_id:
            w["status"] = "failed"
            w["completed_at"] = now_iso()
            w["error"] = error
            tracker["failed_workers"].append(w)
            tracker["active_workers"] = [x for x in tracker["active_workers"] if x["session_id"] != session_id]
            save_worker_tracker(tracker)
            return w
    return None


def write_dispatch_queue(tasks, agent_assignments, session_ids=None):
    """Write dispatch queue JSON for orchestrator processing."""
    queue = {
        "dispatch_id": str(uuid.uuid4()),
        "created_at": now_iso(),
        "items": [],
    }
    for i, (tid, title, body, priority, assignee, created_at) in enumerate(tasks):
        agent = agent_assignments.get(tid, "devops-automator")
        session_id = session_ids[i] if session_ids and i < len(session_ids) else str(uuid.uuid4())
        queue["items"].append({
            "task_id": tid,
            "title": title,
            "body": body,
            "agent": agent,
            "session_id": session_id,
            "dispatched_at": now_iso(),
            "priority": priority,
        })
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(DISPATCH_QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
    log(f"Dispatch queue written: {len(queue['items'])} items (dispatch_id={queue['dispatch_id']})")
    return queue


def promote_backlog_tasks(conn, max_promote=3):
    """
    Promote eligible Backlog tasks to Ready when Ready column has capacity.
    Checks dependency satisfaction: all dependency tasks must be Done.
    Returns list of promoted task IDs.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status = 'Ready'",
        (PROJECT_ID,),
    )
    ready_count = cur.fetchone()[0]
    available_slots = max_promote - ready_count

    if available_slots <= 0:
        log(f"Ready column full ({ready_count}/3) — no backlog promotion")
        return []

    cur.execute(
        """
        SELECT id, title, body, priority, assignee, created_at, completion_contract
        FROM tasks
        WHERE project_id = ? AND status = 'Backlog'
        ORDER BY priority ASC, id ASC
        """,
        (PROJECT_ID,),
    )
    backlog_tasks = cur.fetchall()

    promoted = []
    for tid, title, body, priority, assignee, created_at, contract_json in backlog_tasks:
        if len(promoted) >= available_slots:
            break

        # Check dependency satisfaction
        dependencies = []
        if contract_json:
            try:
                contract = json.loads(contract_json)
                dependencies = contract.get("dependencies", [])
            except (json.JSONDecodeError, TypeError):
                dependencies = []

        deps_satisfied = True
        for dep_id in dependencies:
            cur.execute(
                "SELECT status FROM tasks WHERE id = ? AND project_id = ?",
                (dep_id, PROJECT_ID),
            )
            dep_row = cur.fetchone()
            if not dep_row or dep_row[0] != "Done":
                deps_satisfied = False
                log(f"Skipping {tid}: dependency {dep_id} not Done (status={dep_row[0] if dep_row else 'missing'})")
                break

        if not deps_satisfied:
            continue

        # Promote to Ready
        cur.execute(
            """
            UPDATE tasks
            SET status = 'Ready'
            WHERE id = ? AND project_id = ? AND status = 'Backlog'
            """,
            (tid, PROJECT_ID),
        )
        cur.execute(
            """
            INSERT INTO task_events (task_id, kind, payload, created_at)
            VALUES (?, 'status_change', ?, ?)
            """,
            (
                tid,
                json.dumps({"from": "Backlog", "to": "Ready", "reason": "backlog_promotion"}),
                now_ts(),
            ),
        )
        conn.commit()
        promoted.append(tid)
        log(f"Promoted {tid} from Backlog to Ready")

    return promoted


def run_check_links():
    """Run check_links.py in the repo and return (passed, output)."""
    import subprocess
    try:
        result = subprocess.run(
            ["python3", "scripts/check_links.py"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def discover_backlog_gaps(conn):
    """
    Inspect the repository and domain progress to find engineering gaps.
    Creates new Ready tasks for missing items.
    Returns list of created task IDs.
    """
    created = []
    domain_gaps = {
        "TASK-008.6-E01": [
            ("TASK-008.7-E01-G01", "Create kubernetes/control-plane/scaling-procedures.md",
             "Document cluster scaling procedures: add/remove control-plane and worker nodes, auto-scaling configuration.", 3),
            ("TASK-008.7-E01-G02", "Create kubernetes/acceptance-tests.md",
             "Define cluster acceptance tests: control-plane health, etcd quorum, node readiness, network connectivity.", 3),
        ],
        "TASK-008.6-E02": [
            ("TASK-008.7-E02-G01", "Create kubespray/upgrade-validation.md",
             "Document Kubespray 2.32 upgrade validation procedure: pre-upgrade checks, upgrade execution, post-upgrade validation.", 2),
            ("TASK-008.7-E02-G02", "Create kubespray/offline-deployment-test.md",
             "Create end-to-end offline deployment test procedure: air-gapped environment, image mirroring, OS packages, bootstrap validation.", 2),
        ],
        "TASK-008.6-E04": [
            ("TASK-008.7-E04-G01", "Create storage/ceph/performance-tuning.md",
             "Document Ceph performance tuning: OSD tuning, pool configuration, CRUSH rules, cache tiers.", 3),
            ("TASK-008.7-E04-G02", "Create storage/migration-procedure.md",
             "Document storage migration procedure: PVC migration between StorageClasses, pool migration, data evacuation.", 3),
        ],
        "TASK-008.6-E05": [
            ("TASK-008.7-E05-G01", "Create lifecycle/disaster-recovery/backup-drill-evidence.md",
             "Document backup drill execution evidence: drill scenarios, results, RPO/RTO measurements, sign-off.", 2),
            ("TASK-008.7-E05-G02", "Create lifecycle/disaster-recovery/app-cluster-restore-validation.md",
             "Document application cluster restore validation procedure: Velero restore, PVC reattachment, workload verification.", 2),
        ],
        "TASK-008.6-E06": [
            ("TASK-008.7-E06-G01", "Create kubernetes/networking/cilium-ebpf-deep-dive.md",
             "Document Cilium eBPF deep-dive: XDP, load balancing, routing, NAT, performance considerations.", 3),
            ("TASK-008.7-E06-G02", "Create kubernetes/networking/network-policy-examples.md",
             "Create NetworkPolicy examples: default deny, namespace isolation, service-to-service communication.", 2),
        ],
        "TASK-008.6-E07": [
            ("TASK-008.7-E07-G01", "Create offline-artifacts/sbom-generation.md",
             "Document SBOM generation procedure: Syft/Trivy SBOM creation, verification, storage, distribution.", 3),
            ("TASK-008.7-E07-G02", "Create offline-artifacts/offline-upgrade-test.md",
             "Create offline upgrade end-to-end test procedure: upgrade validation in air-gapped environment.", 2),
        ],
        "TASK-008.6-E08": [
            ("TASK-008.7-E08-G01", "Create automation/ansible/idempotency-test-suite.md",
             "Document Ansible idempotency test suite: changed-when assertions, idempotency verification, test playbooks.", 3),
            ("TASK-008.7-E08-G02", "Create automation/terraform/state-migration-procedure.md",
             "Document Terraform state migration procedure: backend migration, state locking, state import.", 3),
        ],
        "TASK-008.6-E09": [
            ("TASK-008.7-E09-G01", "Create secrets-management/vault/ha-deployment.md",
             "Document Vault HA deployment: raft storage, auto-unseal, standby nodes, performance standby.", 2),
            ("TASK-008.7-E09-G02", "Create secrets-management/kubernetes-auth-config.md",
             "Document Kubernetes auth method configuration for Vault: auth role, service account, token review.", 2),
        ],
        "TASK-008.6-E10": [
            ("TASK-008.7-E10-G01", "Create monitoring/ceph-dashboards.md",
             "Document Ceph Grafana dashboards: cluster health, OSD performance, PG status, capacity planning.", 3),
            ("TASK-008.7-E10-G02", "Create monitoring/network-observability-runbook.md",
             "Document network observability runbook: Cilium Hubble, flow logs, connectivity troubleshooting.", 3),
        ],
        "TASK-008.6-E11": [
            ("TASK-008.7-E11-G01", "Create management-cluster/argocd/installation-guide.md",
             "Create Argo CD installation guide: installation, configuration, application setup, sync waves.", 2),
            ("TASK-008.7-E11-G02", "Create management-cluster/argocd/fleet-argocd-decision-matrix.md",
             "Create Fleet vs Argo CD decision matrix: use cases, ownership boundaries, migration criteria.", 2),
        ],
        "TASK-008.6-E12": [
            ("TASK-008.7-E12-G01", "Create security/image-signing-procedure.md",
             "Document image signing procedure: cosign key generation, signing pipeline, verification at deployment.", 2),
            ("TASK-008.7-E12-G02", "Create security/sbom-generation-pipeline.md",
             "Document SBOM generation pipeline: automated SBOM creation, storage, vulnerability correlation.", 2),
        ],
        "TASK-008.6-E13": [
            ("TASK-008.7-E13-G01", "Create tests/integration-test-suite.md",
             "Document integration test suite: test scenarios, test environment, execution procedure, pass/fail criteria.", 3),
            ("TASK-008.7-E13-G02", "Create tests/failure-scenario-tests.md",
             "Document failure scenario tests: node failure, network partition, etcd quorum loss, control plane failure.", 3),
        ],
        "TASK-008.6-E14": [
            ("TASK-008.7-E14-G01", "Create repository/duplicate-detection.md",
             "Document duplicate detection procedure: identify duplicate documentation, conflicting content, consolidation candidates.", 3),
            ("TASK-008.7-E14-G02", "Create repository/cross-reference-validation.md",
             "Document cross-reference validation: automated validation of all doc cross-references, broken link prevention.", 3),
        ],
    }

    cur = conn.cursor()
    for epic_id, gaps in domain_gaps.items():
        # Check if Epic exists
        cur.execute(
            "SELECT id FROM tasks WHERE id = ? AND project_id = ?",
            (epic_id, PROJECT_ID),
        )
        if not cur.fetchone():
            continue
        for tid, title, body, priority in gaps:
            cur.execute(
                "SELECT id FROM tasks WHERE id = ? AND project_id = ?",
                (tid, PROJECT_ID),
            )
            if cur.fetchone():
                continue
            create_task(conn, tid, title, body, epic_id, priority=priority,
                        workstream=epic_id)
            created.append(tid)
            log(f"Backlog discovery: created {tid} — {title}")

    return created


def main():
    log("=== TASK-008.7 Supervisor cycle started ===")
    state = load_state()
    state["last_updated"] = now_iso()
    state["total_executions"] = state.get("total_executions", 0) + 1

    conn = kanban_connect()
    queue_state, total = get_queue_state(conn)
    state["kanban_state"] = queue_state

    log(f"Kanban state: {queue_state} (total: {total})")

    # Check for stalled In Progress tasks (>24h)
    in_progress = get_in_progress_tasks(conn)
    for tid, title, assignee, started_at in in_progress:
        if started_at:
            age_hours = (now_ts() - started_at) / 3600
            if age_hours > 24:
                log(f"Stalled task detected: {tid} ({title}) — {age_hours:.1f}h old")
                record_event(conn, tid, "stall_detected", {
                    "age_hours": age_hours,
                    "assignee": assignee,
                })

    ready_tasks = get_ready_tasks(conn)
    log(f"Ready tasks: {len(ready_tasks)}")

    dispatch_queue = None
    if ready_tasks:
        # Select eligible tasks respecting WIP limits
        eligible = select_eligible_tasks(conn, max_dispatch=3)

        if eligible:
            # Assign agents based on task domain
            agent_assignments = {}
            for tid, title, body, priority, assignee, created_at in eligible:
                agent_assignments[tid] = agent_for_task(tid, title, body)

            # Move selected tasks to In Progress
            tracker = load_worker_tracker()
            session_ids = []
            for tid, title, body, priority, assignee, created_at in eligible:
                agent = agent_assignments[tid]
                session_id = str(uuid.uuid4())
                move_task(conn, tid, "In Progress", assignee=agent)
                record_event(conn, tid, "dispatched", {
                    "agent": agent,
                    "session_id": session_id,
                    "dispatched_at": now_iso(),
                })
                register_worker(tracker, tid, agent, session_id, now_iso())
                session_ids.append(session_id)
                log(f"Dispatched {tid} to {agent} (session={session_id})")

            # Write dispatch queue for orchestrator processing
            dispatch_queue = write_dispatch_queue(eligible, agent_assignments, session_ids)
            state["last_dispatch"] = {
                "dispatch_id": dispatch_queue["dispatch_id"],
                "task_count": len(dispatch_queue["items"]),
                "at": now_iso(),
            }
        else:
            log("No eligible tasks for dispatch (WIP limits reached or no unassigned Ready tasks)")
    else:
        state["consecutive_empty_backlog_cycles"] = state.get("consecutive_empty_backlog_cycles", 0) + 1
        log("Ready column empty — checking backlog for promotion")

        # Promote eligible Backlog tasks to Ready
        promoted = promote_backlog_tasks(conn, max_promote=3)
        if promoted:
            state["consecutive_empty_backlog_cycles"] = 0
            log(f"Backlog promotion: {len(promoted)} tasks moved to Ready")
            ready_tasks = get_ready_tasks(conn)
            # Dispatch newly promoted tasks
            eligible = select_eligible_tasks(conn, max_dispatch=3)
            if eligible:
                agent_assignments = {}
                for tid, title, body, priority, assignee, created_at in eligible:
                    agent_assignments[tid] = agent_for_task(tid, title, body)
                tracker = load_worker_tracker()
                session_ids = []
                for tid, title, body, priority, assignee, created_at in eligible:
                    agent = agent_assignments[tid]
                    session_id = str(uuid.uuid4())
                    move_task(conn, tid, "In Progress", assignee=agent)
                    record_event(conn, tid, "dispatched", {
                        "agent": agent,
                        "session_id": session_id,
                        "dispatched_at": now_iso(),
                    })
                    register_worker(tracker, tid, agent, session_id, now_iso())
                    session_ids.append(session_id)
                    log(f"Dispatched {tid} to {agent} (session={session_id})")
                dispatch_queue = write_dispatch_queue(eligible, agent_assignments, session_ids)
                state["last_dispatch"] = {
                    "dispatch_id": dispatch_queue["dispatch_id"],
                    "task_count": len(dispatch_queue["items"]),
                    "at": now_iso(),
                }
        else:
            log("No eligible Backlog tasks for promotion — performing backlog discovery")
            created = discover_backlog_gaps(conn)
            log(f"Backlog discovery created {len(created)} new tasks")
            if created:
                state["consecutive_empty_backlog_cycles"] = 0
                ready_tasks = get_ready_tasks(conn)
                eligible = select_eligible_tasks(conn, max_dispatch=3)
                if eligible:
                    agent_assignments = {}
                    for tid, title, body, priority, assignee, created_at in eligible:
                        agent_assignments[tid] = agent_for_task(tid, title, body)
                    tracker = load_worker_tracker()
                    session_ids = []
                    for tid, title, body, priority, assignee, created_at in eligible:
                        agent = agent_assignments[tid]
                        session_id = str(uuid.uuid4())
                        move_task(conn, tid, "In Progress", assignee=agent)
                        record_event(conn, tid, "dispatched", {
                            "agent": agent,
                            "session_id": session_id,
                            "dispatched_at": now_iso(),
                        })
                        register_worker(tracker, tid, agent, session_id, now_iso())
                        session_ids.append(session_id)
                        log(f"Dispatched {tid} to {agent} (session={session_id})")
                    dispatch_queue = write_dispatch_queue(eligible, agent_assignments, session_ids)
                    state["last_dispatch"] = {
                        "dispatch_id": dispatch_queue["dispatch_id"],
                        "task_count": len(dispatch_queue["items"]),
                        "at": now_iso(),
                    }
            else:
                log("No new backlog tasks discovered — organization is caught up")

    # Save state
    save_state(state)
    conn.close()

    if dispatch_queue:
        log(f"=== Supervisor cycle complete — {len(dispatch_queue['items'])} tasks dispatched ===")
    else:
        log(f"=== Supervisor cycle complete — {len(ready_tasks)} Ready tasks available for delegation ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
