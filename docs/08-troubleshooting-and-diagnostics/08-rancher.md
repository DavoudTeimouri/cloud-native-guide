# 08 · Rancher

## Symptoms
- Cluster not showing in Rancher UI
- Cluster registration failed
- Rancher API unreachable
- Agent not connecting to Rancher server
- Cluster provisioning stuck

## Possible causes
- Rancher server pod not running
- Cluster registration token expired or invalid
- Network/firewall blocking agent-to-server (HTTPS 443)
- TLS certificate mismatch or expired
- Node resources insufficient for Rancher workloads

## Diagnostic commands
```bash
# Rancher server
kubectl get pods -n cattle-system
kubectl get deployments -n cattle-system
kubectl logs -n cattle-system deploy/rancher

# Agent on cluster
kubectl get pods -n cattle-system -l app=cattle-agent
kubectl logs -n cattle-system -l app=cattle-agent

# Connectivity
curl -vk https://rancher.management.internal
nc -zv rancher.management.internal 443
```

## Expected output
- Rancher server: Running
- Agent: Running, connected to server
- curl: TLS handshake, HTTP response
- nc: port 443 open

## Investigation procedure
1. Verify Rancher server deployment and pods running
2. Check agent pod status on registered cluster
3. Test connectivity to rancher.management.internal:443
4. Verify registration token valid
5. Check TLS certificate validity

## Resolution
- Restart/redeploy Rancher server
- Re-register cluster with valid token
- Open firewall port 443 between cluster and server
- Renew TLS certificate

## Verification
- Cluster shows in Rancher UI; agent connected; API reachable

## Prevention
- Monitor Rancher server health; alert on pod restart
- Monitor agent connection; alert on disconnect
- Monitor certificate expiry

## Related
- [06 · Kubernetes Infrastructure (6.8 Kubernetes Management Platform)](../06-kubernetes-infrastructure/6.7-kubernetes-management-platform.md)
- [06 · Kubernetes Infrastructure (6.9 Cluster Registration)](../06-kubernetes-infrastructure/6.9-kubernetes-networking.md)
