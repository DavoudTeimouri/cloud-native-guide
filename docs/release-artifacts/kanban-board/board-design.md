# Cloud-Native Stack — Board Design

**Board name:** Cloud-Native Stack
**Board slug:** cloud-native-stack
**Project ID:** cloud-native-stack
**Created:** 2026-11-26T22:30:00Z
**Primary repository:** /workspace/project/github/public-repository/cloud-native-guide

## 1. Board Purpose

The Cloud-Native Stack Board is the central control plane for all project engineering activities. It drives autonomous execution through a Kanban-managed task lifecycle: Backlog → Ready → In Progress → Review → Testing → Blocked → Done.

## 2. Workflow Columns

| Column | WIP Limit | Color | Purpose |
|--------|-----------|-------|---------|
| Backlog | None | #6b7280 | Epics and tasks not yet prioritized |
| Ready | None | #3b82f6 | Dependencies satisfied, eligible for execution |
| In Progress | 3 | #f59e0b | Currently being worked on (max 3 concurrent) |
| Review | 2 | #8b5cf6 | Submitted for independent validation |
| Testing | 2 | #06b6d4 | Validation tests executing |
| Blocked | None | #ef4444 | Genuine conflict or dependency requiring decision |
| Done | None | #10b981 | Definition of Done satisfied, evidence recorded |

WIP limits prevent uncontrolled parallel work. In Progress is limited to 3, Review and Testing to 2 each.

## 3. Swimlanes (Engineering Domains)

1. Kubernetes & Kubespray
2. Storage & Ceph
3. Networking
4. Offline & Air-Gapped
5. Automation & IaC
6. Security
7. Monitoring & Observability
8. Disaster Recovery
9. GitOps & Platform Engineering
10. Repository Quality

## 4. Labels

**Technology labels:** kubernetes, kubespray, rancher, ceph, networking, offline, automation, security, monitoring, disaster-recovery, gitops, repository-quality

**Priority labels:** priority-critical, priority-high, priority-medium, priority-low

**Task type labels:** task-type-epic, task-type-feature, task-type-task, task-type-subtask

**Components:** Kubernetes Platform, Kubespray, Rancher, Ceph Storage, Rook-Ceph, Cilium Networking, Nexus/Harbor, Vault Secrets, Prometheus Monitoring, Argo CD GitOps, Ansible Automation, Terraform IaC, Repository Quality

## 5. Saved Views

- My Work — tasks assigned to current user
- Ready to Execute — status = Ready
- High Priority — priority <= 2
- Blocked — status = Blocked
- Review Required — status = Review
- Testing — status = Testing
- By Engineering Domain — grouped by swimlane
- Upcoming Milestones — due date in future
- Recently Completed — status = Done, sorted by completed_at desc

## 6. Notifications

- Blocked tasks: enabled
- Failed validations: enabled
- Review requests: enabled
- Completed milestones: enabled
- Worker failures: enabled
- Long-running tasks: disabled

## 7. Git Preservation Boundaries

- Primary repo HEAD: 7c40489c (unchanged)
- Remote main: ebbafc2aa (unchanged)
- Archival branch: archive/integration-reconcile-remote-content (intact)
- PR #2: open, unmerged, untouched
- Pre-existing user changes: 8 tracked + 4 untracked, preserved
- No push, merge, or PR modifications
- All work remains local until independent Review succeeds
