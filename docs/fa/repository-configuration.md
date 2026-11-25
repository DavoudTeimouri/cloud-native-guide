# پیکربندی مخزن

پیکربندی مخازن داخلی برای DNF/YUM (خانواده RHEL) و APT (خانواده دبیان).

## مخازن DNF/YUM (خانواده RHEL)

### فایل مخزن

```ini
# /etc/yum.repos.d/internal.repo
[ol9-baseos]
name=Oracle Linux 9 BaseOS
baseurl=https://nexus.internal/repository/ol9-baseos/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-baseos/RPM-GPG-KEY-oracle

[ol9-appstream]
name=Oracle Linux 9 AppStream
baseurl=https://nexus.internal/repository/ol9-appstream/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-appstream/RPM-GPG-KEY-oracle
```

### تأیید

```bash
# لیست مخازن فعال
dnf repolist

# پاک کردن و بازسازی متادیتا
dnf clean all
dnf makecache

# بررسی کلیدهای GPG
rpm -q gpg-pubkey --qf '%{name}-%{version}-%{release}\n' | grep -i oracle
```

## مخازن APT (خانواده دبیان)

### فایل مخزن

#### Ubuntu 24.04 (noble)

```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ noble main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ noble-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ noble-security main restricted universe multiverse
```

#### Ubuntu 22.04 (jammy)

```bash
# /etc/apt/sources.list.d/nexus.list
deb https://nexus.internal/repository/ubuntu-main/ jammy main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ jammy-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ jammy-security main restricted universe multiverse
```

### تأیید

```bash
# به‌روزرسانی सूچقه پکیج‌ها
apt-get update

# تأیید امضاء مخازن (هیچ خطا tidak انتظار می‌رود)
apt-get update 2>&1 | grep -iE "error|warning|signature"

# لیست پکیج‌های نصب شده
dpkg -l | grep containerd
```

## نصب کلید GPG

### خانواده RHEL

```bash
# ورودی کلید GPG Oracle Linux
rpm --import https://nexus.internal/repository/ol9-baseos/RPM-GPG-KEY-oracle
```

### خانواده دبیان

```bash
# افزودن کلید GPG نکسوس
curl -fsSL https://nexus.internal/repository/gpg-keys/nexus.gpg | apt-key add -
```

## حالت آفلاین

همه مخازن به نکسوس داخلی اشاره می‌کنند. دسترسی به اینترنت عمومی فرض نمی‌شود.

```bash
# تأیید دسترسی به مخزن داخلی
curl -f https://nexus.internal/repository/ol9-baseos/
curl -f https://nexus.internal/repository/ubuntu-main/
```

## منابع

- [راهنمای آماده‌سازی سیستم‌عامل](os-preparation.md)
- [ماتریس خانواده RHEL](../../operating-systems/rhel-family-matrix.md)
- [ماتریس خانواده دبیان](../../operating-systems/debian-family-matrix.md)

---\n*وضعیت: پیش‌نویس | مالک: تیم پلتفرم | آخرین بازبینی: 2026-11-25*
