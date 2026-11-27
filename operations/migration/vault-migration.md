# Vault Migration

### Purpose
Migrate Vault to newer major version.

### Prerequisites
- Vault cluster healthy
- Backup snapshot created
- Offline unseal shares available
- Maintenance window

### Execution
```bash
# Upgrade each node sequentially
for node in vault-1 vault-2 vault-3; do
  ssh $node "systemctl stop vault"
  ssh $node "yum update -y vault"  # or apt-get
  ssh $node "systemctl start vault"
  # Wait for node to join cluster
  ssh $node "vault operator raft list-peers"
done

# Unseal each node
for node in vault-1 vault-2 vault-3; do
  vault operator unseal -address=https://$node:8200 $SHARD1
  vault operator unseal -address=https://$node:8200 $SHARD2
  vault operator unseal -address=https://$node:8200 $SHARD3
done
```

### Validation
- `vault status` shows active on one node, standby on others
- All nodes sealed=false
- Cluster healthy
- All policies and secrets accessible