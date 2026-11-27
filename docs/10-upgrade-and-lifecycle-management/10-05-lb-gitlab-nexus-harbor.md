# 10 · Load Balancer, GitLab, Nexus, Harbor

## Purpose and scope
LB, GitLab, Nexus, Harbor upgrades; TLS, backup/restore.

## Steps
1. Check version compatibility matrix
2. Backup application data/configuration
3. Upgrade component one at a time
4. Verify service healthy

## Implementation
```bash
# Harbor upgrade via Helm
helm upgrade harbor harbor/harbor --version <new-version> -n harbor

# GitLab upgrade
gitlab-ctl stop
gitlab-ctl upgrade
gitlab-ctl start

# Nexus upgrade
# Replace Nexus home directory with new version
# Start Nexus service

# Validate
kubectl get pods -n harbor
gitlab-ctl status
curl -vk https://nexus.internal/
curl -vk https://harbor.internal/
```

## Validation
- All components Running/healthy
- Harbor push/pull works
- GitLab login works
- Nexus repository browse works

## Related
- [03 · Repository & Registry Management](../03-repository-registry/index.md)
- [04 · Operational Management & GitLab (4.5 GitLab)](../04-operation-servers/4.5-gitlab.md)
- [05 · Load Balancers & Traffic Management](../05-load-balancers/index.md)
