# Secret Delivery Troubleshooting

## Symptoms

- Pods cannot mount secrets
- Vault agent injector fails to inject secrets
- Secret not found at expected path
- Authentication to Vault fails
- Secret rotation not propagating to running pods

## Likely causes

- Vault not running or sealed
- Kubernetes auth method not configured
- Secret path wrong or not created
- Vault agent sidecar crash-looping
- Secret CSI driver not installed

## Diagnostic commands

```bash
# Is Vault running?
kubectl -n vault get pods
kubectl -n vault logs -l app=vault

# Is Vault sealed?
vault status

# Can we authenticate?
vault login -method=kubernetes role=<role>
vault token lookup

# Check secret exists
vault kv get <path>

# Check CSI driver
kubectl get daemonset -n vault-csi -l app=vault-secret-csi-driver

# Check pod events
kubectl describe pod <pod> | grep -A5 "Events"
```

## Expected healthy state

- Vault: Unsealed, healthy
- `vault token lookup` returns valid token info
- `vault kv get <path>` returns secret data
- Secret CSI driver daemonset: Running
- Pod events show successful secret mount

## Remediation

- Unseal Vault: `vault operator unseal` with 3 keys
- Restart Vault: `kubectl -n vault rollout restart sts/vault`
- Configure Kubernetes auth method: `vault write auth/kubernetes/config`
- Create secret at correct path: `vault kv put <path> key=value`
- Install Secret CSI driver if missing

## Risks

- Unsealing Vault requires 3 separate key holders
- Restarting Vault briefly interrupts all secret access
- Wrong auth config can lock out all applications

## Verification

```bash
vault status
vault token lookup
vault kv get <path>
kubectl describe pod <pod> | grep -A3 "secret"```
