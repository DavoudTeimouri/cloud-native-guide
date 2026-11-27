# Server preparation template

## Purpose
Standard template for preparing a host (any OS, any role) before it joins the Cloud-Native stack.

## Sections
1. **Purpose and scope** — role, OS, environment
2. **Prerequisites and dependencies** — hardware, network, access
3. **Architecture and design** — hardening baseline, partitioning, kernel
4. **Step-by-step implementation** — install OS, configure repos, apply sysctl, users/SSH, NTP/DNS, firewall, container runtime
5. **Configuration examples** — /etc/sysctl.d, sshd_config, repo files
6. **Production best practices** — no host AD join, break-glass account, local accounts only
7. **Security considerations** — SELinux/AppArmor, auditd, file descriptors, max pods
8. **Networking and firewall requirements** — from shared network matrix
9. **Validation and verification** — ansible ping, setup idempotency, break-glass test
10. **Monitoring and logging** — node_exporter, Fluent Bit, auditd shipping
11. **Troubleshooting** — common failure conditions and resolution
12. **Upgrade and maintenance** — patching, kernel upgrade, reboot procedure

## Placeholders
- `<OS>`, `<OS_VERSION>`, `<HOSTNAME>`, `<IP_ADDRESS>`, `<DNS_SERVER>`, `<NTP_SERVER>`, `<SSH_PORT>`
