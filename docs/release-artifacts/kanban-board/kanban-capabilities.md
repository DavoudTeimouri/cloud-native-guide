# Kanban Capabilities — TASK-008.6

**Kanban database:** /data/kanban.db
**Projects database:** /data/projects.db
**Hermes Gateway:** pid 173, version 0.23.4, API 127.0.0.1:8642

## 1. Supported Capabilities (Verified)

| Capability | Supported | Implementation |
|------------|-----------|----------------|
| Multiple Boards | Yes | projects.db `projects` table with `board_slug` |
| Board-specific columns | Yes | project_meta `board_config` JSON |
| Projects and Epics | Yes | projects.db + kanban.db `tasks` with `project_id` |
| Swimlanes | Yes | project_meta `board_config` swimlanes array |
| Labels and components | Yes | project_meta `board_config` labels/components arrays |
| Priority levels | Yes | tasks `priority` INTEGER (1=highest) |
| Task assignments | Yes | tasks `assignee` TEXT |
| WIP limits | Yes | project_meta `board_config` wip_limits |
| Dependencies and blocking | Yes | task_links parent_id/child_id + tasks block_kind |
| Comments and discussions | Yes | task_comments table |
| Attachments and evidence | Yes | task_attachments table + completion_contract JSON |
| Task execution history | Yes | task_events table |
| Notifications | Yes | kanban_notify_subs table |
| Automation rules | Yes | project_meta `board_config` automation_rules array |
| Saved views and filters | Yes | project_meta `board_config` saved_views array |
| Due dates and milestones | No | Not in schema — documented as limitation |
| Board-level reporting | No | Not in schema — documented as limitation |
| Activity history | Yes | task_events table |
| Recurring tasks | No | Not in schema — documented as limitation |

## 2. Unsupported Capabilities (Documented)

| Capability | Reason | Alternative |
|------------|--------|-------------|
| Due dates and milestones | No column in tasks schema | Use task title/body for date info |
| Board-level reporting | No reports table | Query task_events and tasks directly |
| Recurring tasks | No recurrence schema | Create new tasks manually per cycle |

## 3. Task Status Lifecycle

| Status | Meaning |
|--------|---------|
| Backlog | Epic or task not yet prioritized |
| Ready | Dependencies satisfied, eligible for execution |
| In Progress | Currently being worked on |
| Review | Submitted for independent validation |
| Testing | Validation tests executing |
| Blocked | Genuine conflict or dependency requiring decision |
| Done | Definition of Done satisfied, evidence recorded |

## 4. Task Fields

Every task has: id, title, body, assignee, status, priority, created_by, created_at, started_at, completed_at, workspace_kind, workspace_path, branch_name, project_id, claim_lock, claim_expires, tenant, result, completion_contract (JSON), block_kind, worker_pid, and more.
