# Management Cluster Setup

### Purpose
Deploy Rancher, Argo CD, Keycloak on dedicated management cluster.

### Prerequisites
- Phase 7 cluster healthy
- Phase 3 identity (Keycloak) deployed
- Phase 4 Vault deployed

### Execution
```bash
# Install Rancher
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm install rancher rancher-stable/rancher \
  --namespace cattle-system --create-namespace \
  --version 2.15.2 \
  --set hostname=rancher.internal \
  --set replicas=3 \
  --set bootstrapPassword=admin \
  --set ingress.tls.source=secret \
  --set tls=external

# Install Argo CD
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd \
  --namespace argocd --create-namespace \
  --version 10.10.5 \
  --set server.autoscale.enabled=true \
  --set server.autoscale.minReplicas=2 \
  --set server.autoscale.maxReplicas=5 \
  --set server.autoscale.enabled=true \
  --set configs.params.server.insecure=false \
  --set configs.cm.url=https://argocd.internal \
  --set configs.cm.oidc.config="
    name: Keycloak
    issuer: https://keycloak.internal/realms/platform
    clientID: argocd
    clientSecret: \$ARGOCD_OIDC_CLIENT_SECRET
    requestedScopes: ['openid', 'profile', 'email', 'groups']
  "

# Configure Keycloak OIDC client for Argo CD
# Configure Keycloak realm for Rancher
```

### Validation
- Rancher registers Application Cluster and reads nodes
- Keycloak login works for Rancher and Argo CD
- Argo CD syncs test app from GitLab
- Velero backup completes and restore into fresh namespace succeeds
- Rancher and Argo CD survive Management Cluster restart