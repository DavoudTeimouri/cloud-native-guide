# Step 11 — Day-2 Operations

**Purpose**: Operate the running stack — prove backups with drills, restore the control plane, run on-call, and recover registries and secrets. Re-run after any major change or incident.

**Prerequisites**: Steps 00–10 complete (stack deployed and validated per `en/cloud-native-stack-step-by-step.md`).

## 11.1 Backup drills

Run restore drills on a schedule, not after an incident. A backup that has never been restored is a hypothesis.

- **Velero**: daily-full schedule; restore into a scratch namespace; verify application data checksums. Record the measured RTO. See `../lifecycle/backup/backup-and-dr.md` §C (Velero) and §H (validation).
- **etcd**: snapshot cadence targets ≤ 1 min RPO / ≤ 30 min RTO; restore verified quarterly. See `../lifecycle/disaster-recovery/etcd-restore.md`.
- **Drill evidence**: recorded scenarios, actual RPO/RTO, sign-off. See `../lifecycle/disaster-recovery/backup-drill-evidence.md` and `../lifecycle/disaster-recovery/dr-exercises.md`.
- **Full rebuild order**: network/DNS/NTP → OS baseline → PKI → artifact repos → GitLab → identity → Vault → AWX → Ceph → Kubernetes → management cluster → Argo CD → GPU workers → applications. Steps 1–8 need no Kubernetes. See `../lifecycle/backup/backup-and-dr.md` §G.

**Validation**: last drill's measured RTO ≤ declared RTO; drill recorded in `backup-drill-evidence.md` with sign-off.

## 11.2 Control-plane restore

etcd is the authoritative control-plane backup; Velero does not cover etcd. A cluster restore without an etcd snapshot restores workloads onto a control plane with no cluster state.

- **Quorum math**: 3-node cluster needs 2 members; losing more than `floor(N/2)` members loses quorum entirely. See `../lifecycle/disaster-recovery/etcd-restore.md` §D.
- **Restore (same node)**: stop the etcd member, clear `/var/lib/etcd`, `etcdctl snapshot restore` into the data directory, restart, verify `member list` and `endpoint health --cluster`. See `etcd-restore.md` §B.
- **Restore (new node)**: place the snapshot on a fresh control-plane node, start etcd, verify it joins and reports healthy quorum. See `etcd-restore.md` §B "Etcd restore with a new node".

**Validation**: `kubectl get nodes` all Ready; `etcdctl endpoint health --cluster` healthy; API server `/readyz?verbose` ok.

## 11.3 On-call

On-call owns the first response to alerts: etcd quorum loss, node loss, registry outage, Vault seal, identity outage.

- **First hour**: declare the incident; check `kubectl get nodes`, etcd health, Ceph `ceph -s`, and Prometheus/Alertmanager dashboards.
- **Runbooks**: `../troubleshooting/README.md` indexes the etcd, Ceph, CNI, CSI, Vault, Argo CD, Registry Auth, and GPU runbooks.
- **Break-glass**: the local `emergency` account (UID 999, key-only) authenticates when directory/identity is unreachable (ADR-0015).
- **Handoff**: record actions, measured RTO, and gaps; update runbooks after every exercise.

## 11.4 Registry and secrets recovery

- **Harbor / Nexus**: restore DB (`pg_dump`) plus registry/storage object data from Ceph RGW. See `../lifecycle/backup/backup-and-dr.md` §B table.
- **Vault**: `vault operator raft snapshot save` / `restore`, then unseal with offline shares. The backup set must include the raft snapshot, unseal key shares, root token, and CA material — stored separately from the snapshot. A backup that cannot be unsealed is not a backup. See `../secrets-management/recovery/restore.md` and `../lifecycle/backup/backup-and-dr.md` §D.
- **GitLab**: `gitlab-backup create`; copy the tar to object storage; also back up repositories, LFS objects, registry data, config files, and the encryption keys/secrets file. See `../lifecycle/backup/backup-and-dr.md` §E.
- **PKI / TLS**: cert-manager re-issues leaf certs; PKI root material is imported into Vault PKI from offline media.

**Validation**: image pull works from a node after registry restore; Vault unseals and issues secrets; GitLab accepts commits.

---

[Next: Step 12 — Upgrades, Retirement & Decommission →](step-12-upgrades-retirement.md)
