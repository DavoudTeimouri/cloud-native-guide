# اشتباهات رایج و رفع nói장

مشکلات رایج که هنگام آماده‌سازی سیستم‌عامل به آن‌ها می‌برید و نحوه رفع آن‌ها.

## شکست در نصب پکیج‌ها

### علامت

DNF/APT در نصب پکیج‌ها از مخزن داخلی شکست می‌خورد.

### تشخیص

```bash
# تأیید دسترسی به مخزن داخلی
curl -f https://nexus.internal/repository/ol9-baseos/
curl -f https://nexus.internal/repository/ubuntu-main/
```

### رفع مشکل

- بررسی کنید نکسوس داخلی قابل دسترسی است
- پیکربندی مخزن را در `/etc/yum.repos.d/internal.repo` یا `/etc/apt/sources.list.d/nexus.list` بررسی کنید
- بررسی کنید کلیدهای GPG وارد شده‌اند

## مشکل اتصال SSH

### علامت

Ansible نمی‌تواند به میزبان‌های هدف متصل شود.

### تشخیص

```bash
# بررسی اتصال SSH
ansible all -i inventories/production/hosts.ini -m ping

# Verify host keys
ssh-keyscan target-host >> ~/.ssh/known_hosts
```

### رفع مشکل

- مطمئن شوید سرور SSH در پورت 22 در حال اجرا است
- مطمئن شوید کاربر `ansible` sudo بدون رمز عبور دارد
- احراز هویت مبتنی بر کلید SSH را پیکربندی کنید

## مشکل هماهنگی زمان

### علامت

chronyd زمان را هماهنگ نمی‌کند.

### تشخیص

```bash
# بررسی وضعیت chrony
chronyc tracking
chronyc sources -v
```

### رفع مشکل

- سرورهای NTP داخلی (10.10.0.1, 10.10.0.2) را بررسی کنید
- پیکربندی chrony در `/etc/chrony.conf` را بررسی کنید
- سرویس chronyd فعال و در حال اجرا باشد

## مشکل containerd

### علامت

سرویس containerd خراب است یا نقطه انتهای CRI قابل دسترسی نیست.

### تشخیص

```bash
# تأیید پیکربندی containerd
containerd --config /etc/containerd/config.toml --validate

# بررسی وضعیت سرویس
systemctl is-active containerd

# بررسی نقطه انتهای CRI
crictl info
```

### رفع مشکل

- پیکربندی containerd در `/etc/containerd/config.toml` را بررسی کنید
- مطمئن شوید آینه‌های ثبت‌شده به هاربور داخلی اشاره می‌کنند
- نسخه پکیج containerd.io را 2.3.7 (نسخه پین‌شده Kinbspray releasing-2.32) بررسی کنید
- لاگ‌های سرویس را بررسی کنید: `journalctl -u containerd`

## مشکل فایروال

### علامت

פورت‌های کربرنتیز بین گره‌ها قابل دسترسی نیستند.

### تشخیص

```bash
# nftables (خانواده دبیان)
nft list ruleset

# firewalld (خانواده RHEL)
firewall-cmd --list-all
```

### رفع مشکل

- بررسی کنید پورت‌های مورد نیاز باز هستند: 6443, 10250, 8472/UDP, 6081/UDP, 30000-32767
- مطمئن شوید پورت SSH 22 مجاز است (بدون قفل کردن مدیر)
- بررسی کنید سرویس فایروال فعال است

## مشکل ماژول کرنل

### علامت

ماژول‌های لازم برای کرنل بارگذاری نشده‌اند.

### تشخیص

```bash
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'
```

### رفع مشکل

- ماژول‌ها را با `modprobe` بارگذاری کنید
- در `/etc/modules-load.d/k8s.conf` پایدار کنید
- اگر ماژول‌ها بعد از پیکربندی بارگذاری نشوند، راه‌اندازی مجدد کنید

## مشکل swap

### علامت

swap در گره کربرنتیز شناسایی شده است.

### تشخیص

```bash
swapon --show
```

### رفع مشکل

- `k8s_swap_policy: "managed"` را در group_vars تنظیم کنید
- `k8s_swap_confirm_disable: true` را برای swapoff موقت تنظیم کنید
- یا `k8s_swap_policy: "preserve"` را برای حفظ swap فعلی تنظیم کنید (انحراف مستند شده)

## نیاز به راه‌اندازی مجدد

### علامت

پلی‌بوک `REBOOT REQUIRED` را گزارش می‌کند.

### رفع مشکل

```bash
# راه‌اندازی مجدد دستی وقتی آماده هستید
ansible all -i inventories/production/hosts.ini -m reboot
```

- راه‌اندازی خودکار انجام نمی‌شود (کنترل اپراتور لازم است)
- پس از راه‌اندازی مجدد، دوباره پلی‌بوک را اجرا کنید تا نشان باز شود

## منابع

- [راهنمای آماده‌سازی سیستم‌عامل](os-preparation.md)
- [دستورالعمل‌های تأیید](validation-commands.md)

---\n*وضعیت: پیش‌نویس | مالک: تیم پلتفرم | آخرین بازبینی: 2026-11-25*
