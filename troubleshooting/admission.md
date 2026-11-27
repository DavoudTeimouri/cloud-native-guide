# Admission Policy Troubleshooting

## Symptoms

- All pod creation rejected ("admission webhook denied the request")
- ValidatingWebhookConfiguration pointing to wrong service
- MutatingWebhookConfiguration modifying resources unexpectedly
- Webhook certificate expired
- Webhook service unreachable

## Likely causes

- Webhook configuration points to deleted/changed service
- Webhook backend pod crash-looping
- Webhook TLS certificate expired
- Webhook rejects all resources (too broad rules)
- NamespaceSelector excludes required namespaces

## Diagnostic commands

```bash
# Check webhook configurations
kubectl get validatingwebhookconfiguration
kubectl get mutatingwebhookconfiguration

# Check webhook service
kubectl get svc -l app=<webhook-app>
kubectl get pods -l app=<webhook-app>

# Check webhook logs
kubectl logs -l app=<webhook-app> -n <webhook-ns>

# Check webhook certificate
kubectl get secret <webhook-cert-secret> -o yaml

# Test webhook directly
kubectl create -f <test-resource.yaml> --dry-run=client -o yaml | \
  kubectl apply -f - --validate=false
```

## Expected healthy state

- Webhook configurations: valid, pointing to existing services
- Webhook backend pods: Running
- Webhook TLS certificate: valid
- `kubectl create --dry-run` succeeds for allowed resources

## Remediation

- Fix webhook service reference (service name, namespace, path)
- Restart webhook backend: `kubectl rollout restart deployment/<webhook-app>`
- Rotate webhook TLS certificate
- Narrow webhook rules (exclude system namespaces)
- Fix NamespaceSelector to include required namespaces

## Risks

- Deleting webhook configuration can allow unrestricted resource creation
- Wrong webhook rules can block all cluster operations
- Certificate rotation can cause brief webhook failures

## Verification

```bash
kubectl get validatingwebhookconfiguration -o yaml
kubectl get mutatingwebhookconfiguration -o yaml
kubectl create -f <test-resource.yaml> --dry-run=client```
