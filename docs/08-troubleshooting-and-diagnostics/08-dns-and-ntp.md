# DNS and NTP

## Symptoms
- Service name resolution fails
- curl/dig returns no answer
- kubectl hangs on DNS lookup
- chronyc shows not synchronized
- Clock skew > 100 ms across nodes

## Possible causes
- CoreDNS pod not running or crash-looping
- Internal DNS unreachable from node
- chrony not running or NTP server unreachable
- Firewall blocking port 53 (DNS) or 123 (NTP)
- /etc/resolv.conf misconfigured

## Diagnostic commands
```bash
# DNS
dig kubernetes.default.svc.cluster.local @<dns-server>
nslookup harbor.internal
cat /etc/resolv.conf
kubectl get pods -n kube-system -l k8s-app=kube-dns

# NTP
chronyc tracking
chronyc sources
chronyc sourcestats
systemctl status chronyd
```

## Expected output
- dig: ANSWER section with record
- nslookup: server and address returned
- resolv.conf: nameserver pointing to internal DNS
- chronyc: LEAP status normal, sources online
- kube-dns pod: Running

## Investigation procedure
1. Check /etc/resolv.conf points to internal DNS
2. Test dig/nslookup against internal DNS server
3. Check CoreDNS pod status in kube-system
4. Check chronyd status and sources
5. Verify firewall allows UDP/TCP 53 and UDP 123

## Resolution
- Fix /etc/resolv.conf to use internal DNS
- Restart CoreDNS pod; check logs
- Restart chronyd; verify NTP server reachable
- Open firewall ports 53/123

## Verification
- dig returns ANSWER; chronyc shows synchronized; kubectl DNS lookup succeeds

## Prevention
- Automate DNS/NTP config via Ansible
- Monitor chrony offset; alert on skew
- Monitor CoreDNS pod health

## Related
- [Overview (1.4 Network Architecture and Access Matrix)](../01-overview-and-architecture/1.4-network-architecture-and-access-matrix.md)
