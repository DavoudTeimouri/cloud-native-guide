# Repositories and Registries

## Symptoms
- Image pull failing (ImagePullBackOff)
- Package install failing (repository unreachable)
- Helm chart install failing (chart not found)
- Docker login failing
- Helm repo add failing

## Possible causes
- Image not in internal Harbor
- Image pull secret missing or invalid
- Harbor/TLS certificate expired or untrusted
- Nexus repository unreachable or misconfigured
- Helm repo not added or URL wrong
- Network/firewall blocking registry

## Diagnostic commands
```bash
# Image pull
skopeo inspect docker://harbor.internal/
kubectl describe pod <pod> | grep -A5 Image
kubectl get secret <pull-secret> -o yaml

# Package repository
dnf repolist   # OL/RHEL/Rocky/Alma
apt-cache policy  # Ubuntu
curl -vk https://nexus.internal/repository/...

# Helm
helm repo list
helm search repo <chart>
helm pull <chart>
```

## Expected output
- skopeo: manifest digest returned
- pull-secret: .dockerconfigjson present and valid
- repolist: enabled repos with package counts
- helm repo: chart listed

## Investigation procedure
1. Check image exists in internal Harbor (skopeo inspect)
2. Check pull secret exists and is valid
3. Verify node trusts Harbor CA certificate
4. Check Nexus repository reachability
5. Verify Helm repo URL and chart availability

## Resolution
- Push missing image to internal Harbor
- Create/update image pull secret
- Install Harbor CA certificate on node
- Fix Nexus repository configuration
- Add/correct Helm repo

## Verification
- skopeo inspect succeeds; pod pulls image; package install works; helm search finds chart

## Prevention
- Automate image mirroring to internal Harbor
- Monitor image pull secret validity
- Monitor Harbor/Nexus health; alert on crash
- Monitor certificate expiry

## Related
- [Repository & Registry Management](../03-repository-registry/index.md)
- [Troubleshooting (08-certificates-and-tls.md)](08-certificates-and-tls.md)
