# Ceph CRUSH Rules Documentation

## CRUSH Ruleset Design

CRUSH (Controlled Replication Under Scalable Hashing) is Ceph's algorithm for mapping object data to OSDs without a centralized metadata store. The ruleset defines how data is replicated or erasure-coded across the cluster, how device classes influence placement, and how bucket types organize the hierarchy.

### Ruleset Overview

- **Default ruleset**: Ceph clusters ship with a built-in ruleset (usually ruleset 0) that provides simple uniform replication across all OSDs.
- **Custom rulesets**: Production clusters should define dedicated rulesets (e.g., ruleset 1, 2) to enforce device-class-aware placement, rack/zone awareness, and erasure-code profiles.
- **Ruleset identification**: Each ruleset is referenced by an integer ID. Pools declare their ruleset at creation (`ceph osd pool ruleset <pool> <id>`) and it cannot be changed without recreating the pool.

### CRUSH Rule Grammar

A CRUSH rule consists of:

| Component | Description |
|-----------|-------------|
| `id` | Unique integer identifier for the rule. |
| `type` | Bucket type (`host`, `rack`, `row`, `pdu`, `room`, `datacenter`, `zone`, `region`, `root`). Determines the scope of the rule. |
| `min`, `max` | Minimum and maximum number of OSDs involved in the placement. For replication, `min` is the number of replicas; for erasure coding, it relates to data + parity chunks. |
| `step` | Placement step (`take`, `choose`, `choose-last`). Controls how CRUSH selects OSDs within the bucket hierarchy. |
| `class` | Device class filter (`hdd`, `ssd`, `nvme`, `pmem`). Restricts placement to OSDs of the specified class. |
| `type_name` | Named type reference, linking to a previously defined rule or a device class. |
| `index` | Ordered list of bucket names or IDs that CRUSH iterates during placement. |

### Rule Design Guidelines

1. **Always associate rules with device classes** so that, e.g., SSD-only pools place data on SSDs and HDD pools on HDDs.
2. **Use separate rulesets for different workloads**: replication‑heavy pools, erasure‑coded analytics pools, and gateway pools should each have their own rule to avoid cross‑contamination.
3. **Respect rack/zone topology**: Include `rack` and `zone` bucket types in rules to prevent losing all replicas in a single physical failure domain.
4. **Set appropriate `min`/`max`**: For 3‑way replication, `min=3, max=3`. For erasure coding with 2 data + 2 parity chunks, set `min=4, max=4` (or let CRUSH compute the chunk count from the profile).
5. **Document the ruleset ID** in cluster runbooks so that operators know which rule a pool uses and can troubleshoot placement anomalies.

## Replica Rules (Replication)

Replication rules ensure that each object exists on `N` distinct OSDs, spreading across failure domains.

### Example: 3‑Way Replication with Device-Class Awareness and Zone Spread

```python
rule replica {
    step choose
    size 3
    type osd
    class ssd
    index_rule (type host min 3 max 3 step choose class ssd) # inline illustration
}
```

In practice, a Ceph CRUSH command to create such a rule looks like:

```bash
ceph osd crush rule create-replica \
    1 \
    "replica-ssd" \
    host \
    min 3 \
    max 3 \
    step choose \
    type osd \
    class ssd
```

**Result**: Objects in pools using ruleset 1 will be placed on 3 OSDs that all belong to the `ssd` device class. CRUSH will automatically spread the 3 OSDs across distinct `host` buckets (i.e., different physical hosts) because the default CRUSH map groups OSDs under `host` buckets.

### Replication Bucket Types Commonly Used

| Bucket Type | Purpose |
|-------------|---------|
| `host` | Physical server; CRUSH ensures replicas land on different hosts. |
| `rack` | Rack-level failure domain; useful when multiple hosts share a power source or network switch. |
| `row` | Row-level domain within a datacenter (less common). |
| `datacenter` | Geographic region; used for cross‑datacenter replication. |
| `region` | Wide‑area region; for multi‑region clusters. |

### Tuning Replication Rules

- **Add `until`/`choose‑first` steps** if you need to enforce that the first `N` choices respect a particular constraint (e.g., avoid placing two replicas on the same rack).
- **Use `index_rule`** to compose complex rules from simpler ones (e.g., “choose 3 hosts, then within each host choose 1 OSD”).
- **Test with `ceph osd crush rule dump <rule_name>`** and verify that `size` matches the desired replica count and that `class` and `type` filters are applied as expected.
- **Avoid `step take`** in most replication rules; `choose` or `choose-last` gives CRUSH freedom to spread replicas across the hierarchy, whereas `take` tends to cluster them under the first matching branch.

## Erasure Code Rules (Erasure Coding)

Erasure‑coding rules define how data is striped across OSDs with parity chunks for fault tolerance. They are more complex than replication rules because CRUSH must stripe data and compute parity while respecting device classes and failure domains.

### Example: 2‑Data‑2‑Parity (RS 4+2) Erasure Coding on SSDs

```bash
ceph osd crush rule create-erasure-code \
    2 \
    "ec-2p-ssd" \
    host \
    min 4 \
    max 4 \
    step choose \
    type osd \
    class ssd
```

**Result**: Objects in pools using ruleset 2 will be striped across 4 OSDs, each holding a different data or parity chunk. The total storage efficiency is 4 / 6 = 66.7 % (2 data + 2 parity). The cluster can tolerate the loss of any 2 OSDs without data loss.

### Erasure Code Bucket Types and Considerations

| Bucket Type | Purpose in EC Rules |
|-------------|----------------------|
| `host` | Ensures parity and data chunks land on different hosts. |
| `rack` | Prevents losing all chunks in a single rack failure. |
| `region` | For multi‑region EC profiles; may use a separate ruleset with cross‑region OSD selection. |
| `root` | The top‑level bucket; the rule’s `root` directive maps to the cluster root. |

### EC Rule Tuning Tips

- **Match the `size` (min/max) to the erasure‑code profile**: A 4+2 profile (6 chunks) requires `min=6, max=6`. The profile is set separately (`ceph osd erasure code profile set <profile> <k> <m>`) and referenced by the pool; the CRUSH rule’s `size` must agree.
- **Always include a `class` filter** so that EC chunks are placed on the intended device class. Mixing SSD and HDD chunks in the same EC pool is possible but requires careful rule design and is generally not recommended.
- **Use `step choose`** for even distribution across the hierarchy. `step take` can be used for “filled‑last” placement (e.g., always fill the lowest‑indexed OSDs first), but this can lead to uneven utilization.
- **Verify with `ceph osd erasure code profile get <profile>`** and then `ceph osd crush rule dump <rule_name>` to confirm that the rule’s parameters align with the profile’s `k` and `m` values.
- **Test failure scenarios**: Remove an OSD with `ceph osd out <id>` and confirm that the cluster enters `HEALTH_WARN` during recovery but no data is lost; the EC profile should rebuild parity from remaining chunks.

## Device Classes

Device classes allow CRUSH to distinguish OSDs by their storage medium (SSD, HDD, NVMe, Intel Optane/pmem, etc.). Using classes in CRUSH rules ensures that pools respect the intended performance and capacity characteristics.

### Defining and Assigning Device Classes

1. **Create the class** (if not already present):
   ```bash
   ceph osd device class add /dev/nvme0n1 nvme
   ceph osd device class add /dev/sda1 hdd
   ```
2. **Assign the class to all OSDs of that type** (batch example):
   ```bash
   ceph osd crush reweight type hdd 1.0
   ```
   Actually, class assignment is done per‑OSD; you can view current classes:
   ```bash
   ceph osd dump | grep class
   ```
3. **Use the class in rules**:
   ```bash
   ceph osd crush rule create-replica 3 my-replica-rule host min 3 max 3 step choose class ssd
   ```

### Common Device Classes

| Class | Typical Use Case |
|-------|-------------------|
| `hdd` | Capacity‑oriented, cost‑effective storage for backups, archives, and less latency‑sensitive workloads. |
| `ssd` | General‑purpose SSD, good for databases, caches, and mixed workloads. |
| `nvme` | High‑performance NVMe, used for low‑latency databases, hot caches, and performance‑critical pools. |
| `pmem` | Persistent memory, combines memory‑speed access with data persistence; used for WAL‑heavy workloads or crash‑safe databases. |
| `cpu` (rare) | OSDs that are actually CPU‑bound accelerators (e.g., GPUs used as storage targets in specialized setups). |

### Best Practices for Device‑Class Rules

- **Never mix classes within a single pool’s rule** unless you have a specific, documented reason (e.g., a tiered storage pool where hot data goes to SSD and cold data to HDD via separate sub‑pools). Even then, prefer using separate pools with separate rules.
- **Label OSDs at provisioning** and verify the assignment after any OSD re‑balancing or cluster re‑install; a missed class label leads to mis‑placement and performance anomalies.
- **Document the class‑to‑purpose mapping** in your cluster runbook so that operators can quickly determine which OSDs a given pool will use.
- **Use `ceph osd device class list`** to audit all OSDs and their classes periodically.

## Bucket Types

Bucket types define the hierarchy that CRUSH uses to track failure domains and scope placement decisions. A well‑structured bucket hierarchy is essential for both replication and erasure‑coding rules to spread data across the right failure domains.

### Standard Bucket Hierarchy

```
root
├── region
│   ├── datacenter1
│   │   ├── rack1
│   │   │   ├── host1
│   │   │   │   ├── osd.0
│   │   │   ├── host2
│   │   │   │   ├── osd.1
│   │   │   └── ...
│   └── datacenter2
│       └── ...
├── region2
│   └── ...
```

### Bucket Type Cheat‑Sheet

| Bucket Type | Typical Label | Depth in Hierarchy | Role in CRUSH |
|-------------|---------------|---------------------|---------------|
| `root` | `root` | 0 | Top of the CRUSH map; all other buckets are descendants. |
| `region` | `region‑us‑east‑1`, `region‑eu‑central‑1` | 1 | Geographic region; used for cross‑region replication and EC rules that span sites. |
| `datacenter` | `dc‑atl`, `dc‑sjc` | 2 | Individual data center; used to isolate failures within a city/region. |
| `rack` | `rack‑01`, `rack‑12` | 3 | Rack or cabinet level; prevents all replicas from landing in the same rack. |
| `host` | `ceph‑node‑01`, `ceph‑node‑02` | 4 | Physical server; the most common level for ensuring replicas are on different hosts. |
| `osd` | `osd.0`, `osd.1`, … | 5 | Individual OSD device; the granularity at which CRUSH actually places data. |
| `pdu` (optional) | `pdu‑a`, `pdu‑b` | 5a | Power distribution unit; useful for rack‑level power redundancy modeling. |
| `row` (optional) | `row‑A`, `row‑B` | 6 | Row within a datacenter; less commonly used but helpful for large facilities. |

### Creating and Managing Buckets

Buckets are typically created as part of the initial Ceph deployment via `ceph osd crush add-bucket`, but they can be added or renamed later:

```bash
# Add a new region bucket under root
ceph osd crush add-bucket region-us-east-1 root=root

# Add a rack under that region
ceph osd crush add-bucket rack-01 region=region-us-east-1

# Add hosts under the rack
ceph osd crush add-bucket host1 rack=rack-01

# Add OSDs under each host (example)
ceph osd crush add osd.0 host=host1
ceph osd crush add osd.1 host=host1
```

### Bucket Type Best Practices

1. **Always have at least `region`, `datacenter`, `rack`, and `host` levels** in your CRUSH map for proper failure-domain awareness.
2. **Keep the hierarchy shallow**; deep hierarchies can increase CRUSH computation time and make it harder to reason about placement.
3. **Naming consistency**: Use a consistent naming scheme (e.g., `region-<name>`, `datacenter-<name>`, `rack-<number>`, `host-<name>`) so that automation and documentation stay synchronized.
4. **Document the full hierarchy** in your runbook; when a new site is added, the CRUSH map must be updated and the change validated.
5. **Use `ceph osd crush tree`** to visualize the current hierarchy and verify that new buckets are attached at the correct level.

## Rule Tuning Procedures

### Adding a New CRUSH Rule

1. **Determine the ruleset ID** you want to use. Check existing rulesets:
   ```bash
   ceph osd crush rule list
   ```
2. **Create the rule** using the appropriate `create-replica` or `create-erasure-code` command. Example for a 3‑replica SSD pool:
   ```bash
   ceph osd crush rule create-replica 1 replica-ssd-3 \
       host min 3 max 3 step choose class ssd
   ```
3. **Assign the rule to a pool**:
   ```bash
   ceph osd pool set <pool> ruleset 1
   ```
4. **Verify the rule**:
   ```bash
   ceph osd crush rule dump replica-ssd-3
   ```
5. **Test placement** by putting an object in the pool and checking which OSDs it lands on:
   ```bash
   rados -p <pool> put test-object <file>
   ceph osd map <pool> test-object
   ```

### Modifying an Existing Rule

- **CRUSH rules are immutable** once created; to change a rule, you must create a new rule with a different ID and reassign the pool. Old rules can be left dormant or deleted after confirming no pools reference them.
- **To change replica count**: Create a new rule with the desired `size` and migrate the pool to the new ruleset. During migration, data is gradually re‑balanced.
- **To change device class**: Same as above — new rule, pool reassignment, verify placement, then optionally remove the old rule.

### Removing a CRUSH Rule

1. **Ensure no pools reference the rule**:
   ```bash
   ceph osd pool ruleset <pool>   # check current ruleset
   ```
2. **Migrate pools away** to another ruleset if needed.
3. **Remove the rule**:
   ```bash
   ceph osd crush rule remove <rule-name>
   ```
4. **Clean up**: Optionally run `ceph osd crush rule list` to confirm the rule is gone.

### Tuning for Performance and Balance

| Tuning Lever | Effect | When to Adjust |
|--------------|--------|----------------|
| `step choose` vs `step take` | `choose` spreads placement more evenly; `take` fills first‑matching branch. | Default to `choose`. Use `take` only for specialized "fill‑last" scenarios. |
| `min`/`max` size | Controls the number of OSDs involved. | Set `min`/`max` to the desired replica count or EC chunk count. |
| `class` filter | Restricts placement to a device class. | Always specify a class for performance‑tiered pools. |
| `index_rule` | Composes sub‑rules. | Use when you need compound constraints (e.g., "3 hosts, each from a different rack"). |
| `type osd` vs `type host` | Determines whether the rule operates at the OSD or host level. | Replication rules typically use `type osd` with `class` filtering; CRUSH internally spreads across hosts based on the bucket hierarchy. |

### Validation Checklist After Rule Changes

- [ ] `ceph osd crush rule dump <name>` shows the expected `step`, `size`, `class`, and `type`.
- [ ] `ceph osd pool stats <pool>` reflects the new ruleset and shows correct `size` (replica count or EC chunk count).
- [ ] `ceph pg stat` after placing a test object shows the correct number of OSDs and that they span different `host` buckets.
- [ ] `ceph osd tree` visually confirms that the selected OSDs are in distinct failure domains (different hosts, racks, etc.).
- [ ] No `CRUSH map parse errors` in `ceph -s` output.
- [ ] Run a short‑term load test or object placement test to ensure no unexpected hotspots appear on specific OSDs.

### Common Pitfalls and Fixes

| Pitfall | Symptom | Fix |
|---------|----------|-----|
| **Forgot to assign device class to OSDs** | OSDs of the wrong class are selected, or CRUSH falls back to the default ruleset. | Re‑assign classes: `ceph osd device class add <device> <class>` and re‑verify with `ceph osd dump`. |
| **Rule `min`/`max` mismatch with pool profile** | Pool creation fails or objects are placed with wrong redundancy. | Align `min`/`max` in the rule with the pool’s `min_size`/`max_size` and EC profile’s `k`/`m`. |
| **Missing `rack` or `host` level in bucket hierarchy** | All replicas end up on the same physical rack, defeating fault tolerance. | Add the missing bucket level and re‑balance: `ceph osd crush rebalance`. |
| **Using `step take` for replication** | Data concentrates on the first few OSDs, causing uneven utilization. | Switch to `step choose` for even distribution. |
| **Cross‑region pool using a single‑region ruleset** | Writes are localized to one region, violating data‑distribution policies. | Create a separate ruleset that includes `region` bucket types and references it for cross‑region pools. |

### Automated Rule Auditing (Optional)

You can write a small script that parses `ceph osd crush rule list` and `ceph osd dump`, cross‑checks device classes, and reports any rules that:
- Reference a class that no OSDs have.
- Have `min`/`max` larger than the number of OSDs in the cluster.
- Lack a `step` directive (defaults to `choose`, but explicit is preferred).

Example skeleton:

```bash
#!/usr/bin/env bash
RULES=$(ceph osd crush rule list)
for rule in $RULES; do
  echo "=== Rule: $rule ==="
  ceph osd crush rule dump "$rule"
  # Add custom checks here
done
```

Schedule this as a cron job or integrate it into your cluster health monitoring pipeline.

## References

- [Ceph CRUSH Documentation](https://docs.ceph.com/en/latest/ceph-crush-map/)
- [Ceph OSD Device Classes](https://docs.ceph.com/en/latest/storage/osd/device-classes/)
- [CRUSH Rule Grammar](https://docs.ceph.com/en/latest/rados/operations/crush-map/#rule-syntax)
- [Erasure Coding Profiles](https://docs.ceph.com/en/latest/rados/operations/erasure-code/#erasure-coding-profiles)
