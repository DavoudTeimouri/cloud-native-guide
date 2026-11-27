# Service Mesh Troubleshooting

## Symptoms

- Sidecar injection not working
- mTLS between services failing
- Traffic not routing correctly
- Istio control plane not healthy
- Gateway not receiving external traffic

## Likely causes

- Istio sidecar injector not running
- DestinationRule missing or wrong
- VirtualService not matching traffic
- Istiod not running or unhealthy
- Gateway not configured for correct ports

## Diagnostic commands

```bash
# Is Istiod running?
kubectl -n istio-system get pods -l app=istiod
kubectl -n istio-system logs -l app=istiod

# Is sidecar injector working?
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].name}' | grep istio-proxy

# Check DestinationRules
kubectl get destinationrule -A

# Check VirtualServices
kubectl get virtualservice -A

# Check Gateways
kubectl get gateway -A

# Test sidecar proxy
kubectl exec <pod> -c istio-proxy -- pilot-agent request GET server_info
```

## Expected healthy state

- Istiod: Running, healthy
- Sidecar injected into workload pods
- DestinationRules exist for all services
- VirtualServices route traffic correctly
- Gateways configured for correct ports

## Remediation

- Enable sidecar injection: `kubectl label namespace <ns> istio-injection=enabled`
- Restart pods to get sidecar: `kubectl rollout restart deployment/<app>`
- Create/fix DestinationRules
- Create/fix VirtualServices
- Restart Istiod: `kubectl -n istio-system rollout restart deployment/istiod`

## Risks

- Enabling sidecar injection restarts all pods in namespace
- Wrong VirtualService can misroute traffic
- Removing Gateway can cut off external access

## Verification

```bash
kubectl -n istio-system get pods -l app=istiod
kubectl get destinationrule -A
kubectl get virtualservice -A
kubectl get gateway -A
kubectl exec <pod> -c istio-proxy -- curl -sf localhost:15000/server_info```
