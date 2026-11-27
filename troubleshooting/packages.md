# Linux Package Management Troubleshooting

## Symptoms

- `apt` or `dnf` returns "Unable to locate package"
- Package installation fails with dependency conflicts
- `apt-get update` fails with GPG signature errors
- Repository metadata out of date
- Lock file held by another process

## Likely causes

- Repository not configured or unreachable
- GPG key expired or missing
- Package cache corrupted
- Lock file from previous process
- Wrong distribution version in sources list

## Diagnostic commands

```bash
# Check apt/dnf status
apt-cache policy <package>
dnf repoinfo <package>

# Check repository configuration
cat /etc/apt/sources.list.d/*.list
cat /etc/yum.repos.d/*.repo

# Check GPG keys
apt-key list
rpm -q gpg-pubkey

# Check for lock files
ls /var/lib/apt/lists/lock /var/lib/dnf/lock 2>/dev/null
ps aux | grep -E "apt|dnf|yum"

# Clear cache
apt-get clean
dnf clean all
```

## Expected healthy state

- `apt-cache policy <package>` shows candidate version
- `dnf repoinfo <package>` shows available version
- No lock files held by other processes
- Repository metadata current (not stale)
- GPG keys present and valid

## Remediation

- Refresh package index: `apt-get update` or `dnf makecache`
- Import missing GPG keys: `apt-key adv --keyserver ...` or `rpm --import`
- Remove stale lock files: `rm -f /var/lib/apt/lists/lock`
- Kill stale apt/dnf processes and retry
- Fix repository URLs in sources list

## Risks

- Removing lock files while another process runs can corrupt package database
- Importing wrong GPG keys can allow untrusted packages
- Changing repository URLs can pull packages from unintended sources

## Verification

```bash
apt-get update
apt-cache policy <package>
dnf makecache
dnf repoinfo <package>```
