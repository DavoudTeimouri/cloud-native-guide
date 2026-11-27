# TASK 008.2 — Hermes Directory Map

**Task:** TASK 008.2 — Hermes Directory Map

## Directory Layout

| Component | Path | Type | Evidence |
|-----------|------|------|----------|
| Hermes config | /data/config.yaml | File | `cat` shows provider: custom:9router |
| Cron directory | /data/cron/ | Directory | `ls` shows executions.db, ticker files |
| Kanban DB | /data/kanban.db | File | SQLite, 7 tables, 0 tasks |
| Kanban WAL | /data/kanban.db-wal | File | SQLite WAL file |
| Kanban SHM | /data/kanban.db-shm | File | SQLite shared memory |
| Dispatch lock | /data/kanban.db.dispatch.lock | File | Empty lock file |
| Init lock | /data/kanban.db.init.lock | File | Empty lock file |
| Gateway state | /data/gateway_state.json | File | pid:173, state:running, version:0.23.4 |
| Gateway PID | /data/gateway.pid | File | pid:173, hermes_home:/opt/data |
| Gateway socket | /data/gateway.sock | Socket | srw------- 10000:10000 |
| Workspace | /workspace/ | Directory | Mount: /dev/sda1 ext4 rw |
| Release artifacts | /workspace/release-artifacts/ | Directory | Task reports and deliverables |
| TASK-008.2 deliverables | /workspace/release-artifacts/TASK-008.2-runtime-integrity/ | Directory | This task's output |
| TASK-008.0 task queue | /workspace/release-artifacts/TASK-008.0-persistent-runtime/tasks/ | Directory | pending/, completed/, blocked/, in-progress/ |
| Dispatcher | /workspace/release-artifacts/TASK-008.0-persistent-runtime/dispatcher.py | File | Python dispatcher script |
| Dispatcher log | /workspace/release-artifacts/TASK-008.0-persistent-runtime/dispatcher-logs/dispatcher.log | File | Execution log |
| Cloud-native-guide repo | /workspace/project/github/public-repository/cloud-native-guide/ | Git repo | Original repository |
| Phase 7 worktree | /workspace/project/github/public-repository/cloud-native-guide.phase7/ | Git worktree | Isolated execution, 35 uncommitted changes |
| Phase 8 worktree | /workspace/project/github/public-repository/cloud-native-guide.phase8/ | Git worktree | Isolated execution, 0 uncommitted changes |
| Phase 1-6 worktrees | /workspace/project/github/public-repository/cloud-native-guide.phase{1-6}/ | Git worktrees | Committed, clean |

## HERMES_HOME

**Not defined as an environment variable.** Only `HOME=/root` and `HERMES_AGENT=true` are set. The gateway's pid file reports `hermes_home: /opt/data`, but `/opt/data` does not exist in this namespace. The actual data directory is `/data`.

## XDG Variables

`XDG_CONFIG_HOME` and `XDG_DATA_HOME` are not defined.

## Summary

The Hermes runtime uses `/data` as its data directory (not `/opt/data` as the gateway pid file suggests). All configuration, cron, Kanban, and gateway state files are under `/data`. The workspace is `/workspace`, mounted read-write.
