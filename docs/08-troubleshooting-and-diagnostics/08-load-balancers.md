# 08 · Load Balancers

## Symptoms
- VIP not floating between nodes
- Backend not receiving traffic
- Health checks failing
- TLS handshake failing
- Connection timeouts

## Possible causes
- Keepalived not running or misconfigured
- HAProxy/Nginx backend pool misconfigured
- Health check endpoint not responding
- TLS certificate expired or mismatched
- Backend pod/service not Ready

## Diagnostic commands
```bash
# Keepalived
systemctl status keepalived
ip addr show | grep <vip>
keepalived status

# HAProxy
systemctl status haproxy
echo "show stat" | socat /var/run/haproxy.stat - | head -20

# Nginx
systemctl status nginx
nginx -t
curl -vk https://<vip>:<port>

# MetalLB
kubectl get svc -l app.kubernetes.io/name=metallb
kubectl get ipaddress -A
kubectl get l2advertisement -A

# F5 NIC
kubectl get pods -n ingress-nginx
kubectl get ingressclass
kubectl get gatewayclass
```

## Expected output
- keepalived: active, VIP present on master
- haproxy: backups UP, checks passing
- nginx: config test successful, curl returns 200
- metallb: IPAddress allocated, L2Advertisement present
- f5 nic: controller pod Running, IngressClass available

## Investigation procedure
1. Verify keepalived/haproxy/nginx service status
2. Check VIP presence on active node
3. Verify backend health check target responding
4. Check MetalLB IPAddress allocation (ingress service)
5. Check F5 NIC controller and IngressClass

## Resolution
- Restart/fix keepalived; correct VRRP configuration
- Fix HAProxy/Nginx backend pool and health check
- Renew/replace TLS certificate
- Fix MetalLB IP pool or L2 advertisement
- Fix F5 NIC controller deployment

## Verification
- VIP floats correctly; backends UP; health checks passing; curl returns 200 with valid cert

## Prevention
- Automate LB config from templates; monitor VIP ownership
- Alert on backend health check failure
- Monitor certificate expiry (14/7 days)

## Related
- [05 · Load Balancers and Traffic Management](../05-load-balancers/index.md)
- [06 · Kubernetes Infrastructure (6.11 Kubernetes Add-ons)](../06-kubernetes-infrastructure/6.11-kubernetes-add-ons.md)
