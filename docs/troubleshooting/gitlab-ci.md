# GitLab CI/CD Troubleshooting

## Symptoms

- Pipeline stuck in "pending" or "created"
- Jobs failing with "runner not available"
- Docker-in-Docker (DinD) failures
- Cache not restoring between jobs
- Artifacts not published

## Likely causes

- GitLab Runner not registered or offline
- Runner tags not matching job tags
- Docker daemon not accessible in job
- Cache key mismatch or storage full
- Artifact path wrong or not created

## Diagnostic commands

```bash
# Check runner status
gitlab-runner list
gitlab-runner status

# Check runners in GitLab
curl -H "PRIVATE-TOKEN: <token>" \
  https://<gitlab-url>/api/v4/runners

# Check job logs
# View in GitLab UI: CI/CD > Jobs > <job>

# Check runner configuration
cat /etc/gitlab-runner/config.toml

# Test Docker in runner
docker run --rm hello-world
```

## Expected healthy state

- GitLab Runner: registered, online, not paused
- Runner tags match job tags
- Docker daemon accessible in CI jobs
- Cache storage available and writable
- Artifact paths created by jobs

## Remediation

- Register runner: `gitlab-runner register`
- Start runner: `gitlab-runner start`
- Match runner tags to job tags
- Fix Docker daemon access (mount /var/run/docker.sock)
- Clear old cache: delete expired cache entries
- Fix artifact paths in .gitlab-ci.yml

## Risks

- Unregistering runner loses all its job history
- Restarting runner interrupts running jobs
- Changing cache keys invalidates all existing caches

## Verification

```bash
gitlab-runner list
gitlab-runner verify
curl -H "PRIVATE-TOKEN: <token>" \
  https://<gitlab-url>/api/v4/runners?active=true | python3 -m json.tool | head -20```
