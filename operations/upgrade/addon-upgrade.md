# Add-on Upgrade

### Purpose
Upgrade platform add-on Helm charts.

### Prerequisites
- Cluster healthy
- New chart versions available in internal Helm repo
- Velero backup completed

### Execution
```bash
# Update Helm chart versions in values files
# Example for cert-manager
sed -i 's/version: 1.21.2/version: 1.21.3/' values/cert-manager.yaml

# Upgrade via Argo CD (preferred)
argocd app sync cert-manager

# Or manual helm upgrade
helm upgrade cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version 1.21.3 \
  -f values/cert-manager.yaml

# Verify
kubectl get pods -n cert-manager
```

### Validation
- All pods Running
- Certificates renewing correctly
- No disruption to existing certificates
