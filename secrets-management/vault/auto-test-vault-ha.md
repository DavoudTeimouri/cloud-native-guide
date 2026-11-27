# Auto-Test Vault HA Deployment

## Raft Storage

HashiCorp Vault uses integrated Raft storage for high availability. The default deployment consists of 5 nodes forming a Raft quorum (3 of 5), where each node stores a full copy of the Raft log and state.

**Node roles:**
- **Active node**: Handles all client requests and log replication
- **Standby nodes**: Remaining nodes that replicate the Raft log but may or may not serve client requests depending on configuration

**Quorum operations:**
- Write operations require majority agreement (3 of 5) across the Raft cluster
- Read operations can be served by any node once the Raft state is committed
- Snapshots are taken periodically and stored externally (e.g., S3, Ceph RGW)

**Failure handling:**
- If the active node fails, one standby automatically becomes the new active node
- The remaining nodes continue replication without interruption
- Manual intervention is only needed if multiple nodes fail simultaneously exceeding the quorum threshold

## Auto-Unseal

Auto-unseal eliminates the need for manual unseal share provisioning by automating the unseal process through cloud KMS services.

**Configuration types:**
- **KMS auto-unseal**: Integration with AWS KMS, Azure Key Vault, or GCP KMS
  - Vault sends encrypted unseal keys to the KMS service
  - KMS returns the decrypted key material to Vault on startup
  - Configured via the `auto-unseal` block in the Vault configuration

- **Device auto-unseal**: Hardware security modules (HSMs) or cloud-native device attestation
  - Vault uses sealed content from the HSM to auto-unseal on startup
  - Common in air-gapped environments with on-premise HSMs

**Unseal key management:**
- Shamir's Secret Sharing: 3 of 5 shares required for manual unseal
- Auto-unseal KMS: No shares needed; KMS provides the unseal key automatically
- Periodic key rotation recommended for compliance

Standby nodes are configured via the `ui` and `cluster_name` settings in the Vault configuration. The active node is elected automatically through Raft, and standby nodes seamlessly take over client traffic without manual intervention.

## Standby Nodes

Vault HA architecture uses an active-passive model with standby nodes that provide both high availability and load distribution.

**Active-Passive topology:**
- **1 active node**: Accepts all client requests and processes leases
- **N-1 standby nodes**: Replicate the Raft log and take over if the active node fails (in a 5-node cluster, 4 standbys)

**Standby node behavior:**
- Standby nodes do not serve client requests under normal operation (unless configured for performance standby)
- They maintain Raft state synchronization with the active node
- In case of active node failure, the cluster automatically elects a new active from the standbys
- State transfer is seamless; no manual intervention required for failover

**Performance consideration:**
- Standard standby nodes reduce read load on the active node by serving stale-read queries if `performance_standby` is enabled
- They provide redundancy without additional compute cost during normal operation
- Monitoring replication lag is critical to ensuring smooth failover

## Performance Standby

Performance standby is a deployment pattern where standby nodes are tuned for specific workload characteristics rather than pure HA readiness.

**Use cases:**
- **Read-heavy workloads**: Standby nodes can serve read-only queries, distributing read traffic
- **Disaster recovery**: One standby can be positioned in a separate geographic region
- **Maintenance windows**: Standby nodes can be taken offline for updates while the active node continues serving

**Configuration:**
- Performance standbys are configured with the same Raft storage backend
- They can be tuned for specific performance characteristics (CPU, memory, I/O)
- Network latency between nodes should be minimized for fast failover
- Metrics to monitor: Raft election latency, replication lag, CPU utilization, disk I/O

**Monitoring and alerts:**
- Raft state health: leader, follower states, election timing
- Replication lag between nodes
- Seal status across all nodes
- Node resource utilization (CPU, memory, disk)
- Unseal progress and seal/unseal latency

## Cross-references

- `secrets-management/vault/vault-architecture.md` — Vault deployment architecture and node topology
- `secrets-management/kubernetes-integration/secret-delivery.md` — Secret delivery methods and integration patterns
- `secrets-management/vault/recovery/restore.md` — Recovery procedures including raft snapshot restore
- `secrets-management/vault/access-control.md` — Auth methods, policies, and seal/unseal process
- `secrets-management/vault/hashicorp-vault-decision.md` — Product decision and license position