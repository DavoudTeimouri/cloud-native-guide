# OS and Infrastructure Monitoring

## Monitoring Spec Table

| Aspect | Details |
|---|---|
| **Health** | Node physical health: CPU, memory, disk, network, kernel stability |
| **Metrics** | `node_cpu_seconds_total`, `node_memory_Active_bytes`, `node_memory_MemTotal_bytes`, `node_swap_total_bytes`, `node_disk_io_time_seconds_total`, `node_filesystem_avail_bytes`, `node_filesystem_size_bytes`, `node_inodes_total`, `node_inodes_free`, `node_network_receive_bytes_total`, `node_network_transmit_bytes_total`, `node_network_errs_out_total`, `node_network_errs_in_total`, `node_kernel_oom_events_total`, `ntp_offset_seconds`, `x509_certificate_expiry` |
| **Collection** | `node_exporter` (OS-level collectors); native `/proc` and `/sys` endpoints; `systemctl status`; `journalctl -k` for kernel errors; ` chronyc sources`; `certbot certificates` or PKI endpoint |
| **Dashboards** | Node hardware utilization (CPU%, memory%, swap, disk I/O, network throughput); filesystem usage and inode heat; network error rates; kernel OOM rate; NTP sync status; certificate expiry timeline |
| **Alerts** | `HighCPUUsage` (100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80 for 5m), `HighMemoryUsage` ((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90 for 5m), `DiskSpaceLow` (100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes) > 85 for 2m), `InodeUsageHigh` (100 - ((node_inodes_free * 100) / node_inodes_total) > 90), `NTPOffsetHigh` (ntp_offset_seconds > 3600), `CertificateExpiringSoon` (x509_certificate_expiry < 30d) |
| **SLI/SLO** | CPU availability SLO: 99.9% over 30d; Memory availability SLO: 99.9% over 30d; Disk space SLO: 99% available over 30d; Inode availability SLO: 99% over 30d; NTP sync SLO: offset < 1000s over 90d; Certificate renewal SLO: 100% renewal success per cycle over 30d |
| **Tuning** | `node_exporter` scrape interval alignment; disk I/O latency threshold tuning; swapiness kernel parameter; inode overcommit prevention; NTP server pool diversification; certificate auto-renewal window configuration |
| **Troubleshooting** | `kubectl top node` for node-level utilization; `ssh <node> vmstat 1 5`; `dmesg | tail` for kernel panics; `swapon -s` for swap status; `fsck` for filesystem consistency; `chronyc tracking` for NTP drift; `certbot certificates` for certificate status |
| **Recovery** | Scale nodes or redistribute pods if CPU/memory saturated; free disk space or add storage; increase inode count via filesystem tuning; restart NTP daemon or repoint to preferred servers; reissue/renew expired certificates; isolate and restart processes holding inode locks |
| **Dependencies** | `node_exporter` running on all targets; Prometheus scrape targets reachable; network connectivity to node exporter ports (9100); time service (NTP/Chrony) reachable; certificate authority access for renewal |

## Validation Commands (independent of Prometheus)

| Check | Command | Expected Output |
|---|---|---|
| CPU idle / usage | `mpstat 1 1` | Idle % reported; non-zero idle confirms CPU headroom |
| Memory available | `free -h` | `Available` row shows MemAvailable; compares to `node_memory_MemAvailable_bytes` |
| Swap usage | `swapon -s` | Swap file/partition listed; `node_swap_total_bytes` matches |
| Disk I/O stats | `iostat -xz 1 5` | Disk latency (await), utilization (%util), queue depth (qdepth); correlates with `node_disk_io_time_seconds_total` |
| Filesystem usage | `df -h` | Usage % matches `100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes)` |
| Inode usage | `df -i` | Usage % matches `100 - ((node_inodes_free * 100) / node_inodes_total)` |
| Network throughput | `sar -n DEV 1 5` | Receive/transmit bytes/sec; matches `node_network_receive_bytes_total` and `node_network_transmit_bytes_total` |
| Network errors/drops | `cat /proc/net/dev` | `err` columns for RX/TX; matches `node_network_errs_in_total` / `node_network_errs_out_total` |
| Kernel OOM events | `journalctl -k -n 50` | OOM kill messages; matches `node_kernel_oom_events_total` counter increase |
| NTP synchronization | `chronyc sources` | `*` or `+` prefix on source lines; offset within ms; `ntp_offset_seconds` small |
| NTP offset | `chronyc tracking` | Offset and delay displayed; `ntp_offset_seconds` < 3600 |
| Certificate expiry | `certbot certificates` or `openssl x509 -enddate -noout <path>` | `notAfter` date displayed; `x509_certificate_expiry` < 30d triggers alert |