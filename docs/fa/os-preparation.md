# راهنمای آماده‌سازی سیستم‌عامل (فارسی)

این راهنما مراحل اتوماسیون شده آماده‌سازی میزبان‌های لینوکس برای پلتفرم استک کلود-بومی با استفاده از Ansible را پوشش می‌دهد.

## سیستم‌عامل‌های پشتیبانی شده

| سیستم‌عامل | نسخه | کرنل | وضعیت |
|---|---|---|---|
| Oracle Linux | 9 | 5.14 (UEK/RHCK) | ترجیح داده شده |
| Ubuntu Server | 24.04 LTS | 6.8+ (GA)، 6.11+ (HWE) | ترجیح داده شده |
| Ubuntu Server | 22.04 LTS | 5.15 (GA)، 6.x (HWE) | پشتیبانی شده |
| RHEL / Rocky / Alma | 9 | 5.14 | پشتیبانی شده |

**نکته**: Oracle Linux 8 (کرنل 4.18) و Ubuntu 20.04 زیر حداقل کرنل 4.19 توصیه شده توسط Kubespray هستند و پشتیبانی نمی‌شوند. Ubuntu 24.04 LTS با کرنل 6.8+ GA و 6.11+ HWE عرضه می‌شود؛ کرنل 6.6 که در پیش‌نویس‌های قبلی ذکر شده بود کرنل GA نیست.

**الزامات کرنل مخصوص CNI:**
- **Cilium 1.20+**: نیازمند کرنل لینوکس >= 5.10 (مستندات upstream Cilium). Ubuntu 22.04 HWE (5.15+) و Oracle Linux 9 UEK/RHCK (5.14+) این نیاز را برآورده می‌کنند.
- **Calico**: از کرنل >= 4.19 پشتیبانی می‌کند.
- نیاز واقعی کرنل، بیشینه حداقل عمومی کوبرنتیز (4.19) و حداقل مخصوص CNI است.

## پیش‌نیازها

### نود کنترل (Control Node)
- Python 3.11-3.13
- ansible-core >=2.19.0، <2.20.0 (طبق الزامات Kubespray v2.32.0)
- Ansible 12 (طبق Kubespray v2.32.0)
- دسترسی SSH با کلید به همه میزبان‌های هدف
- دسترسی به Nexus و Harbor داخلی

**نکته**: محیط Ansible باید به طور مستقل از آماده‌سازی نودهای هدف، روی نود کنترل آماده شود. این رول وابستگی‌های نود کنترل را مدیریت نمی‌کند.

### میزبان‌های هدف (Target Hosts)
- سرور SSH در پورت 22 در حال اجرا
- کاربر `ansible` با sudo بدون رمز عبور
- Python 3 نصب شده
- دسترسی شبکه به Nexus داخلی (`https://nexus.internal`) و Harbor (`https://harbor.internal`)

## آماده‌سازی Inventory

### ۱. کپی و سفارشی‌سازی Inventory

```bash
cd automation/ansible
cp inventories/staging/hosts.ini inventories/production/hosts.ini
```

فایل `inventories/production/hosts.ini` را با نام‌های میزبان و آدرس‌های IP واقعی خود ویرایش کنید:

```ini
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13

[worker]
k8s-w-1 ansible_host=10.30.0.11
k8s-w-2 ansible_host=10.30.0.12

[gpu]
k8s-gpu-1 ansible_host=10.50.0.11

[storage]
ceph-st-1 ansible_host=10.40.0.11
ceph-st-2 ansible_host=10.40.0.12
ceph-st-3 ansible_host=10.40.0.13
...
```

### ۲. تنظیم متغیرهای گروه (Group Variables)

فایل‌های زیر در `group_vars/all/` را ویرایش کنید:

**`main.yml`** - تنظیمات کلی:
```yaml
ntp_servers:
  - 10.10.0.1
  - 10.10.0.2

dns_servers:
  - 10.10.0.53
  - 10.10.0.54

internal_registry: "harbor.internal:5000"
internal_helm_repo: "https://harbor.internal/charts"
internal_nexus: "https://nexus.internal"
```

**`offline.yml`** - میirrorهای داخلی (الزامی برای حالت آفلاین):
```yaml
ol9_baseos_repo_url: "https://nexus.internal/repository/ol9-baseos/"
ol9_appstream_repo_url: "https://nexus.internal/repository/ol9-appstream/"

ubuntu_main_repo_url: "https://nexus.internal/repository/ubuntu-main/"
ubuntu_updates_repo_url: "https://nexus.internal/repository/ubuntu-updates/"
ubuntu_security_repo_url: "https://nexus.internal/repository/ubuntu-security/"

container_registry:
  url: "harbor.internal:5000"
```

**`vault.yml`** - اتصال Vault (هیچ رمز ذخیره نمی‌شود):
```yaml
vault_addr: "https://vault.internal:8200"
vault_namespace: "platform"
```

## اجرا

### ۱. اعتبارسنجی تنظیمات

```bash
cd automation/ansible

# بررسی سینتکس
ansible-playbook -i inventories/production/hosts.ini site.yml --syntax-check

# لینت (lint)
ansible-lint playbooks/ roles/

# اجرای تست (check mode)
ansible-playbook -i inventories/production/hosts.ini site.yml --check --diff
```

### ۲. اجرای پایه پیش‌فرض سیستم‌عامل

```bash
# پایه پیش‌فرض (شامل monitoring، kubernetes، یا GPU/DCGM نمی‌شود)
ansible-playbook -i inventories/production/hosts.ini site.yml

# یا اجرای پلی‌بوک‌های جداگانه
ansible-playbook -i inventories/production/hosts.ini playbooks/base.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/repositories.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/security.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/time-sync.yml
ansible-playbook -i inventories/production/hosts.ini playbooks/containerd.yml
```

### ۳. پیش‌نیازهای نود Kubernetes (اختیاری)

```bash
# بعد از پایه OS + containerd کامل شدن
ansible-playbook -i inventories/production/hosts.ini playbooks/k8s-node-prereqs.yml
```

### ۴. اجزای اختیاری (Opt-in)

```bash
# مانیتورینگ (اختیاری)
ansible-playbook -i inventories/production/hosts.ini playbooks/monitoring.yml

# Kubernetes/Kubespray استقرار کلاستر (جریان کار جداگانه و صریح، بعد از k8s-node-prereqs)
ansible-playbook -i inventories/production/hosts.ini playbooks/kubernetes.yml

# GPU/DCGM (نیاز به پیاده‌سازی رول gpu)
# ansible-playbook -i inventories/production/hosts.ini playbooks/gpu.yml
```

### ۵. اجرای هدفمند

```bash
# محدود به نودهای کنترل‌پلین
ansible-playbook -i inventories/production/hosts.ini site.yml --limit control-plane

# اجرای تگ‌های خاص
ansible-playbook -i inventories/production/hosts.ini site.yml --tags base,security
ansible-playbook -i inventories/production/hosts.ini site.yml --tags containerd
```

### ۵. اعتبارسنجی پس از اجرا

```bash
# بررسی 멱등یت (0 changed در اجرای دوم)
ansible-playbook -i inventories/production/hosts.ini site.yml

# بررسی همه میزبان‌ها
ansible all -i inventories/production/hosts.ini -m setup | grep -E "ansible_distribution|ansible_distribution_version"

# بررسی سرویس‌های خاص
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active chronyd"
ansible all -i inventories/production/hosts.ini -m shell -a "systemctl is-active node_exporter"
ansible all -i inventories/production/hosts.ini -m shell -a "crictl version"
```

## آنچه پیکربندی می‌شود

### رول Base (`roles/base/`)
- اعتبارسنجی/پیکربندی نام میزبان (hostname)
- پکیج‌های پایه (chrony، audit، jq، vim، htop، net-tools، tcpdump، strace، sysstat، curl، wget و...)
- ماژول‌های کرنل مورد نیاز (overlay، br_netfilter، ip_vs، nf_conntrack)
- تنظیمات sysctl برای کوبرنتیز (IP forwarding، bridge-nf، حافظه، فایل‌سیستم، کرنل)
- **سخت‌سازی SSH عبر drop-in (`/etc/ssh/sshd_config.d/99-hardening.conf`) — فایل `/etc/ssh/sshd_config` بازنویسی نمی‌شود**
- همگام‌سازی زمان Chrony با سرورهای NTP داخلی
- پیکربندی DNS با systemd-resolved و سرورهای DNS داخلی
- دایرکتوری گواهی CA داخلی

### رول Repositories (`roles/repositories/`)
- غیرفعال‌سازی مخازن عمومی
- پیکربندی مخازن DNF داخلی Oracle Linux 9 (BaseOS، AppStream، Add-ons)
- پیکربندی مخازن APT داخلی Ubuntu (main، updates، security)
- دانلود و نصب کلیدهای GPG Nexus

### رول Security (`roles/security/`)
- Auditd با قوانین مخصوص کوبرنتیز
- SELinux Enforcing (Oracle Linux) / AppArmor (Ubuntu)
- سخت‌سازی کرنل sysctl (kptr_restrict، dmesg_restrict، ptrace_scope، mmap_min_addr)
- فایروال nftables با پیش‌فرض deny ورودی، مجاز صریح برای:
  - SSH (22) — **محدود به `security_firewall_allowed_source_cidrs` (بدون پیش‌فرض، باید صریح تنظیم شود)**
  - Kubernetes API (6443)
  - etcd (2379-2380)
  - kubelet (10250)
  - kube-scheduler (10259)
  - kube-controller-manager (10257)
  - رنج NodePort (30000-32767)
  - VXLAN (8472 UDP) — برای حالت VXLANِ Cilium
  - Geneve (6081 UDP) — برای حالت Geneveِ Cilium
  - VXLAN (4789 UDP) — برای Calico/overlay
  - ICMP echo-request
- **قوانین iptables legacy به طور خودکار حذف نمی‌شوند** (روش مهاجرت صریح در صورت نیاز)

### رول Monitoring (`roles/monitoring/`) — **اختیاری (Opt-in)**
- Prometheus Node Exporter (پورت 9100)
- Fluent Bit فورواردر لاگ به Loki
- DCGM Exporter (فقط نودهای GPU، پورت 9400) — **فقط روی نودهایی که `nvidia-smi` دارند اجرا می‌شود**
- **اختیاری عبر `ansible-playbook playbooks/monitoring.yml`**
- **حالت آفلاین**: در صورت تنظیم نشدن `monitoring_node_exporter_download_url` / `monitoring_dcgm_exporter_download_url` به میirror داخلی، با خطای واضح شکست می‌دهد؛ به طور تلقین به URLهای عمومی GitHub رجوع نمی‌کند

### رول Containerd (`roles/containerd/`)
- نصب containerd.io از مخازن داخلی
- تولید کانفیگ containerd با:
  - درایو cgroup systemd
  - اسنپ‌شاتر OverlayFS
  - میirror رجیستری برای docker.io، registry.k8s.io، ghcr.io، quay.io → Harbor
  - پیکربندی TLS برای Harbor
- ایجاد کانفیگ میirror رجیستری با گواهی‌های CA

### رول پیش‌نیازهای نود Kubernetes (`roles/k8s-node-prereqs/`) — **اختیاری (Opt-in)**
- اعتبارسنجی سازگاری OS با نسخه‌های Kubespray/Kubernetes
- اعتبارسنجی نسخه کرنل: حداقل عمومی کوبرنتیز 4.19 + مخصوص CNI (Cilium >=5.10، Calico >=4.19)
- بارگذاری ماژول‌های کرنل مورد نیاز (overlay، br_netfilter، ip_vs، nf_conntrack) — ip_vs_rr/wrr/sh در کرنل‌های مدرن در ip_vs گنجانده شده‌اند
- **مالکیت sysctl: رول base ۱۷ تنظیمات (۶ کوبرنتیز + ۱۱ عملکرد) را در `/etc/sysctl.d/99-kubernetes.conf` اعمال می‌کند؛ این رول آن‌ها را اعتبارسنجی می‌کند**
- اعمال sysctl مخصوص CNI: Cilium (۲: IPv4/IPv6 forwarding) در `/etc/sysctl.d/99-cilium.conf`؛ Calico (۳: VXLAN، WireGuard، IPVS) مشروط به فعال‌سازی ویژگی‌ها
- بررسی‌های read-only کانفیگ کرنل Cilium: BPF fs، cgroup v2، CONFIG_BPF، CONFIG_BPF_SYSCALL، CONFIG_CGROUP_BPF، CONFIG_VXLAN/GENEVE، CONFIG_NETFILTER، CONFIG_BPF_JIT؛ هشدار اگر قابل تأیید نباشند
- بررسی‌های read-only کانفیگ کرنل Calico: CONFIG_VXLAN، CONFIG_WIREGUARD، CONFIG_IP_VS، CONFIG_NETFILTER؛ هشدار اگر قابل تأیید نباشند
- مدیریت Swap: **غیرمخرب، opt-in صریح عبر `k8s_swap_policy: "managed"` + `k8s_swap_confirm_disable: true`**
  - شناسایی همه منابع swap (پارتیشن‌ها، فایل‌ها، fstab، واحدهای systemd، zram)
  - گزارش منابع شناسایی شده؛ شکست اگر policy برابر "disable" باشد بدون opt-in
  - با `k8s_swap_policy: "managed"`: پشتیبان‌گیری `/etc/fstab`، کامنت‌گذاری fstab swap entries؛ **فایل swapها، کانفیگ zram، یا واحدهای systemd حذف نمی‌شوند**
  - swapoff موقت **نیاز به `k8s_swap_confirm_disable: true` دارد**؛ در غیر این صورت مراحل دستی گزارش می‌شود
  - با `k8s_swap_policy: "preserve"`: حفظ پیکربندی swap موجود
- تأیید فعال بودن cgroups v2 (cgroup2fs)
- SELinux/AppArmor: گزارش حالت جاری، هشدار اگر حالت هدف نباشد، به طور کورکورانه تغییر نمی‌دهد
- ایجاد دایرکتوری‌های مورد نیاز (/etc/kubernetes، /var/lib/kubelet، /var/lib/etcd، /opt/cni/bin، /etc/cni/net.d، /etc/containerd، /etc/kubernetes/manifests)
- تأیید Containerd: سرویس active + endpoint CRI قابل دسترسی (`crictl info`)
- بررسی وضعیت reboot-required (needs-restarting روی RedHat، /var/run/reboot-required روی Debian)
- مستندسازی پورت‌های شبکه مورد نیاز بر اساس نقش (control-plane در برابر worker) و CNI (Cilium VXLAN 8472 UDP، Geneve 6081 UDP؛ Calico VXLAN 4789 UDP، WireGuard)
- **اختیاری عبر `ansible-playbook playbooks/k8s-node-prereqs.yml`**
- **کوبنیتز نصب نمی‌کند، به کلاستر نمی‌پیوندد، و Kubespray اجرا نمی‌کند**
- **پیش‌نیازها**: پایه OS، repositories، security، time-sync، containerd باید قبلاً کامل شده باشند

### استقرار کلاستر Kubespray (`playbooks/kubernetes.yml`) — **جریان کار جداگانه**
- اجرای Kubespray `cluster.yml` از checkout پین‌شده در `/opt/kubespray/<version>`
- نیازمند برآورده شدن تمام پیش‌نیازهای نود قبل از اجرا
- **اختیاری عبر `ansible-playbook playbooks/kubernetes.yml`**
- **بخشی از site.yml پیش‌فرض نیست**

## عملیات آفلاین/شبکه محدود

سه حالت عملیات تعریف شده‌اند:

### ۱. شبکه محدود (پیش‌فرض)
- میirrorهای پکیج داخلی (Nexus) برای DNF/APT
- رجیستری کانتینر داخلی (Harbor) برای ایمیج‌های containerd
- کلیدهای GPG و گواهی‌های CA از منابع داخلی
- **باینری‌های Monitoring/DCGM**: دانلود از میirror داخلی در صورت تنظیم URLها؛ در غیر این صورت با خطای واضح شکست می‌دهد

### ۲. فقط میirror پکیج
- نصب پکیج تنها از Nexus داخلی
- سایر آرتیفکت‌ها (باینری‌های monitoring، آرتیفکت‌های GPU) ممکن است نیاز به استیج دستی داشته باشند
- وابستگی‌های خارجی صریح به ازای هر رول مستند شده‌اند

### ۳. کاملاً Air-Gap — **هنوز پشتیبانی نمی‌شود**
- کالکشن‌های Ansible و وابستگی‌های پایتون هنوز مسیر استیج/نصب داخلی مستند و قابل reproducer ندارند
- تا حل این موارد، اجرای کامل air-gapِ Ansible پشتیبانی نمی‌شود
- در حال پیشرفت: استیج داخلی برای کالکشن‌های Ansible و وابستگی‌های پایتون عبر Nexus

برای فعال‌سازی رفتار شبکه محدود (حالت‌های ۱ و ۲)، `offline_mode: true` را در `group_vars/all/offline.yml` تنظیم کنید.

## مدیریت ریبوت (Reboot)

اگر به‌روزرسانی‌های کرنل یا کتابخانه‌های هسته اعمال شوند، پلی‌بوک:
- در خروجی `REBOOT REQUIRED` گزارش می‌دهد
- `k8s_reboot_required: true` تنظیم می‌کند
- **به صورت خودکار ریبوت نمی‌کند** (کنtrl در دست اپراتور باقی می‌ماند)

```bash
# ریبوت دستی وقتی آماده هستید
ansible all -i inventories/production/hosts.ini -m reboot
```

**نکته**: پلی‌بوک وضعیت reboot-required را با روش‌های زیر تشخیص می‌دهد:
- خانواده RedHat: `needs-restarting -r` (کد خروجی 1 = ریبوت لازم است)
- خانواده Debian: وجود فایل `/var/run/reboot-required`

اجرای مجدد پلی‌بوک در صورت عدم ریبوت میزبان، همان وضعیت reboot-required را گزارش می‌دهد. این رفتار انتظارشده است — نشانگر تا ریبوت واقعی میزبان باقی می‌ماند.

## مرز هویت (Identity Boundary)

**پیوستن میزبان به دایرکتوری با SSSD/realmd در پلی‌بوک‌های پیش‌فرض آماده‌سازی سیستم‌عامل انجام نمی‌شود.**

طبق ADR-0015 و تعریف کاتالوگ `idpIntegration`، مدل هویت استاندارد پلتفرم از Keycloak به عنوان بروکر OIDC مرکزی برای فدراسیون هویت در لایه اپلیکیشن استفاده می‌کند. یکپارچه‌سازی دایرکتوری در سطح میزبان نیازمند ADR جداگانه پذیرفته شده است.

رول base موارد زیر را حفظ می‌کند:
- حساب break-glass محلی (کاربر `emergency`، UID 999، فقط کلید)
- احراز هویت مبتنی بر کلید SSH برای کاربر `ansible`
- دسترسی اداری امن

## عیب‌یابی

### شکست نصب پکیج
```bash
# بررسی دسترسی به مخزن داخلی
ansible all -i inventories/production/hosts.ini -m shell -a "curl -f https://nexus.internal/repository/ol9-baseos/"

# بررسی کش DNF/APT
ansible all -i inventories/production/hosts.ini -m shell -a "dnf clean all && dnf makecache"
```

### مشکلات اتصال SSH
```bash
# تست اتصال SSH
ansible all -i inventories/production/hosts.ini -m ping

# تأیید کلیدهای میزبان
ssh-keyscan target-host >> ~/.ssh/known_hosts
```

### شکست همگام‌سازی زمان
```bash
# بررسی وضعیت chrony
ansible all -i inventories/production/hosts.ini -m shell -a "chronyc tracking"
ansible all -i inventories/production/hosts.ini -m shell -a "chronyc sources -v"
```

### مشکلات Containerd
```bash
# بررسی کانفیگ containerd
ansible all -i inventories/production/hosts.ini -m shell -a "containerd --config /etc/containerd/config.toml --validate"

# بررسی میirror رجیستری
ansible all -i inventories/production/hosts.ini -m shell -a "cat /etc/containerd/certs.d/*/hosts.toml"

# تأیید سرویس Containerd و CRI
ansible all -i inventories/production/hosts.ini -m systemd -a "name=containerd"
ansible all -i inventories/production/hosts.ini -m shell -a "crictl info"
```

## محدودیت‌ها

1. **بدون پارتیشن‌بندی خودکار دیسک** - فرض می‌کند سیستم‌عامل با لایه پارتیشن مناسب نصب شده است
2. **بدون پیکربندی RAID سخت‌افزاری** - باید قبل از نصب سیستم‌عامل انجام شود
3. **بدون به‌روزرسانی BIOS/فرم‌ور** - باید جداگانه انجام شود
4. **بدون پیکربندی کارت شبکه** - فرض می‌کند کارت‌ها توسط نصب‌کننده سیستم‌عامل یا cloud-init پیکربندی شده‌اند
5. **نصب درایور GPU** - به طور جداگانه توسط رول `gpu` بعد از پایه سیستم‌عامل انجام می‌شود

## مراجع

- [README پروژه Ansible](../../automation/ansible/README.md)
- [راهنمای استفاده از Inventory](../../inventories/README.md)
- [استانداردهای پلتفرم](../../requirements/platform-standards.md)
- [ماتریس نسخه و سازگاری](../../compatibility/version-matrix.md)
- [Kubespray Deployment Guide (English)](../../docs/en/kubespray-deployment.md)
- [راهنمای استقرار Kubespray (فارسی)](../../docs/fa/kubespray-deployment.md)
- [OS Preparation Guide (English)](../../docs/en/os-preparation.md)

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-24*