#validate-commands

دستورالعمل‌های تأیید برای آماده‌سازی گره کربرنتیز.

## تأیید سیستم‌عامل

```bash
# تأیید سیستم‌عامل
cat /etc/os-release

# تأیید کرنل
uname -r

# تأیید cgroups
stat -fc %T /sys/fs/cgroup
# خروجی مورد انتظار: cgroup2fs
```

## تأیید sysctl

```bash
# تأیید تنظیمات کلیدی sysctl
sysctl net.bridge.bridge-nf-call-iptables net.ipv4.ip_forward net.ipv4.conf.all.rp_filter
sysctl net.bridge.bridge-nf-call-ip6tables net.ipv4.conf.all.forwarding
```

## تأیید ماژول‌های کرنل

```bash
# تأیید ماژول‌های بارگذاری شده
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'
```

## تأیید containerd

```bash
# تأیید نسخه containerd
crictl version

# تأیید نقطه انتهای CRI
crictl info

# بررسی وضعیت سرویس
systemctl is-active containerd

# اعتبار سنجی پیکربندی
containerd --config /etc/containerd/config.toml --validate
```

## تأیید فایروال

```bash
# nftables (خانواده دبیان)
nft list ruleset

# firewalld (خانواده RHEL)
firewall-cmd --list-all
```

## تأیید هماهنگی زمان

```bash
# بررسی وضعیت chrony
chronyc tracking
chronyc sources -v
# هدف: انحراف < 100 م Secondary در همه گره‌ها
```

## تأیید SELinux / AppArmor

```bash
# SELinux (خانواده RHEL)
getenforce
# خروجی مورد انتظار: Enforcing

# AppArmor (خانواده دبیان)
apparmor_status
```

## تأیید swap

```bash
# بررسی وضعیت swap
swapon --show
# خروجی مورد انتظار: بدون خروجی (swap غیرفعال است)
```

## تأیید Ansible

```bash
# تأیید همه میزبان‌ها سیستم‌عامل درست گزارش می‌کنند
ansible all -i inventories/production/hosts.ini -m setup | grep -E "ansible_distribution|ansible_distribution_version"

# Verify services
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active chronyd"
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active containerd"
ansible all -i inventories/production/hosts.ini -m shell -a "crictl version"
```

## نتایج مورد انتظار تأیید

| بررسی | نتیجه مورد انتظار |
|-------|----------------|
| `cat /etc/os-release` | سیستم‌عامل/نسخه پشتیبانی‌شده |
| `uname -r` | >= 4.19 (کربرنتیز)، >= 5.10 (Cilium) |
| `stat -fc %T /sys/fs/cgroup` | cgroup2fs |
| `getenforce` (RHEL) | Enforcing |
| `apparmor_status` (Debian) | پروفایل‌ها بارگذاری شده‌اند |
| `systemctl is-active containerd` | active |
| `crictl info` | RC=0، نقطه انتهای CRI قابل دسترسی |
| `chronyc tracking` | انحراف < 100 م Secondary |

## منابع

- [راهنمای آماده‌سازی سیستم‌عامل](os-preparation.md)
- [پیکربندی کرنل و شبکه](kernel-networking-preparation.md)
- [containerd پیش‌نیازها](containerd-prerequisites.md)

---\n*وضعیت: پیش‌نویس | مالک: تیم پلتفرم | آخرین بازبینی: 2026-11-25*
