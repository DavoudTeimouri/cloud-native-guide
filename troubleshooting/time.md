# Time Skew Troubleshooting

## Symptoms

- `timedatectl` shows large offset or "System clock synchronized: no"
- TLS certificate validation fails (certificate not yet valid / expired)
- Kubernetes API rejects requests with timestamp skew errors
- etcd cluster members cannot agree on leader
- Logs show timestamps out of order

## Likely causes

- `chronyd` or `systemd-timesyncd` not running
- NTP servers unreachable from nodes
- Hardware clock drift
- VM host time not synchronized (virtualized environments)
- Timezone mismatch between nodes

## Diagnostic commands

```bash
# Check time synchronization status
timedatectl
chronyc tracking
chronyc sources -v

# Check offset
chronyc tracking | grep "Last offset"

# Compare across nodes
for host in <node-list>; do ssh $host "date -u && timedatectl"; done

# Check NTP reachability
nc -zv <ntp-server> 123

# Check hardware clock
hwclock --debug
```

## Expected healthy state

- `timedatectl` shows "System clock synchronized: yes"
- `chronyc tracking` shows "Leap status: normal"
- Offset < 100 ms
- All nodes within 1 second of each other

## Remediation

- Start and enable chronyd: `systemctl enable --now chronyd`
- Verify NTP servers in `/etc/chrony.conf` or `/etc/systemd/timesyncd.conf`
- Restart chronyd after config change: `systemctl restart chronyd`
- Force sync: `chronyc burst <ntp-server>`
- Check VM host time if running in virtualized environment

## Risks

- Large time jumps can break TLS sessions and Kubernetes API tokens
- Restarting time sync service briefly disrupts time-sensitive operations
- Hardware clock drift may indicate failing CMOS battery or host issue

## Verification

```bash
timedatectl | grep "System clock synchronized"
chronyc tracking | grep -E "Leap status|Last offset"
for host in <node-list>; do ssh $host "date -u +%s"; done | sort -n | uniq -c```
