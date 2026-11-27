# GitLab

## Symptoms
- GitLab unreachable (502/503)
- CI/CD pipeline failing
- Runner not picking up jobs
- Container registry not pushable/pullable
- Backup/restore failing

## Possible causes
- GitLab service not running (puma, sidekiq, nginx)
- Runner not registered or token expired
- Container registry storage full or misconfigured
- Database (PostgreSQL) not running
- Secrets file missing/corrupt (needed for restore)

## Diagnostic commands
```bash
# GitLab
gitlab-ctl status
gitlab-ctl tail puma
gitlab-ctl tail sidekiq

# Runner
gitlab-runner status
gitlab-runner list
gitlab-runner verify

# Registry
docker login harbor.internal
curl -vk https://harbor.internal/api/v2.0/projects

# Database
gitlab-ctl status postgresql
```

## Expected output
- gitlab-ctl status: all services run
- runner: registered and active
- docker login: login succeeded
- curl: HTTP 200 on projects API

## Investigation procedure
1. Check GitLab service status (gitlab-ctl status)
2. Check GitLab logs (puma, sidekiq, nginx)
3. Check runner status and registration
4. Test registry access (docker login, curl API)
5. Check PostgreSQL status

## Resolution
- Restart failed GitLab services
- Re-register runner; verify token
- Fix registry storage or credentials
- Restore from backup if database corrupt

## Verification
- GitLab services run; runner active; registry push/pull succeeds; pipeline runs

## Prevention
- Monitor GitLab services; alert on failure
- Monitor runner registration; alert on unregistered
- Monitor registry storage; alert at threshold
- Schedule regular backups; test restores

## Related
- [04 · Operational Management and GitLab (4.5 GitLab)](../04-operation-servers/4.5-gitlab.md)
