# TASK 008.1 — Kanban Database Diagnosis

**Task:** TASK 008.1 — Kanban Database Diagnosis

## 1. Database Path

**Verified path:** `/data/kanban.db` (NOT `/opt/data/kanban.db` — `/opt/data` does not exist)

## 2. File Permissions

| Item | Owner | Group | Mode | Notes |
|------|-------|-------|------|-------|
| /data | 10000 | 10000 | drwx------ (700) | Owner-only access |
| /data/kanban.db | 10000 | 10000 | -rw-r--r-- (644) | Owner rw, others r |
| /data/kanban.db-wal | 10000 | 10000 | -rw-r--r-- (644) | WAL file |
| /data/kanban.db-shm | 10000 | 10000 | -rw-r--r-- (644) | Shared memory |
| /data/kanban.db.dispatch.lock | 10000 | 10000 | -rw-r--r-- (644) | Dispatch lock |
| /data/kanban.db.init.lock | 10000 | 10000 | -rw-r--r-- (644) | Init lock |

## 3. Current Process Identity

- UID: 0 (root)
- GID: 0 (root)
- HOME: /root

## 4. Read Test (Passed)

```
sqlite3 connect → OK
7 tables: tasks, task_links, task_comments, sqlite_sequence, task_events, task_runs, task_attachments, kanban_notify_subs
```

## 5. Write Test (on temp copy, Passed)

Copied `/data/kanban.db` to `/tmp/kanban_test.db`, executed CREATE TABLE + INSERT + COMMIT → WRITE OK

## 6. Root Cause Diagnosis

The Kanban database is **owned by uid/gid 10000:10000** with the parent directory `/data` at mode **700 (owner-only)**.

The current terminal process runs as **root (uid 0)** and can read/write the database (root bypasses Unix permissions). However, the Hermes Gateway process likely runs as **uid 10000**, which:
- Can access `/data` (mode 700, owned by 10000)
- Can read/write `kanban.db` (mode 644, owned by 10000)

The "read-only" error observed earlier (`attempt to write a readonly database`) occurred in the `execute_code` kernel, which may run under different restrictions than the terminal. The direct SQLite write test on a copy succeeded, confirming SQLite itself can write.

**Most likely cause:** The `execute_code` execution context runs under a restricted user or SELinux/AppArmor policy that prevents writing to `/data/kanban.db`. The file-based task queue (under `/workspace`, which is mounted rw) works around this limitation.

## 7. Classification

**Permission/ownership issue** — The Kanban DB is owned by 10000:10000 with restrictive parent directory permissions. The `execute_code` context cannot write to it. The file-based task queue under `/workspace` (rw mount) is the working alternative.

## 8. Remediation (Not Applied)

Would require either:
- Running the dispatcher under uid 10000 to match file ownership
- Or adjusting permissions on `/data/kanban.db` (requires explicit authorization — not performed)

**Decision:** File-based task queue under `/workspace/release-artifacts/` is used instead. Kanban DB remains as read-only reference.
