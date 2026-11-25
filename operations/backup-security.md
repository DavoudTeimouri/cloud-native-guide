# Section 9 — Backup Security and Immutability

*Illustrative only — not production-committed configurations. No live infrastructure or credentials are modified from this document.*

## 9.1 Encryption in Transit and at Rest

All backup data must be encrypted:

- **At rest**: Backup files/objects encrypted before leaving the source cluster (server-side encryption with customer-managed keys, or client-side encryption). Backup storage (S3, Ceph RGW, GS) must enforce bucket-level default encryption.
- **In transit**: Backup transfer over TLS 1.2+ (mutual TLS where the backup client authenticates to the storage endpoint). Do not send unencrypted backup streams over the internal network.

Example (illustrative placeholder):
```bash
# Client-side encryption before upload — placeholders only
gpg --batch --cipher-algo AES256 --s2k-mode 3 \
    --s2k-digest-algo SHA512 --symmetric \
    --passphrase-file /etc/backup/encryption.key \
    --output /backup/etcd-snapshot.enc.gpg \
    /backup/etcd-snapshot.db
aws s3 cp /backup/etcd-snapshot.enc.gpg s3://backup-bucket/cluster-a/etcd/
```
Never commit `/etc/backup/encryption.key` to Git.

## 9.2 Backup Identity and Least Privilege

The backup service/account must hold only the permissions needed to read source data and write backup storage:

- Separate backup service account from cluster admin credentials.
- Read-only access to source namespaces/resources; write-only access to backup destination bucket/prefix.
- No cluster-admin, no delete on production data, no write to source clusters.
- Credentials rotated on the same cadence as other service credentials (see Section 7 rotation).

## 9.3 Separation of Backup Administration from Cluster Administration

- The person/team operating backups is not necessarily the cluster admin.
- Backup admin can create/read/delete backup objects but cannot modify cluster workloads.
- Cluster admin can trigger backups but cannot alter backup retention or delete backup copies without a second approval.
- Audit both roles independently.

## 9.4 Immutable or Write-Protected Backup Copies

- Enable Object Lock (S3 Object Lock in compliance mode) or equivalent WORM protection on backup storage so backup objects cannot be deleted or overwritten for a minimum retention period.
- Ransomware protection: even a compromised cluster admin credential must not be able to delete or encrypt existing backup copies during the immutability window.
- Test immutability: attempt to delete a recent backup object; the operation must fail.

## 9.5 Retention and Lifecycle Policy

Define and document retention per backup class:

| Backup class | Minimum retention | Immutability window | Example |
|---|---|---|---|
| etcd snapshot | 30 days | 30 days | daily |
| PVC/volume snapshot | 14 days | 14 days | daily |
| Application data (DB dump) | 35 days | 35 days | daily |
| Git/config backup | 90 days | 30 days | per commit |
| Vault Raft snapshot | 7 daily / 4 weekly / 1 monthly | 30 days | daily |

Lifecycle rules: transition older backups to cheaper cold storage; expire after retention; never delete before retention elapses while immutability is enabled.

## 9.6 Malware/Ransomware Considerations

- Backup destination must not be writable by the same credentials that run production workloads.
- Separate network zone or dedicated backup storage account.
- Scan restored backup objects for known-bad content before restore where feasible.
- Keep at least one offline/air-gapped copy (or Object Lock protected copy) for catastrophic ransomware scenarios.

## 9.7 Integrity Verification

- Every backup job must verify checksum (SHA-256) of the produced object after upload.
- Periodic restore drills (see Section 12) are the definitive integrity test — a checksum pass is not proof of a restorable backup.
- Record verification result (pass/fail + timestamp) in the backup audit log.

## 9.8 Key and Credential Recovery

- Backup encryption keys and unseal/recovery material must be backed up independently of the data they protect.
- Store encryption keys in a separate vault/key manager from the data they encrypt.
- Recovery key escrow: at least two custodians, geographically distributed, never stored together with the encrypted backups.
- Loss of encryption key = permanent loss of backup data. Treat key loss as a data-loss event.

## 9.9 Off-Site Protection

- At least one backup copy in a different failure domain (region/AZ or off-site object storage).
- Cross-region copy for etcd and application data backups.
- Off-site copy must be reachable without depending on the primary cluster's network or identity provider.

## 9.10 Audit Logging

- Log every backup job: start/end time, source, destination, object count, bytes, checksum, result.
- Log every backup deletion/retention expiry with operator identity.
- Log every restore initiation with operator identity and target environment.
- Retain audit logs for the same period as the longest backup retention.

## 9.11 Backup Deletion Protection

- Soft-delete + permanent-delete delay on backup storage (e.g., S3 Object Lock legal hold).
- Require two-person approval for manual backup deletion outside normal retention expiry.
- Alert on any backup deletion outside the automated lifecycle policy.

## 9.12 Avoiding the Backup Repository as a Single Point of Compromise

- Do not store all backups in a single bucket/account/credential.
- Segment backup storage by environment (prod/staging/dr) and by data class (etcd vs app data vs config).
- Use distinct credentials per segment.
- If one segment is compromised, others remain intact.

---

*SND 004-P11.5 — Backup Security and Immutability (illustrative)*
