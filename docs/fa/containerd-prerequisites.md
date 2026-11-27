#containerd پیش‌نیازها

نصب و پیکربندی containerd به عنوان زمان اجراkontener برای گره‌های کربرنتیز.

## نصب

### خانواده RHEL

```bash
# نصب containerd از آینه داخلی
dnf install -y containerd.io

# فعال کردن و شروع containerd
systemctl enable --now containerd

# تأیید
crictl version
crictl info
```

### خانواده دبیان

```bash
# نصب containerd از آینه داخلی
apt-get update && apt-get install -y containerd.io

# فعال کردن و شروع containerd
systemctl enable --now containerd

# تأیید
crictl version
crictl info
```

## پیکربندی

```toml
# /etc/containerd/config.toml
version = 2

[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "harbor.internal/base/pause:3.9"
  max_container_log_line_size = 16384

  [plugins."io.containerd.grpc.v1.cri".containerd]
    snapshotter = "overlayfs"
    default_runtime_name = "runc"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
      runtime_type = "io.containerd.runc.v2"
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
        SystemdCgroup = true

  [plugins."io.containerd.grpc.v1.cri".cni]
    bin_dir = "/opt/cni/bin"
    conf_dir = "/etc/cni/net.d"

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://harbor.internal/library"]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry.k8s.io"]
  endpoint = ["https://harbor.internal/k8s"]

[plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal".tls]
  ca_file = "/etc/containerd/certs.d/harbor.internal/ca.crt"
```

### تأیید

```bash
# تأیید پیکربندی containerd
containerd --config /etc/containerd/config.toml --validate

# بررسی وضعیت سرویس
systemctl is-active containerd

# بررسی نقطه انتهای CRI
crictl info

# بررسی آینه‌های ثبت‌شده
cat /etc/containerd/certs.d/*/hosts.toml
```

## سرProcess آفلاین

- **بدون دانلود عمومی.** پکیج‌ها و تصاویر containerd از آینه نکسوس/هاربور داخلی می‌آیند.
- **containerd 2.3.7** نسخه پین‌شده Kinbspray releasing-2.32 است.
- آینه‌های ثبت‌شده به هاربور داخلی برای docker.io، registry.k8s.io اشاره می‌کنند.

## منابع

- [راهنمای آماده‌سازی سیستم‌عامل](os-preparation.md)
- [عملیات خانواده RHEL](../operating-systems/host-configuration.md)
- [عملیات خانواده دبیان](../operating-systems/host-configuration.md)

---\n*وضعیت: پیش‌نویس | مالک: تیم پلتفرم | آخرین بازبینی: 2026-11-25*
