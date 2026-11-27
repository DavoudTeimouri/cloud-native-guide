# Kernel and Networking Preparation

ماژول‌های کرنل، تنظیمات sysctl و پیکربندی فایروال برای گره‌های کربرنتیز.

## ماژول‌های کرنل

### ماژول‌های مورد نیاز

| ماژول | هدف |
|--------|------|
| overlay | OverlayFS برای ذخیره‌سازی kontener |
| br_netfilter | فیلتر netto برای شبکه کربرنتیز |
| ip_vs | سرور مجازی IP برای kube-proxy |
| ip_vs_rr | زمان‌بندی دور و زدن IPVS |
| ip_vs_wrr | زمان‌بندی وزن‌دار دور و زدن IPVS |
| ip_vs_sh | زمان‌بندی هش کوتاه‌ترین IPVS |
| nf_conntrack | پیگیری اتصال nettoffilter |

### بارگذاری ماژول‌ها

```bash
# بارگذاری ماژول‌های مورد نیاز
modprobe overlay
modprobe br_netfilter
modprobe ip_vs
modprobe ip_vs_rr
modprobe ip_vs_wrr
modprobe ip_vs_sh
modprobe nf_conntrack

# پایدار‌سازی در راه‌اندازی مجدد
cat > /etc/modules-load.d/k8s.conf << 'EOF'
overlay
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack
EOF

# تأیید بارگذاری ماژول‌ها
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'
```

## تنظیمات sysctl

### فایل پیکربندی

```ini
# /etc/sysctl.d/99-kubernetes.conf
# شبکه
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# حافظه
vm.swappiness = 10
vm.overcommit_memory = 1
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1

# سیستم فایل
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 8192
fs.file-max = 2097152

# کرنل
kernel.panic = 10
kernel.panic_on_oops = 1
kernel.keys.root_maxkeys = 1000000
kernel.keys.root_maxbytes = 25000000
```

### اعمال و تأیید

```bash
# اعمال تنظیمات sysctl
sysctl -p /etc/sysctl.d/99-kubernetes.conf

# تأیید تنظیمات کلیدی
sysctl net.bridge.bridge-nf-call-iptables net.ipv4.ip_forward net.ipv4.conf.all.rp_filter
```

## پیکربندی فایروال

### nftables (خانواده دبیان)

```nft
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        ct state established,related accept
        iif "lo" accept
        tcp dport 22 ct state new accept
        tcp dport 6443 ct state new accept
        tcp dport 2379-2380 ct state new accept
        tcp dport 10250 ct state new accept
        tcp dport 10259 ct state new accept
        tcp dport 10257 ct state new accept
        tcp dport 30000-32767 ct state new accept
        udp dport 8472 ct state new accept  # VXLAN (Cilium)
        udp dport 6081 ct state new accept  # Geneve (Cilium)
        udp dport 4789 ct state new accept  # VXLAN (Calico/overlay)
        icmp type echo-request accept
        ct state invalid drop
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
        ct state established,related accept
    }
    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

### firewalld (خانواده RHEL)

```bash
# فعال کردن و شروع firewalld
systemctl enable --now firewalld

# افزودن پورت‌های کربرنتیز
firewall-cmd --permanent --add-port=6443/tcp
firewall-cmd --permanent --add-port=10250/tcp
firewall-cmd --permanent --add-port=8472/udp
firewall-cmd --permanent --add-port=6081/udp
firewall-cmd --permanent --add-port=30000-32767/tcp

# بارگذاری مجدد و تأیید
firewall-cmd --reload
firewall-cmd --list-all
```

### اقدامات ایمنی

- **پورت SSH 22 همیشه مجاز است** — قفل کردن پیش‌فرض بدون قفل شدن مدیر
- **بازنویسی ناامن پیکربندی SSH نیست** — قوانین فایروال `/etc/ssh/sshd_config` را تغییر نمی‌دهند

## منابع

- [راهنمای آماده‌سازی سیستم‌عامل](os-preparation.md)
- [عملیات خانواده RHEL](../operating-systems/host-configuration.md)
- [عملیات خانواده دبیان](../operating-systems/host-configuration.md)

---\n*وضعیت: پیش‌نویس | مالک: تیم پلتفرم | آخرین بازبینی: 2026-11-25*
