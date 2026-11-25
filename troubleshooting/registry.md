# Registry Troubleshooting

## Common Issues

### Harbor Unreachable

**Symptoms**: Cannot access Harbor UI or push/pull images.

**Likely Causes**:
- Harbor pods not running
- Database unavailable
- Redis unavailable
- Ingress not routing correctly
- TLS certificate expired

**Diagnosis**:
```bash
kubectl get pods -n harbor
kubectl logs -n harbor -l app=harbor
curl -k https://harbor.internal/api/v2.0/health
```

**Resolution**:
- Restart Harbor pods
- Check PostgreSQL and Redis connectivity
- Verify ingress configuration
- Renew TLS certificates

### Image Pull Fails

**Symptoms**: `ImagePullBackOff` or `ErrImagePull` errors.

**Likely Causes**:
- Image not in registry
- Registry authentication failed
- Image name/tag incorrect
- Registry unreachable
- Image pull secrets missing/incorrect

**Diagnosis**:
```bash
kubectl describe pod <pod> -n <namespace>
kubectl get secret <pull-secret> -n <namespace> -o yaml
crictl pull <image>
```

**Resolution**:
- Verify image exists in Harbor: `curl -k https://harbor.internal/api/v2.0/projects/<project>/repositories/<repo>/artifacts/<tag>`
- Check imagePullSecret exists and has correct credentials
- Verify registry URL in pod spec
- Check network connectivity to Harbor

### Push Fails

**Symptoms**: `docker push` or `helm push` fails.

**Likely Causes**:
- Authentication failed
- Insufficient permissions
- Repository doesn't exist
- Quota exceeded
- Network connectivity

**Diagnosis**:
```bash
docker login harbor.internal
docker push harbor.internal/project/image:tag
helm push chart.tgz oci://harbor.internal/charts
```

**Resolution**:
- Verify credentials and permissions
- Create repository/project in Harbor if missing
- Check quota limits
- Verify network connectivity

### Chart Push Fails

**Symptoms**: `helm push` fails.

**Likely Causes**:
- Chart version already exists
- Chart format invalid
- OCI registry not configured for charts
- Authentication issue

**Resolution**:
```bash
# Verify chart
helm lint ./chart
helm package ./chart

# Push with explicit version
helm push ./chart-1.0.0.tgz oci://harbor.internal/charts
```

### Nexus Issues

**Symptoms**: Cannot pull packages from Nexus.

**Likely Causes**:
- Nexus pods down
- Repository configuration incorrect
- Authentication failed
- Blob store full

**Diagnosis**:
```bash
kubectl get pods -n nexus
curl -k https://nexus.internal/service/rest/v1/status
```

**Resolution**:
- Restart Nexus pods
- Verify repository configuration
- Check blob store disk space
- Verify authentication realms

### GitLab Registry Issues

**Symptoms**: Cannot push/pull from GitLab registry.

**Likely Causes**:
- GitLab registry not enabled
- Authentication token expired
- Project/repository doesn't exist
- CI/CD token not configured

**Diagnosis**:
```bash
curl -k https://gitlab.internal/-/health
curl -k https://gitlab.internal/v2/_catalog
```

**Resolution**:
- Enable container registry in GitLab project settings
- Generate personal access token with `read_registry`, `write_registry` scopes
- Configure CI/CD variables for registry auth

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-23*