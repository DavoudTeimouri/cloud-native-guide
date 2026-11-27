# Performance

## Symptoms
- Application slow or timeout
- Node CPU/memory high
- Disk I/O slow
- Network latency high
- Database queries slow

## Possible causes
- Resource exhaustion (CPU/memory/disk)
- Node tainted or unschedulable
- Pod resource limits too low
- Disk full or slow (OSD rebalancing)
- Network congestion or misconfiguration
- Ceph OSD rebalancing

## Diagnostic commands
```bash
# Node resources
kubectl top nodes
kubectl top pods
ssh <node> 'top; df -h; iostat -x 1 5'

# Network
iperf3 -c <target-ip>
ping -c 10 <target-ip>
mtr <target-ip>

# Storage
ceph osd perf
ceph pg stat
iostat -x 1 5
```

## Expected output
- kubectl top: CPU/memory within limits
- iperf3: bandwidth near link speed; low latency
- ping: low latency (< 10ms local, < 50ms remote)
- ceph osd perf: no slow ops; PGs active+clean

## Investigation procedure
1. Check node/pod resource usage; identify hot node/pod
2. Check disk I/O and capacity; check for Ceph rebalance
3. Test network bandwidth and latency; check for congestion
4. Check application logs for slow queries/timeouts
5. Check Pod resource limits; adjust if too low

## Resolution
- Scale up node/pod resources; adjust limits
- Move pod to less loaded node; add taint/toleration
- Wait for Ceph rebalance; tune backfill rate
- Fix network congestion; upgrade link if needed
- Optimize application queries

## Verification
- CPU/memory within limits; iperf3 good latency/bandwidth; Ceph PGs active+clean; application responsive

## Prevention
- Monitor resource usage; alert at threshold
- Monitor disk capacity; alert at 70%/80%
- Monitor Ceph health; alert on degradation
- Monitor network latency; alert on degradation

## Related
- [Overview (1.2 Infrastructure Sizing)](../01-overview-and-architecture/1.3-infrastructure-sizing-and-resource-calculation.md)
- [Software-Defined Storage (7.6 Monitoring and Logging)](../07-software-defined-storage/7.6-monitoring-and-logging.md)
