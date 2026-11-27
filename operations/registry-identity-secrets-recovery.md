# Section 7 (Registry Portion): Nexus/Harbor + Keycloak Recovery

## Guiding Principles

- **Config-only backups are insufficient for stateful services** — Registry and identity services store critical data in databases, object storage, and TLS caches. A backup of configuration files alone does not guarantee recoverability.
- **Never include actual secrets, recovery keys, or tokens in documentation** — All examples use placeholder paths and omit sensitive values. Real secrets must be stored in External Secrets, Vault, or hardware security modules, never in Git or markdown.
- **Verify before restore** — All recovery commands must be validated against the current service state before execution. Test in isolated environment first.
- **Data-loss-risk operations** — Clearly identified. Require specialist review, stakeholder sign-off, and a tested rollback path.

---

## 7.1 Nexus Repository Manager Recovery

Nexus stores three categories of data: **configuration/metadata** (stored in an embedded H2 or external PostgreSQL/Oracle database), **blobs/artifacts** (stored in the file system or object storage), and **RBAC/project configuration** (also in the database). Recovery requires restoring all three categories in the correct order.

| Artifact Category | Storage Location | Backup Procedure | Restore Procedure | Data-loss Risk |
|---|---|---|---|---|
| **Configuration + Metadata** | Embedded H2 database (default) or external PostgreSQL/Oracle instance | `nexus backup -name <backup-name>` — creates a ZIP of config + DB snapshot <br>Or: `pg_dump` / `oracle exp` on external DB if used | `nexus restore -from <backup-zip>` <br>Or: restore DB dump to same/newer DB version, then `nexus restart` | **Low** — if backup includes both config ZIP and DB dump; **High** if only config files are backed up (metadata lost) |
| **Blobs / Artifacts** | `${NEXUS_DATA}/sonatype-work/sonatype-work/nexus3/` (file system) or S3-compatible object storage (cloud mode) | `tar czf /backup/nexus-blobs-$(date +%F).tar.gz ${NEXUS_DATA}/sonatype-work/sonatype-work/nexus3/` <br>Or: if using S3 backend, ensure bucket has versioning enabled; copy bucket contents to off-site storage | Restore from tar: `tar xzf /backup/nexus-blobs-$(date +F).tar.gz -C ${NEXUS_DATA}/` <br>Or: sync from off-site S3 bucket; ensure `nexus` user has write access | **Medium** — blob tar includes all artifacts; if only metadata backup exists, blobs are lost. Cloud mode: verify S3 bucket versioning and object integrity after restore |
| **RBAC + Project Configuration** | Embedded in the same database as configuration (PostgreSQL/Oracle) | Included in `nexus backup` ZIP <br>Or: `pg_dump -Fc nexus > /backup/nexus-db-$(date +%F).dump` | `nexus restore` includes RBAC restoration <br>Or: `pg_restore -d nexus /backup/nexus-db-$(date +%F).dump` | **Low** — RBAC and project mappings are preserved if DB backup is complete and restorable; **High** if only config files are restored (RBAC lost, users must be re-created) |
| **TLS Certificates + Trust Store** | `${NEXUS_DATA}/security/` or external KeyStore | `cp /opt/sonatype/sonatype-work/nexus3/security /backup/nexus-security-$(date +%F).tar.gz` <br>Also back up `cacerts` trust store if customized | `cp /backup/nexus-security-$(date +%F).tar.gz /opt/sonatype/sonatype-work/nexus3/` <br>`chown nexus:nexus <restored-path>` <br>`systemctl restart nexus` | **Low** — certificates are restored; if original certs are expired or lost, may need to regenerate via CSR or import from offline CA |
| **Replication / Sync State** (Nexus Repository Fleet) | Replication groups configuration + status | `nexus repo-replication-group list` to capture config; replicate blobs to remote Nexus | If primary Nexus lost: restore primary from backup <br>Then re-establish replication groups; verify sync state via `nexus repo-replication-group status` | **Medium** — replication lag may mean some blobs are only on primary; RPO depends on replication frequency; full sync may take hours |
| **Metadata-Artifact Consistency** | Index of blobs vs. actual files on disk | After restore: run `nexus check` or `nexus blob-check` (if available) <br>Compare DB record count vs. file system object count | Resolve any inconsistencies via `nexus blob-delete` / `nexus blob-recover`; re-index if needed | **Low** — consistency check is preventive; if inconsistency exists before backup, it propagates |

> ** Specialist review required **: Nexus recovery that relies only on configuration file backup (without DB dump and blob archive) is **insufficient**. Must verify that the backup includes all three categories: config/metadata, blobs/artifacts, and RBAC. Any missing category requires a separate recovery procedure and increases data-loss risk.

---

## 7.2 Harbor Registry Recovery

Harbor stores configuration in a PostgreSQL database, blobs in object storage (S3/Swift/CEPH RGW), and TLS certificates in the filesystem. Recovery requires restoring the database, verifying object storage accessibility, and restoring TLS materials.

| Artifact Category | Storage Location | Backup Procedure | Restore Procedure | Data-loss Risk |
|---|---|---|---|---|
| **Configuration + Metadata** | Harbor's internal PostgreSQL database (tables: `projects`, `repositories`, `users`, `artifacts`, etc.) | `pg_dump -Fc harbor > /backup/harbor-db-$(date +%F).dump` <br>Include Harbor core config: `/etc/harbor/harbor.yml` | `pg_restore -d harbor /backup/harbor-db-$(date +%F).dump` <br>Restore config: `cp /backup/harbor.yml /etc/harbor/` <br>`systemctl restart harbor-portal` <br>`systemctl restart harbor-jobworker` | **Low** — if DB dump is complete and restorable; **High** if only config files are restored (DB lost; all project configs, mappings, and metadata must be re-created) |
| **Blobs / Artifacts** | Backend object storage: S3, Swift, Ceph RGW, or embedded file storage | If using cloud storage: ensure bucket has versioning enabled; copy bucket contents to off-site bucket <br>If using local file storage: `tar czf /backup/harbor-blobs-$(date +%F).tar.gz ${HARBOR_DATA}/harbor/hub/` | If cloud: sync from off-site bucket; verify `aws s3 cp --recursive s3://backup-bucket/harbor/ ${HARBOR_OBJECT_BUCKET}/` <br>If local: `tar xzf /backup/harbor-blobs-$(date +%F).tar.gz -C ${HARBOR_DATA}/` | **Medium** — cloud mode: depends on bucket versioning and off-site copy lag; **High** if local file storage and no off-site copy: blobs lost when volume is deleted or corrupted |
| **TLS Certificates + Private Keys** | `/etc/harbor/certs/` or mounted PKI volume | `cp /etc/harbor/certs /backup/harbor-certs-$(date +%F).tar.gz` <br>Also back up CA chain and intermediate certs | `cp /backup/harbor-certs-$(date +%F).tar.gz /etc/harbor/certs/` <br>`chmod 440 /etc/harbor/certs/*.key` <br>`systemctl restart harbor` | **Medium** — private key restoration is critical; if keys are lost and no CSR/offline CA exists, certificates must be re-generated and all artifacts re-encrypted; **never store recovery keys in markdown or Git** |
| **Harbor RBAC + Project Config** | Same PostgreSQL DB as configuration (projects, users, permissions) | Included in `pg_dump` above | Restored automatically with `pg_restore` | **Low** — same as configuration/metadata risk |
| **Replication / Sync State** (Haror replica) | Replication worker state + remote registry sync status | `harctl replication status` to capture state; replicate blobs to replica | If primary lost: restore primary from DB + blob backup <br>Then re-establish replica: `harctl replication enable` <br>Verify sync: `harctl replication status` | **Medium** — async replication means RPO defined by sync interval; some artifacts may be only on primary; full catch-up may take hours to days |
| **Harbor Registry Garbage Collection** | Old/dangling image manifests | `harbor gc` run after restore to clean up | Run `harbor gc` manually after data verification | **Low** — GC is safe; removes only truly orphaned layers |

> ** Specialist review required **: Harbor DB restore requires the PostgreSQL version match between backup creation and restore. A `pg_dump` from PostgreSQL 13 cannot be restored into PostgreSQL 12 without compatibility adjustments. Always verify the DB version compatibility before starting restore. Also: private key restoration must be verified against the original CSR or offline CA — never assume restored keys match originals without verification.

---

## 7.3 Keycloak Recovery

Keycloak stores realm configurations, client mappings, and user credentials in a PostgreSQL or MySQL database. TLS certificates and OIDC IdP metadata are stored on the filesystem. Recovery requires DB restore + filesystem restoration + IdP/OIDC re-configuration.

| Artifact Category | Storage Location | Backup Procedure | Restore Procedure | Data-loss Risk |
|---|---|---|---|---|
| **Realm + Client Configuration** | Keycloak's internal database (PostgreSQL/MySQL) | `pg_dump -Fc keycloak > /backup/keycloak-db-$(date +%F).dump` <br>Or: `mysqldump -u keycloak -p keycloak > /backup/keycloak-db-$(date +%F).sql` | `psql -U keycloak -d keycloak < /backup/keycloak-db-$(date +%F).dump` <br>Or: `mysql -u keycloak -p keycloak < /backup/keycloak-db-$(date +%F).sql` | **Low** — DB dump is standard; verify `SELECT count(*) FROM realm;` and `SELECT count(*) FROM client;` after restore |
| **User Credentials + Credentials Mappings** | Same DB as realms/clients (password hashes, OIDC client secrets) | Included in `pg_dump`/`mysqldump` above | Restored automatically | **Medium** — password hashes are restored; if DB master key is lost, some encrypted fields may be inaccessible; **never store master keys in markdown or Git** |
| **TLS Certificates + Private Keys** | `${KEYCLOAK_CONFIG}/server.keystore` or mounted volume | `cp /opt/keycloak/keycloak/${VERSION}/conf/server.keystore /backup/keycloak-keystore-$(date +%F).jks` <br>Also back up `tls.crt` + `tls.key` if separate | `cp /backup/keycloak-keystore-$(date +%F).jks /opt/keycloak/keycloak/${VERSION}/conf/` <br>`chmod 600 /opt/keycloak/keycloak/${VERSION}/conf/server.keystore` <br>`systemctl restart keycloak` | **Medium** — keystore restoration requires the original keystore password; if password is lost, certificates must be regenerated via CSR or imported from offline CA |
| **OIDC IdP Metadata + Federation Config** | Filesystem: `${KEYCLOAK_CONFIG}/providers/` or DB (federation records) | `cp -r /opt/keycloak/keycloak/${VERSION}/providers /backup/keycloak-providers-$(date +%F).tar.gz` <br>Also export IdP metadata via Keycloak admin UI: `Export` → `File` → download XML | Restore providers: `cp -r /backup/keycloak-providers-$(date +%F).tar.gz /opt/keycloak/keycloak/${VERSION}/` <br>`systemctl restart keycloak` <br>Or: import via Admin UI: `Authentication → Add provider → Import` | **Low** — provider config is restored; if OIDC endpoints changed or IdP metadata URL updated, may need to re-configure after restore |
| **Refresh Token + Session Data** | DB (session table) + Redis (if configured as session store) | Include in DB dump; if Redis: `redis-cli SAVE` or RDB snapshot | Sessions restored with DB dump; Redis RDB restored if separate backup | **Medium** — active user sessions may be lost if session store not fully restored; users may need to re-authenticate; SSO sessions terminated |
| **RBAC + Group Mappings** | Same DB as realms; groups, role mappings, client scopes | Included in DB dump | Restored automatically | **Low** — same as realm/config risk |

> ** Specialist review required **: Keycloak DB restore requires the database version to match or be compatible with the Keycloak version being restored. A dump from Keycloak 23 may not restore cleanly into a Keycloak 22 database schema. Always test restore in a non-production environment first. Also: keystore password must be recovered from a separate secret store (Vault, External Secrets, or offline record) — never derive from the keystore file itself.

---

## 7.4 Vault/OpenBao Recovery

Vault (and OpenBao, its open-source fork) stores secrets, PKI certificates, and encryption keys. Recovery includes storage backend backup, Raft snapshot restore, and unseal material reconstruction. **This section covers only backup/restore of Vault data plane; admission enforcement (policy ACLs, token routing) is covered elsewhere.**

### Supported Storage Backend Backup

Vault supports multiple storage backends. Backup method depends on the backend in use:

- **Consul**: Raft snapshot is the primary backup mechanism; Consul data directory (`/opt/consul`) must be included in off-site backup.
- **Etcd**: `etcdctl snapshot save` produces a point-in-time quiesced snapshot; etcd WAL files must also be preserved for complete recovery.
- **PostgreSQL**: `pg_dump` of the Vault `seal` and `identity` tables; the `sys` schema contains critical encryption keys.
- **MySQL**: `mysqldump` of the Vault database; same considerations as PostgreSQL.
- **Filesystem**: `tar` of the Vault data directory (`/var/lib/vault`) — only valid if no in-memory state is lost; Raft snapshots take precedence.

> **Rule of thumb**: For all backups, the Raft snapshot is the authoritative source. Any backend-specific dump is supplementary and must be restored *after* the Raft snapshot is applied.

### Raft Snapshot Considerations

Vault's Raft consensus group is the source of truth for all sealed and unsealed state. Snapshots capture the cluster state at a point in time.

- **Snapshot command**: `vault operator raft snapshot save <path>` — writes a `.snap` file accessible inside the Vault container/VM.
- **Snapshot frequency**: At least daily; additionally before any upgrade, configuration change, or node replacement.
- **Off-site copy**: Snapshots must be copied to off-site storage (S3, Ceph RGW, GS) immediately after creation; do not rely on the same cluster disk.
- **Retention**: Keep a minimum of 7 daily, 4 weekly, and 1 monthly snapshot. Retention policy must be documented and tested.
- **Peer consistency**: `vault operator raft list-peers` must show all expected nodes before and after restore. A quorum (>= 3 for 5-node cluster, >= 2 for 3-node cluster) must be available to proceed.

> **Critical**: A Raft snapshot without the corresponding unseal material is useless. Backup both the snapshot and the unseal keys/seal configuration in the same operation.

### Unseal + Recovery Key Protection

Vault unseal material is the highest-value secret in the system. Loss of unseal keys = permanent data loss.

- **Shamir's Secret Sharing**: Default is 3 of 5 shards; each shard must be stored independently (physical safe, HSM, cloud KMS split).
- **Shard storage**: Never store all 5 shards in the same location. Use geographically distributed custodians.
- **Recovery key rotation**: Annual rotation is recommended; each rotation generates new shards and invalidates old ones.
- **Never in code or Git**: Unseal keys, root tokens, and recovery paths must never appear in repository, CI artifacts, or configuration files.
- **Admission enforcement distinction**: Unseal material is separate from admission controller policies. Admission enforcement governs *who can* unseal; unseal material is the *ability* to unseal. Loss of admission policies does not unseal the cluster — only the unseal keys do.

> **Distinction from admission enforcement**: Admission plugins (e.g., OPA, Kyverno) may gate Vault operations, but they do not replace the need for unseal material. A cluster with all admission policies intact but no unseal keys is still sealed. A cluster with unseal keys but no admission policies is operational (less restrictive, but operational).

### Seal Configuration + Recovery Dependencies

The seal determines how Vault protects data at rest. Recovery depends on the seal type.

| Seal Type | Backup/Recovery Method | Dependencies |
|---|---|---|
| **Unseal Shards (Shamir)** | Store 3 of 5 shards offline; use `vault operator unseal` to reconstruct | Custodian quorum, shard storage location |
| **KMS Auto-Unseal** | KMS key ID / ARN must be available; no local backup needed if KMS is external and durable | External KMS endpoint, IAM/role permissions |
| **Sealed Storage (e.g., File)** | Backup the encrypted seal data directory; recovery requires the same seal config + passphrase | Filesystem path, passphrase/key location |
| **Hybrid** | Combine shards + KMS; document which component is authoritative | Both shard storage and KMS access |

> **Recovery dependency order**: 1) Raft snapshot restore, 2) Unseal all nodes, 3) Start Vault, 4) Verify storage backend connectivity, 5) Restore secrets from application perspective.

### Restore + Post-Restore Validation

Restore is a coordinated, multi-step operation. Do not skip steps or reorder.

#### Restore Procedure

1. **Snapshot availability**: Confirm the Raft snapshot file exists at the expected path; verify checksum if available.
2. **Node preparation**: Stop Vault on all nodes `vault operator leave` if joining an existing cluster, or ensure clean state for fresh restore.
3. **Restore on first node** (becomes leader):
   ```bash
   vault operator raft snapshot restore /backup/vault-snapshot-<timestamp>.snap
   ```
4. **Start first node**: `systemctl start vault` (or equivalent).
5. **Wait for leader election**: `vault operator raft list-peers` — confirm the restored node is the leader.
6. **Start remaining nodes**: `systemctl start vault` on each; they will join the Raft cluster automatically.
7. **Unseal all nodes**: Provide the unseal shard(s) for each node via `vault operator unseal`.
8. **Verify cluster status**: `vault status` — must show `Sealed: false` and `HA: true` (if configured).

#### Post-Restore Validation

- `vault status` — `Sealed: false`, active lease count matches expectation.
- `vault operator raft list-peers` — all expected peers listed; no split-brain.
- `vault kv get <path>` — read back a known secret; data must match pre-loss state.
- `vault policy list` / `vault token list` — policies and tokens are present (they are stored in the Raft log).
- `vault auth list` — auth methods are configured; test a login with a known token.
- **Application-level check**: Deploy a workload that reads a secret from Vault; verify it resolves without error.

> **Do NOT** treat a restore as complete simply because `vault status` shows `Sealed: false`. Application-level secret resolution is the definitive validation.

### Distinguish from Admission Enforcement

A common point of confusion: admission enforcement (OPA, Kyverno, etc.) governs *authorized* operations on the Vault cluster — who can read, write, unseal, or rotate. It does not govern *data survival*.

- **Admission enforcement lost**: Policies are missing; the cluster may still operate with reduced guards, but no new operations are blocked/unblocked based on policy. Recovery: re-apply admission policies from version-controlled templates.
- **Unseal material lost**: Cluster is permanently sealed; no amount of admission policy re-application will unseal it. Recovery: restore unseal shards or KMS configuration *before* the cluster can accept any operation.

> **Memory aid**: Admission = "who can operate." Unseal = "whether the cluster is unlocked." One is a policy gate; the other is a physical/logical lock. Confusing the two leads to incomplete recovery drills.

--

## 7.5 Statefullness Warning: Why Config-Only Backups Fail

| Service | Config-Only Backup Missing | Required Backup Components | Result if Only Config Restored |
|---|---|---|---|
| **Nexus** | Repository metadata, blob indices, RBAC mappings, user passwords | DB dump + blob archive + config + TLS | **Critical** — repository appears configured but has no artifacts; users cannot authenticate; RBAC must be re-created from scratch |
| **Harbor** | Project mappings, tag retention policies, user permissions, artifact data | DB dump + object storage backup + certs | **Critical** — registry API responds but no projects/repositories exist; all artifacts lost; TLS restored but users cannot push/pull |
| **Keycloak** | User passwords, client secrets, realm configs, federation mappings | DB dump + keystore + provider configs | **Critical** — login fails; users must be re-created; OIDC flows broken; all active sessions invalidated |

> ** Rule of thumb **: For all three services (Nexus, Harbor, Keycloak), a **valid backup** must include: (1) database dump with all schema and data, (2) TLS certificate/key materials, (3) object storage or file system blobs/artifacts, and (4) provider/IdP federation metadata. Config-only backups are insufficient and must not be relied upon for disaster recovery.

---

## 7.6 Recovery Ordering & Dependency Handling

### Recommended Recovery Order (total site loss)

1. **Network, DNS, NTP** — Ensure infrastructure connectivity before any service restore
2. **PostgreSQL / MySQL** — Restore database(s) first; all three services (Nexus, Harbor, Keycloak) depend on their DBs
3. **Artifact repositories** — Nexus and Harbor: restore blobs/object storage after DB is running
4. **Identity services** — Keycloak: restore after DB; verify realms and clients
5. **TLS certificates** — Restore after services are running; regenerate if expired or keys lost
6. **Service startup** — Restart Nexus, Harbor, Keycloak in order; verify each is healthy before proceeding
7. **SSO / OIDC validation** — Test Keycloak login; verify Harbor/Nexus access via Keycloak-authenticated flows
8. **Data consistency checks** — Run `nexus check`, `harbor gc`, Keycloak `realm export/import` to validate integrity

### Recovery Order (per-service, isolated)

1. **Nexus-only**: DB → Blobs → Config → TLS → Startup
2. **Harbor-only**: DB → Blobs → Certs → Startup
3. **Keycloak-only**: DB → Keystore → Providers → Startup

> ** Specialist review required **: Skipping the DB-first order leads to incomplete recovery — services may start but fail to load configuration, users cannot authenticate, and artifacts cannot be located. Always restore the database before any other component.

---

## 7.7 Validation Checklist — Post-Recovery

### Nexus Post-Recovery

- [ ] `nexus status` shows `Started`
- [ ] Repository listings work (both hosted and proxy)
- [ ] RBAC: user can log in; permissions are as expected
- [ ] Blob count matches pre-loss baseline (compare `du -sh ${NEXUS_DATA}/sonatype-work/sonatype-work/nexus3/`)
- [ ] Replication status: `nexus repo-replication-group status` shows expected groups synced
- [ ] TLS certificate valid and accessible via HTTPS

### Harbor Post-Recovery

- [ ] `harbor status` shows all components Running
- [ ] Project listings visible; projects match pre-loss configuration
- [ ] Image push/pull works for at least one known repository
- [ ] TLS certificate valid; HTTPS access functional
- [ ] Replication status: `harctl replication status` shows expected state
- [ ] GC has run and orphaned layers cleaned: `harbor gc`

### Keycloak Post-Recovery

- [ ] `keycloak status` shows server Running
- [ ] Login succeeds with at least one pre-existing user credential
- [ ] Realms listed and match pre-loss configuration
- [ ] Client mappings functional (at least one OIDC client usable)
- [ ] TLS certificate valid; HTTPS access to Keycloak admin works
- [ ] Active user sessions: verify `SELECT count(*) FROM session;` matches expected (or accept session loss with user re-authentication)
- [ ] Federation/OIDC: at least one IdP flow functional (test with test user)

> ** Specialist review required **: Any validation item that fails indicates incomplete recovery. Do not mark service as "recovered" until all critical path items pass. If DB version mismatch is detected, do not proceed with service startup — roll back and re-attempt with compatible backup.

---

**Infra Maintainer**: Platform Team
**Section**: 7 (Registry + Vault/OpenBao Portion) — Nexus/Harbor/Keycloak + Vault/OpenBao Recovery
**Status**: DRAFT | **Owner**: Infrastructure Maintainer
**Last reviewed**: 2026-11-25
**Review cycle**: Quarterly (verify off-site backup integrity, review RPO/RTO assumptions, rotate test credentials, validate Vault snapshot retention)
**No credentials, secrets, or recovery keys are included in this documentation**. All paths use placeholder conventions; real secrets must be stored in External Secrets, Vault, or hardware security modules.
**Do NOT execute** any restore commands against a live production service without specialist sign-off and a tested rollback path. These procedures are documented for reference and drill purposes only.

---
