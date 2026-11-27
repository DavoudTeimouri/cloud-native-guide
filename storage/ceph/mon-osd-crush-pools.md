# Ceph MON, OSD, CRUSH, and Pool Configuration

## MON (Metadata Daemon) Quorum

- **Quorum size**: `ceil(N/2) + 1` for an odd number of MON nodes (e.g., 3, 5, 7). Even numbers are not recommended because the extra node does not increase fault tolerance but adds overhead.
- **Placement**: Deploy MONs on separate physical or virtual machines, ideally in different failure domains (power, network, rack).
- **Data directory**: `/var/lib/ceph/mon/<cluster>-<id>` — keep on fast SSD; do not share with OSD data.
- **Keyring**: `/etc/ceph/ceph.client.admin.keyring` and per-MON keyrings. Rotate keys via `ceph auth import` after generation.
- **Health monitoring**: `ceph mon health`, `ceph mon stat`, andPrometheus metrics `ceph_mon_election_duration_seconds`.
- **Recovery**: If a MON is lost, replace it and restart; the remaining MONs preserve the cluster state. Do not manually edit the mon map.

## OSD (Object Storage Daemon) Tuning

| Parameter | Recommended Default | Description |
|-----------|---------------------|-------------|
| `osd_max_backfills` | `2` | Maximum concurrent backfill operations per OSD. Reduce if cluster is latency-sensitive. |
| `osd_max_create_size` | `0` (unlimited) | Maximum object size for create operations; typically left at default. |
| `osd_max_num_buckets` | `1000` | Upper limit of CRUSH bucket hierarchy depth. Adjust upward only if CRUSH map is deeply nested. |
| `osd_scrub_interval` | `3600` (seconds) | How often each OSD runs a scrub. Lower for aggressive consistency checking. |
| `osd_deep_scrub_interval` | `86400` (seconds) | Deep scrub frequency; runs full data consistency check. |
| `osd_target_utilization_percent` | `80` | Target space utilization; Ceph will strive to keep usage near this % across the cluster. |
| `osd_pool_default_pg_autobalance` | `true` | Enables automatic PG rebalancing when OSDs are added/removed. |
| `osd_pool_default_min_size` | `2` (replicated) / `k` (erasure) | Minimum number of OSDs that must hold data for the pool to be considered "up". |
| `osd_pool_default_size` | `3` (replicated) / `m+n` (erasure) | Total number of OSD copies (replicated) or encoding sets (erasure). |
| `osd_request_timeout` | `30` (seconds) | Timeout for individual OSD requests. Increase if network latency is high. |

### OSD Deployment Guidelines

- **Device class**: Use dedicated SSD or NVMe for journal (`osd journal`), and spinning rust or HDD for data depending on workload (SSD for metadata‑heavy, HDD for capacity‑oriented).
- **Journal size**: `osd journal size` should be at least 5 GiB, typically 10–20 GiB for sustained write workloads.
- **No overlap**: Ensure OSD data directories do not overlap with journal or filesystem metadata.
- **Linux kernel settings**: `vm.swappiness=1`, `fs.file-max` increased, and `net.core.somaxconn` tuned if the workload opens many connections.

## CRUSH Rules

CRUSH (Controlled Replication Under Scalable Hashing) determines where data objects and their replicas/encoded chunks are stored. The default rule `default` works for most clusters, but site‑specific rules may be required.

### Built‑in Rule IDs

| Rule ID | Name | Typical Use |
|---------|------|-------------|
| `0` | `default` | Generic rule; places data across failure domains defined in the CRUSH map. |
| `1` | `replicated` | Explicit replicated rule (same behavior as default when using the `default` rule number). |
| `2` | `erasure_code` | Erasure‑code rule; requires a CRUSH hierarchy with `erasure_code` bucket type. |

### Creating a Custom Rule

```bash
# Add a rule that respects three failure domains: host, row, rack
ceph osd crush rule create-replicated my_rule host rack
# or for erasure code
ceph osd crush rule create-erasure-code erasure_rule reed_sol_4+2 host rack
```

### Rule Parameters

- **`min_size`**, **`max_size`** — limit the number of OSDs the rule may use.
- **`tunable`** values (e.g., `hashpower`, `seed`) affect distribution quality.
- After creating a rule, assign it to pools: `ceph osd pool set <pool> crush_rule <rule_name_or_id>`.

## Pool Types

### Replicated Pools

- **Syntax**: `ceph osd pool create <pool_name> <pg_num> <pgp_num> [replicated <size>]`
- **Default size**: `3` (3‑way replication) unless overridden.
- **Minimum size**: `min_size` controls how many copies must be `up` for the pool to be considered `active`. Set `min_size <= size`; typical `min_size=2` allows continued operation after one OSD failure.
- **Example**:

```bash
ceph osd pool create volumes 128 128 replicated 3
ceph osd pool set volumes min_size 2
```

### Erasure‑Coded Pools

- **Syntax**: `ceph osd pool create <pool_name> <pg_num> <pgp_num> erasure_code <k> <m> [stripe_width <n>]`
- **`k`** — data chunks, **`m`** — parity chunks. Total OSDs needed per stripe = `k + m`.
- **`stripe_width`** — number of OSDs over which each stripe is spread; default is `k + m`.
- **Example** (Reed‑Solomon 4+2, tolerating 2 OSD failures):

```bash
ceph osd pool create archives 256 256 erasure_code 4 2
ceph osd pool set archives min_size 3   # keep at least 3 of 6 OSDs up
```

### Pool Parameters to Tune

| Parameter | Effect |
|-----------|--------|
| `pg_num` / `pgp_num` | Number of placement groups per OSD. Higher values improve load balancing but increase metadata overhead. Rule of thumb: `OSD count * 100` for replicated, `OSD count * 20` for erasure‑coded (adjust for workload). |
| `stripe_width` | For erasure coded pools, controls how many OSDs participate in each stripe. |
| `allow_primary_affinity` | Optional affinity weight for primary OSD selection. |
| `target_size` | Desired number of objects per PG; adjusts PG size automatically. |

## Replication Settings

- **`pool min_size`** vs **`pool size`**: `size` is the total number of copies/parities; `min_size` is the minimum number of healthy copies required for the pool to be `active`. Setting `min_size` lower than `size` permits degradation (e.g., 3‑replica pool can run with `min_size=2` after one OSD down).
- **`pause` / `resume`**: `ceph osd pool pause <pool>` temporarily stops all I/O; `ceph osd pool resume <pool>` re‑enables. Use during maintenance.
- **`deep_scrub`**: `ceph osd pool deep_scrub <pool>` forces a full consistency check across all objects. Schedule during maintenance windows.
- **`target_dir`**: Direct objects to a specific CRUSH bucket via `ceph osd pool set <pool> target_dir <bucket>`.
- **`exclude`**: During operations, `ceph osd pool exclude <osd> <osd>` can temporarily remove an OSD from a pool; use with `ceph osd pool unexclude` after replacement.

## Capacity Planning

### Replicated Pools

- **Usable capacity** ≈ `(number_of_OSDs * OSD_size) / replication_size`.
- Example: 20 OSDs × 1 TiB each, `replication_size=3` → ~6.6 TiB usable.
- **Overhead**: PG metadata ~ 1–2 % of total data volume.
- **IOPS**: Each OSD serves its share; scale OSD count or striping to meet throughput targets.

### Erasure‑Coded Pools

- **Usable capacity** ≈ `(number_of_OSDs * OSD_size) * (k / (k + m))`.
- Example: 20 OSDs × 1 TiB each, `k=4, m=2` → ~13.3 TiB usable (vs ~6.6 TiB with replication factor 3).
- **CPU cost**: Encoding/decoding consumes CPU; ensure enough CPU headroom (typically 10–20 % of cores per OSD node).
- **Stripe width impact**: Larger `stripe_width` spreads I/O across more OSDs, improving parallel throughput but increasing latency per write.

### Growth Projections

1. **Track `df -h` on the OSD directory** and `ceph df detail` for cluster‑wide used/available.
2. **Set alerts** when usage exceeds `osd_target_utilization_percent` (default 80 %).
3. **Add OSDs** before hitting 90 % utilization to avoid auto‑balance thrashing.
4. **Plan for at least 20 % headroom** for erasure‑coded pools to accommodate stripe re‑balancing during OSD additions/removals.

### Tools for Planning

- `ceph df` — cluster‑wide usage.
- `ceph osd tree` — view OSD capacities and weights.
- `ceph osd crush dump` — inspect CRUSH map and rule distribution.
- Prometheus + Grafana dashboards (pre‑built `ceph_exporter` metrics) for trend analysis.

## References

- [Ceph CRUSH Map Design](https://docs.ceph.com/en/latest/ceph-storage/crush/)
- [Ceph OSD Tuning Guide](https://docs.ceph.com/en/latest/storage/osd/)
- [Ceph Pool Configuration](https://docs.ceph.com/en/latest/rados/pool-design/#pool-creation)
- [Capacity Planning Checklist](https://docs.ceph.com/en/latest/ceph-storage/capacity/)