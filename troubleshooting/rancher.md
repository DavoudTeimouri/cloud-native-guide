# Rancher Troubleshooting

## Symptoms

- Rancher UI not reachable
- Cluster registration fails
- Fleet jobs not deploying
- Catalog entries not available
- Authentication failures (Keycloak integration)

## Likely causes

- Rancher deployment not running
- Cluster agent not connected
- Fleet controller not running
- Helm chart repository not synced
- Keycloak OIDC misconfiguration

## Diagnostic commands

```bash
# Is Rancher running?
kubectl -n cattle-system get pods
kubectl -n cattle-system logs -l app=rancher

# Is cluster agent connected?
kubectl -n cattle-system get pods -l app=cattle-cluster-agent
kubectl -n cattle-system logs -l app=cattle-cluster-agent

# Is Fleet running?
kubectl -n cattle-fleet-system get pods
kubectl -n cattle-fleet-system logs -l app=fleet-controller

# Is Keycloak reachable?
kubectl -n keycloak get pods
kubectl -n keycloak logs -l app=keycloak

# Check Rancher API
curl -k https://<rancher-url>/v3/
```

## Expected healthy state

- Rancher deployment: Available, 1+ replicas
- Cluster agent: Running, connected to server
- Fleet controller: Running
- Keycloak: Running, healthy
- `curl -k https://<rancher-url>/v3/` returns JSON

## Remediation

- Restart Rancher: `kubectl -n cattle-system rollout restart deployment/rancher`
- Re-register cluster: generate new cluster registration token
- Restart Fleet: `kubectl -n cattle-fleet-system rollout restart deployment/fleet-controller`
- Sync Helm repositories: `helm repo update`
- Fix Keycloak OIDC client configuration in Rancher

## Risks

- Restarting Rancher briefly makes management UI unavailable
- Re-registering cluster requires cluster-admin access
- Wrong Keycloak config can lock out all users

## Verification

```bash
kubectl -n cattle-system get deployment rancher
kubectl -n cattle-fleet-system get deployment fleet-controller
curl -sf https://<rancher-url>/v3/ && echo "OK"```
