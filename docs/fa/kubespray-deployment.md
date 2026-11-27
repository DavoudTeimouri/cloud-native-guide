# راهنمای استقرار Kubespray (فارسی)

این راهنما استقرار اتوماتیک خوشه‌های Kubernetes با استفاده از Kubespray v2.32.0 برای پلتفرم استک کلود-بومی را پوشش می‌دهد.

## بررسی کلی

جریان کار استقرار موارد زیر را جدا می‌کند:
1. **آماده‌سازی نود کنترل (Control Node)** - محیط Python، وابستگی‌های پین‌شده، سورس Kubespray
2. **پیش‌نیازهای نود** - پایه OS، containerd، پیش‌نیازهای میزبان Kubernetes (راهنمای OS Preparation Guide را ببینید)
3. **Preflight استقرار** - اعتبارسنجی تمام پیکربندی‌ها قبل از استقرار
4. **استقرار کلاستر** - اجرای صریح Kubespray توسط اپراتور

## پیش‌نیازها

### نود کنترل
- Oracle Linux 9 یا Ubuntu 22.04/24.04
- Python 3.11
- دسترسی اینترنت یا میirrorهای داخلی برای استیج اولیه
- دسترسی SSH با کلید به همه نودهای هدف (sudo بدون رمز)

### نودهای هدف
- پایه OS کامل شده (playbooks/base.yml)
- پیکربندی مخازن کامل شده (playbooks/repositories.yml)
- سخت‌سازی امنیتی کامل شده (playbooks/security.yml)
- همگام‌سازی زمان کامل شده (playbooks/time-sync.yml)
- نصب containerd کامل شده (playbooks/containerd.yml)
- **پیش‌نیازهای نود Kubernetes کامل شده** (playbooks/k8s-node-prereqs.yml)

### زیرساخت داخلی
- میirror مخزن Nexus (DNF/APT)
- رجیستری کانتینر Harbor با گواهی CA
- سرورهای DNS/NTP داخلی
- Vault برای Secrets (اختیاری)

## شروع سریع

### ۱. آماده‌سازی نود کنترل
```bash
cd automation/ansible
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-control-node.yml
```

### ۲. آماده‌سازی نودهای هدف
```bash
# اجرای پایه OS (اگر قبلاً انجام نشده)
ansible-playbook -i inventories/production/hosts.yml site.yml

# اجرای پیش‌نیازهای نود Kubernetes
ansible-playbook -i inventories/production/hosts.yml playbooks/k8s-node-prereqs.yml
```

### ۳. اجرای Preflight استقرار
```bash
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-deploy.yml
```

خروجی preflight را بررسی کنید. اگر تمام چک‌ها پاس شدند:

### ۴. تأیید نسخه Kubernetes
نسخه `kubespray_kubernetes_version: "1.36.4"` را به صورت دستی با Kubespray v2.32.0 چک کنید (نسخه پیش‌فرض در upstream README.md).
`kubernetes_version_verified: true` را در group vars بعد از تأیید تنظیم کنید.

### ۵. استقرار کلاستر (اقدام صریح اپراتور)
```bash
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-deploy.yml \
  -e '{"kubespray_deploy_mode":"deploy","kubespray_operator_approval":true}'
```

**نکته**: متغیر تأیید باید Boolean JSON (`true`) باشد، نه رشته (`"true"`). مقادیر رشته‌ای توسط preflight رد می‌شوند.

## پین‌کردن نسخه (Version Pinning)

تمام نسخه‌ها برای reproducer بودن صریح پین شده‌اند. **نسخه‌های نشان‌دهنده با ⚠️ overrideهای پروژه هستند، نه پیش‌فرض‌های Kubespray v2.32.0.**

| کامپوننت | نسخه | منبع | وضعیت |
|-----------|-------|------|--------|
| Kubespray | v2.32.0 | GitHub release tag | Verified |
| Kubernetes | 1.36.5 | Kubespray v2.32.0 default | Verified (default) |
| Ansible Core | 2.19.3 | PyPI / Kubespray v2.32.0 | Verified |
| Ansible | 12.3.0 | PyPI / Kubespray v2.32.0 | Verified |
| Cilium CNI | 1.20.3 | Kubespray v2.32.0 default | Verified (default) |
| Calico CNI | 3.31.7 | Kubespray v2.32.0 default | Verified (default) |
| Containerd | 2.3.7 | Kubespray v2.32.0 default | Verified (default) |
| Etcd | 3.6.15 | Kubespray v2.32.0 default | Verified (default) |
| CoreDNS | 1.14.2 | Kubespray v2.32.0 default | Verified (default) |
| Metrics Server | 0.8.0 | Kubespray v2.32.0 default | Verified (default) |
| cni-plugins | 1.9.1 | Kubespray v2.32.0 default | Verified (default) |

## معماری Inventory

### گروه‌های الزامی
| گروه | هدف | حداقل نود |
|------|-------|------------|
| kube_control_plane | نودهای کنترل‌پلین | ۳ (HA) |
| kube_node | همه نودهای Kubernetes | ۳+ |
| etcd | کلاستر etcd (stacked) | ۳ |

### گروه‌های اختیاری
| گروه | هدف |
|------|-------|
| kube_gpu | نودهای worker GPU |
| kube_storage | نودهای ذخیره‌سازی (Ceph/Rook) |
| calico_rr | Route reflectorهای Calico |

### متغیرهای Inventory (به ازای هر میزبان)
```yaml
kubespray_node_labels:
  topology.kubernetes.io/zone: zone-a
  workload-type: general
kubespray_node_taints:
  - key: "dedicated"
    value: "gpu"
    effect: "NoSchedule"
```

## پیکربندی CNI

### Cilium (Baseline اصلی)
```yaml
kubespray_cni_plugin: "cilium"
kubespray_cilium_tunneling_mode: "vxlan"  # vxlan, geneve, disabled
kubespray_cilium_hubble_enabled: true
kubespray_cilium_kube_proxy_replacement: "strict"  # disabled, partial, strict
kubespray_cilium_ipam_mode: "cluster-pool"
```

**پورت‌های مورد نیاز:**
- VXLAN: UDP 8472 (وقتی tunneling_mode=vxlan)
- Geneve: UDP 6081 (وقتی tunneling_mode=geneve)
- Hubble Relay: TCP 4245
- Hubble UI: TCP 12000

### Calico (جایگزین)
```yaml
kubespray_cni_plugin: "calico"
kubespray_calico_vxlan_enabled: false
kubespray_calico_wireguard_enabled: false
kubespray_calico_typha_enabled: false
```

**پورت‌های مورد نیاز (وقتی VXLAN فعال است):**
- VXLAN: UDP 4789
- WireGuard: UDP 51820 (وقتی فعال است)

## رجیستری و یکپارچه‌سازی آفلاین

### رجیستری داخلی
```yaml
kubespray_container_registry: "harbor.internal:5000"
kubespray_registry_ca_cert_path: "/etc/ssl/certs/harbor-ca.crt"
kubespray_registry_auth_enabled: true
```

### استیج آرتیفکت آفلاین
```bash
# روی میزبان staging متصل:
# ۱. Pull تمام ایمیج‌های مورد نیاز
kubespray-offline-images.sh --registry harbor.internal:5000 --output /tmp/kubespray-images.tar

# ۲. انتقال به محیط air-gapped
# ۳. Load ایمیج‌ها در Harbor داخلی
```

**دسته‌های ایمیج مورد نیاز:**
- کامپوننت‌های Kubernetes (kube-apiserver، kube-controller-manager، kube-scheduler، kube-proxy، etcd، coredns، pause)
- CNI (Cilium/Calico، Hubble، operator)
- Containerd (اگر از پکیج سیستمی استفاده نمی‌شود)
- Add-ons (metrics-server، local-path-provisioner، و...)

## امنیت استقرار

### چک‌های Preflight
Preflight استقرار موارد زیر را اعتبارسنجی می‌کند:
- تگ релиز Kubespray برابر v2.32.0 (تأیید شده عبر `git describe --tags`)
- نسخه Kubernetes در بازه پشتیبانی (1.34.x - 1.36.x)
- پرچم تأیید نسخه Kubernetes (`kubernetes_version_verified: true`)
- انتخاب CNI معتبر و پیکربندی شده (cilium یا calico)
- CIDRها تداخل ندارند
- گروه‌های الزامی inventory با شمارش درست وجود دارند
- نودهای etcd زیرمجموعه کنترل‌پلین هستند (topology stacked)
- گواهی CA رجیستری موجود است
- محیط نود کنترل آماده است (venv، collections، سورس Kubespray)
- پیش‌نیازهای نودهای هدف کامل شده‌اند (رول k8s-node-prereqs)

### تأیید اپراتور الزامی
استقرار **بدون تأیید صریح اجرا نمی‌شود**. تأیید باید Boolean JSON باشد:
```bash
-e '{"kubespray_deploy_mode":"deploy","kubespray_operator_approval":true}'
```

**مهم**: مقادیر رشته‌ای (`"true"`، `"yes"`، `"1"`) رد می‌شوند. فقط boolean `true` از preflight می‌گذرد.

### بدون تغییر خودکار
- Preflight تغییری در نودهای هدف ایجاد نمی‌کند
- استقرار فقط بعد از اقدام صریح اپراتور اجرا می‌شود
- هیچ reset یا استقرار بی‌نظارت کلاستر وجود ندارد

## آپگرید و Scale-Out

**در این task پیاده‌سازی نشده.** کارهای آینده شامل:
- آپگرید نسخه Kubernetes (rolling)
- Scale-out کنترل‌پلین
- Scale-out worker nodes
- مدیریت عضوهای etcd
- مهاجرت CNI

## عیب‌یابی

### شکست‌های Preflight
```bash
# بررسی اعتبارسنجی خاص
ansible-playbook -i inventories/kubespray/production/hosts.yml playbooks/kubespray-deploy.yml -e kubespray_preflight_check_all=true -v
```

### مشکلات نود کنترل
```bash
# تأیید virtual environment
/opt/kubespray-venv/bin/ansible --version
/opt/kubespray-venv/bin/ansible-galaxy collection list

# تأیید سورس Kubespray
cd /opt/kubespray && git describe --tags
```

### مشکلات نودهای هدف
```bash
# تأیید پیش‌نیازها
ansible all -i inventories/production/hosts.yml -m shell -a "crictl info"
ansible all -i inventories/production/hosts.yml -m shell -a "swapon --show"
ansible all -i inventories/production/hosts.yml -m shell -a "stat -fc %T /sys/fs/cgroup"
```

## محدودیت‌ها

1. **بدون استقرار خودکار کلاستر** - نیاز به اقدام صریح اپراتور
2. **بدون جریان کار آپگرید** - Task جداگانه در آینده
3. **بدون جریان کار Scale-out** - Task جداگانه در آینده
4. **تأیید patch Kubernetes لازم است** - مرحله دستی؛ استقرار مسدود اگر `kubernetes_version_verified: false`
5. **Air-Gap کامل هنوز پشتیبانی نمی‌شود** - وابستگی‌های نود کنترل نیاز به استیج دارند; Ansible collections/Python deps فاقد مسیر استیج داخلی
6. **پیکربندی GPU worker پیاده‌سازی نشده** - نیاز به رول GPU
7. **تأیید کانفیگ کرنل Cilium/Calico ناقص** - برخی کانفیگ‌های کرنل نیاز به چک دستی اپراتور (عدم وجود `/boot/config-*` یا `/proc/config.gz` روی همه سیستم‌ها)

## مراجع

- [راهنمای آماده‌سازی OS](os-preparation.md)
- [یادداشت‌های ریلیز Kubespray v2.32.0](https://github.com/kubernetes-sigs/kubespray/releases/tag/v2.32.0)
- [Kubespray v2.32.0 README Component Versions](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/README.md#supported-components)
- [Kubespray v2.32.0 Requirements.txt](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/requirements.txt)
- [مستندات Cilium 1.20](https://docs.cilium.io/en/v1.20/)
- [مستندات Calico 3.31](https://docs.tigera.io/calico/3.31/)
- [Kubespray Deployment Guide (English)](../en/kubespray-deployment.md)

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-24*