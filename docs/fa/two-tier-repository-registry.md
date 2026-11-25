# معماری دو cấp مخازن و Rutgers

راهنمای عملی برای راه‌اندازی و مدیریت معماری دو لایه مخزن و د瑞ج برای محیط‌های محدود و capable-オフ‌لاین. این سند از معماری تعریف‌شده در `architecture/two-tier-repository-registry.md` حمایت می‌کند.

> نکته: این سند یک precursors翻訳 (ترجمه مرجع) است و متن انگلیسی اصلی در `docs/en/two-tier-repository-registry.md` منبع پستی است.

## وضعیت

**وضعیت: پیش‌نویس | مالک: تیم پلتفرم | آخرین بازبینی: ۲۰۲۶-۱۱-۲۵**

## ۱. بررسی معماری

معماری بین **امدادی خارجی (External Upstream)** (دسترسی کنترل‌شده به اینترنت) و **مدیریت مخزن و د瑞ج داخلی (Internal Repository/Registry Manager)** (توزیع داخلی) جدا می‌کند. لایه پایگاه ثابت (Reverse Proxy) در جلوی backendهای داخلی قرار می‌گیرد تا مشتریان همیشه از نام‌های DNS پایاده استفاده کنند.

### لایه‌های منطقی

| لایه | نقش | دسترسی به اینترنت |
|---|---|---|
| امدادی خارجی | اتصال به مخازن بسته عمومی و د瑞ج‌های کonteйнر؛ کش/همگام‌سازی ازgaslight فقط مجاز بلوک‌ها | بله — خروج محدود به URL/IP‌های مجاز |
| مدیریت مخزن و د瑞ج داخلی | مخازن پراکسی/کیش (آینه‌سازی عمومی) و مخازن/د瑞ج‌های میزبانی‌شده (انتشار داخلی تیم‌ها) | خیر — فقط داخلی |
| لایه پایگاه ثابت (Reverse Proxy) | Reverse Proxy (HAProxy/Nginx) با DNS پایاده، TLS، مجوزرسی، بررسی سلامت، تنازع لود | خیر — فقط داخلی |

### تضمین‌های کلیدی

- گره‌های داخلی (کارگران، رنرهای CI، میزبان‌های اتوماسیون) دسترسی خروجی به اینترنت **ندارند**. همه بازیابی فایل‌ها از طریق مدیریت مخزن و د瑞ج داخلی انجام می‌گیرد.
- مشتریان داخلی از نام‌های DNS پایاده (مثلاً `nexus.internal`، `harbor.internal`) استفاده می‌کنند، نه نام‌های backend.
- مهاجرت backend بدون تأثیر بر مشتریان transparent است وقتی قرارداد پایگاه (DNS، TLS، سطح API، مجوزرسی) حفظ شود.
- تایید خ同时 از تایید تایید است.

## ۲. مرزهای امنیتی و شبکه

### Fromtopology شبکه (نمای متنی)

```
+----------------------+          +----------------------+          +----------------------+
|  اینترنت عمومی     |          |  امدادی خارجی    |          |  شبکه داخلی       |
|  (ناتمکن)           |          |  (خروج کنترل‌شده) |          |  (ت partially可信) |
+----------+-----------+          +----------+-----------+          +----------+-----------+
           |                                  |                                  |
           | خروج فقط از طریق رنج‌های URL/IP مجاز |  همه جریان فایل از طریق            |
           |                                  |  مدیریت مخزن و د瑞ج داخلی           |
           v                                  v                                  v
+----------------------+          +----------------------+          +----------+-----------+
|  د瑞ج‌های عمومی     |          |  مخازن عمومی       |          |  مخزن Nexus        |
|  (docker.io, ghcr.io,|          |  (yum, apt, PyPI,   |          |  (rpm/deb/pypi/npm)  |
|   quay.io, و غیره)   |          |   npm, go)          |          |  میزبانی شده + پراکسی |
+----------------------+          +----------------------+          +----------+-----------+
                                                  |              |
                                                  |              +--------->|  Harbor            |
                                                  |              +-------------->|  (تصاویر کonteйнر) |
                                                  |                                 +----------+-----------+
                                                                           پراکسی + میزبانی     |
                                                                                  +----+------+
                                                                                   |    |
                                                                                   v    v
                                                                           لایه پایگاه ثابت
                                                                           HAProxy / Nginx
                                                                           DNS پایاده,
                                                                           TLS, مجوزرسی,
                                                                           حفظ مسیر,
                                                                           تنازع لود,
                                                                           بررسی سلامت,
                                                                           مقياس و هشدار
```

### مرزهای امنیتی

| منطقه | سطح اعتبار | قوانین |
|---|---|---|
| اینترنت عمومی | ناتمکن | خروج فیلتر و نظارت می‌شود؛ فقط URL/IP‌های مجاز از امدادی خارجی قابل رسانی است. |
| امدادی خارجی | تاedium معتبر | تنها conductor مجاز به د瑞ج‌های عمومی؛ میزبانان در DMZ/مفنون‌شده؛ خروج محدود به URL/IP‌های مجاز. |
| شبکه داخلی | تاedium معتبر (マイکرو-سگمنت شده) | هیچ گره داخلی دسترسی مستقیم به اینترنت ندارد. بارهای کاری هر صدا زدهی سرویس را même در شبکه داخلی احراز هویت و مجوز می‌دهند. Backendهای مخزن و د瑞ج هرچender مجوزرس را اعمال می‌کنند. |

### قوانین فایروال

| جهت | مبدأ | مقصد | هدف‌ها | هدف |
|---|---|---|---|---|
| خروجی | میزبان امدادی خارجی | مخازن بسته عمومی (yum, apt, PyPI, npm) | 80, 443 | بازیابی بسته‌ها |
| خروجی | میزبان امدادی خارجی | د瑞ج‌های کonteйнر عمومی (docker.io, ghcr.io, quay.io, registry.k8s.io) | 443 | کشیدن تصاویر کonteйнر |
| خروجی | مشتریان داخلی | امدادی خارجی (محدود) | 80, 443 | دسترسی غیرمستقیم از طریق پراکسی |
| رد | گره‌های داخلی | اینترنت عمومی | همه | جلوگیری از خروج |

**رفتار با شکست بسته**: سیاست شبکه پیش‌فرض `drop` است. هیچ پورت مدیریت (SSH 22, RDP 3389) به اینترنت عمومی公開 نمی‌شود. دسترسی مدیریت فقط از بخش مدیریت محدود می‌شود.

## ۳. عهدنامه DNS و پایگاه پایا

همه مشتریان داخلی از آدرس‌های پایگاه پایا استفاده می‌کنند. نام‌های backend هرگز در پیکربندی مشتری ظاهر نشود.

| پای پایا | سرویس backend | هدف |
|---|---|---|
| `nexus.internal` | مخزن Nexus (پراکسی + میزبانی) | مخازن بسته سیستم عامل (rpm/deb)، مخازن زبان (pypi/npm/go)، artefacts خام |
| `harbor.internal` | Harbor (پراکسی + میزبانی OCI) | تصاویر کonteйнر (د瑞ج OCI) |
| `harbor.internal/oci/` | د瑞ج OCI Harbor | کشیدن/ارسال تصویر |
| `harbor.internal/charts/` | د瑞ج چارت Harbor | چارت‌های Helm |
| `harbor.internal/platform/` | پروژه پلتفرم Harbor | تصاویر پلتفرم |

### عهدنامه DNS

- رکوردهای CNAME DNS به VIP تنازع لود اشاره می‌کنند.
- IPهای backend می‌توانند تغییر کنند بدون تأثیر بر مشتری.
- مهاجرت backend: گره‌های backend جدید را اضافه کنید، CNAME DNS را به‌روزرسانی کنید، گره‌های قدیمی را drain کنید. مشتریان نام پایگاه پایا را حفظ می‌کنند.
- تایید: آزمایش pull/install از یک مشتری خالص با استفاده از پایگاه پایا بعد از مهاجرت.

## ۴. الزامات فایروال و اتصال

### میزبان امدادی خارجی

- باید فقط به مخازن بسته عمومی و د瑞ج‌های کonteйнر مجاز برسد (فهرست مجاز).
- خروج محدود به رنج‌های URL/IP مجاز.
- نباید ترافیک دلخواه را برای مشتریان داخلی پراکسی کند.

### مشتریان داخلی

- نباید به اینترنت عمومی دسترسی داشته باشند.
- به خدمات مخزن و د瑞ج از طریق پایگاه پایا از طریق Reverse Proxy می‌رسند.

### دسترسی مدیریت

- SSH (22) / RDP (3389) به اینترنت عمومی δημοσιεύا نمی‌شود.
- فقط از بخش مدیریت محدود است.

## ۵. مراحل راه‌اندازی

### ۵.۱ آماده‌سازی میزبان امدادی خارجی

1. میزبان م 자신 را در DMZ یا بخش محدود prêts کنید.
2. قوانین فایروال خروجی را فقط برای URL/IPهای مجاز مخازن بسته عمومی و د瑞ج کonteйнر روی پورت‌های 80/443 تنظیم کنید.
3. اجزای کش امدادی خارجی را نصب کنید (مخازن پراکسی Nexus، پروژه‌های پراکسی Harbor).
4. فهرست مجاز امده بالا (نام‌ها، الگو، نسخه‌های artefact) را تنظیم کنید.
5. سیاست‌های همگام‌سازی را تنظیم کنید (بنگاه‌دار، به‌ازائه، یا یا).
6. اتصال خروجی به یک د瑞ج نمونه عمومی (مثلاً `docker.io`) و یک مخزن بسته عمومی را تایید کنید.

**نتیجه مورد انتظار**: `curl -I https://registry-1.docker.io/v2/` `200 OK` می‌دهد؛ `curl -I https://repo.example.com/` `200 OK` می‌دهد.

### ۵.۲ اجرای مدیریت مخزن و د瑞ج داخلی

1. مخزن Nexus (بسته سیستم عامل + زبان) و د瑞ج Harbor (تصاویر کonteйнر) را روی میزبان‌های داخلی اجرا کنید.
2. مخازن پراکسی Nexus را به کش امدادی خارجی (نه به منابع عمومی مستقیم) تنظیم کنید.
3. پروژه‌های پراکسی Harbor را به کش امدادی خارجی Harbor تنظیم کنید.
4. پروژه‌ها/فضاهای نام برای تیم‌های داخلی در Harbor بسازهاه.
5. نقش‌های RBAC (خواندن، نوشتن، حذف، مدیریت) را در هر پروژه/فضای نام تنظیم کنید.
6. حساب‌های سرویس برای رنرهای CI با مجوزهای محدوده بسازها.

**نتیجه مورد انتظار**: `curl -k https://nexus.internal/repository/rpm-oraclelinux/` متادیتای مخزن برمی‌گرداند؛ `curl -k https://harbor.internal/api/v2.0/projects` لیست پروژه‌ها را برمی‌گرداند (احراز‌هویت شده).

### ۵.۳ اجرای لایه پایگاه ثابت (Reverse Proxy)

1. HAProxy یا Nginx را به عنوانReverse Proxy جفت (VRRP/keepalived یا VIP کلود) اجرا کنید.
2. نام‌های DNS پایاده (`nexus.internal`، `harbor.internal`) را به VIP LB تنظیم کنید.
3. TLS با گواهینامه‌های امضا شده CA داخلی در پایان کانکشن تنظیم کنید.
4. بررسی‌های سلامت backend را تنظیم کنید (`/health`، `/service/rest/v1/status`، `/api/v2.0/health` برای Harbor).
5. قوانین حفظ مسیر/نویسی مجدد مسیر را تنظیم کنید که مسیرهای پایاده را به مسیرهای backend نگاشت می‌کند.
6. محدودیت‌های زمان و اندازه بدنه را تنظیم کنید (پیش‌فرض: ۳۰ ثانیه اتصال، ۳۰۰ ثانیه خواندن، ۱۰۰ مگابایت حداکثر بدنه؛ برای بلوک‌های OCI بزرگ قابل تنظیم).
7. حذف backend ناکارآمد از چرخه را اضافه کنید.

**نتیجه مورد انتظار**: `curl -I https://nexus.internal/repository/rpm-oraclelinux/` (از طریق پراکسی) `200 OK` می‌دهد؛ backend ناکارآمد در فاصله بررسی سلامت از چرخه حذف می‌شود.

### ۵.۴ پیکربندی довер CA داخلی

1. CA داخلی بسازید (뿌ی آفلاین در Vault PKI، میانه آنلاین).
2. گواهینامه‌های برگ را از طریق cert-manager با CA داخلی صادر کنید.
3. گواهینامه CA داخلی را به فروشگاه‌های довер همه مشتریان داخلی توزیع کنید.
4. تمدید خودکار گواهینامه را (کوتاه‌عمر، ۷–۳۰ روز) تنظیم کنید.
5. لغو مجوز را از طریق CRL/OCSP یا تزریق خودکار تنظیم کنید.

**نتیجه مورد انتظار**: `curl https://nexus.internal/` (با TLS) بدون خطای گواهینامه در مشتریان داخلی اجرا می‌شود.

### ۵.۵ پیکربندی مصرف مشتری

1. مدیریت بسته‌های سیستم عامل (DNF/YUM، APT) را به URLهای مخزن `nexus.internal` تنظیم کنید.
2. مرآة د瑞ج containerd را به `harbor.internal` تنظیم کنید.
3. imagePullSecret Kubernetes برای پروژه‌های میزبانی‌شده Harbor تنظیم کنید.
4. رنرهای CI/CD را برای push/pull از طریق حساب‌های سرویس فدراسیون OIDC (بدون differentiated credential) تنظیم کنید.

## ۶. نمونه‌های پیکربندی

### ۶.۱ مخزن DNF/YUM (خاندان RHEL)

```ini
# /etc/yum.repos.d/internal.repo
[ol9-baseos]
name=Oracle Linux 9 Baseos (داخل)
baseurl=https://nexus.internal/repository/ol9-baseos/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-baseos/RPM-GPG-KEY-oracle

[ol9-appstream]
name=Oracle Linux 9 AppStream (داخل)
baseurl=https://nexus.internal/repository/ol9-appstream/
enabled=1
gpgcheck=1
gpgkey=https://nexus.internal/repository/ol9-appstream/RPM-GPG-KEY-oracle
```

### ۶.۲ مخزن APT (خاندDebian)

```bash
# /etc/apt/sources.list.d/nexus.list (اوبونتو ۲۴.۰۴ noble)
deb https://nexus.internal/repository/ubuntu-main/ noble main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-updates/ noble-updates main restricted universe multiverse
deb https://nexus.internal/repository/ubuntu-security/ noble-security main restricted universe multiverse
```

### ۶.۳ مرآة د瑞ج containerd

```toml
# /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://harbor.internal"]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry.k8s.io"]
  endpoint = ["https://harbor.internal"]

[plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal".tls]
  ca_file = "/etc/containerd/certs.d/harbor.internal/ca.crt"
```

### ۶.۴ imagePullSecret Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: harbor-registry
  namespace: default
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: <base64-encoded-auth>
```

```bash
# اعمال در فضای نام‌هایی که از د瑞ج میزبانی‌شده Harbor کش می‌کنند
kubectl apply -f harbor-registry-secret.yaml
kubectl patch serviceaccount default -p '{"imagePullSecrets":[{"name":"harbor-registry"}]}'
```

### ۶.۵ Reverse Proxy (HAProxy) — Illustrative, قبل از تولید تایید شود

```haproxy
# /etc/haproxy/haproxy.cfg — پیکربندی Illustrative؛ قبل از تولید تایید شود
frontend https-in
    bind *:443 ssl crt /etc/ssl/certs/harbor.internal.pem
    mode http
    option http-server-close
    acl is_nexus req.hdr(host) -i nexus.internal
    acl is_harbor req.hdr(host) -i harbor.internal
    use_backend nexus_backend if is_nexus
    use_backend harbor_backend if is_harbor

backend nexus_backend
    mode http
    balance roundrobin
    option httpchk GET /service/rest/v1/status
    server nexus1 10.20.0.51:8081 check
    server nexus2 10.20.0.52:8081 check
    timeout connect 30s
    timeout server 300s

backend harbor_backend
    mode http
    balance roundrobin
    option httpchk GET /api/v2.0/health
    server harbor1 10.20.0.61:443 check ssl verify none
    server harbor2 10.20.0.62:443 check ssl verify none
    timeout connect 30s
    timeout server 300s
    timeout tunnel 3600s
```

**نکته جایگزین**: مقادیر `10.20.0.51`، `10.20.0.61`، مسیرهای گواهینامه و timeoutها را با مقادیر محیط خود جایگزین کنید. این پیکربندی را قبل از تولید در محیط تولید استفاده نکنید.

## ۷. احراز هویت و مجوز

### احراز هویت

- هیچ credential مخزن یا د瑞ج در کد منبع سورس Controlled ذخیره نمی‌شود.
- رنرهای CI از طریق فدراسیون OIDC احراز هویت می‌شوند (مثلاً `id-token: write` گیت‌هاب اکشنز → ربات مخزن/د瑞ج peril به عنوان ایوال OIDC). توکن‌های یکبار مصرف per-job؛ کلیدهای dauerhaft نیستند.
- عامل‌های انسانی از توکن‌های حساب‌های سرویس کوتاه‌عمر استفاده می‌کنند. رمزهای عبور ادمین مشترک ممنوع است.
- میزبان امدادی خارجی credentialهای Pull خود را برای Pull از منابع عمومی دارد؛ این credentialها هرگز با مشتریان داخلی به اشتراک نمی‌گذارند.

### مجوز (RBAC)

| نقش | مجوزها | دامنه |
|---|---|---|
| admin | خواندن، نوشتن، حذف، مدیریت | در هر پروژه Harbor / مخزن Nexus |
| developer | خواندن، نوشتن | در هر پروژه/فضای نام |
| reader | خواندن | در هر پروژه/فضای نام |
| حساب سرویس CI | خواندن، نوشتن (push/pull) | مختص به پروژه/مخزن خاص |

- cotas در هر پروژه/فضای نام اعمال می‌شود (مثلاً حداکثر GB در هر تیم).
- سیاست‌های حفظ/پاکسازی قابل تنظیم (حفظ N نسخه، حفظ نسخه‌های قدیمی‌تر از X روز، برچسب‌های ناپذیر تغییر).
- هر عملیات خواندن/نوشتن/حذف با کاربر/حساب سرویس، artefact و expert ثبت می‌شود.

## ۸. TLS و پیکربندی گواهینامه

### سلسله مراتبی گواهینامه

| گواهینامه | ذخیره‌سازی | تمدید | لغو |
|---|---|---|---|
| CA ریشه داخلی | آفلاین (Vault PKI) | با سیاست CA | اینجا (ریشه) |
| CA میانه داخلی | آنلاین (cert-manager) | با سیاست CA | CRL/OCSP |
| گواهینامه برگ Reverse Proxy | cert-manager | تمدید خودکار (۷–۳۰ روز) | CRL/OCSP یا تزریق خودکار |

### довре مشتری

- همه مشتریان داخلی CA داخلی را довCalculate می‌کنند.
- توزیع گواهینامه از طریق روش الثقة CA سیستم عامل (مسیر `operating-systems/host-configuration.md`).

### حالت TLS

| حالت | زمان استفاده | تفاوت |
|---|---|---|
| پایان TLS در Reverse Proxy | ساده‌سازی مدیریت گواهینامه؛ ترافیک داخلی ممکن است بدون TLS باشد | پایان TLS در Reverse Proxy؛ رمزنگاری متوالی کمتر |
| TLS به‌صورت Passthrough | رمزنگاری متوالی نیاز دارد | مدیریت گواهینامه پیچیده‌تر در Backendها |

## ۹. پیکربندی مخزن پراکسی و میزبانی‌شده

### مخازن پراکسی/کیش

**حالت استفاده**: آینه‌سازی منابع عمومی تا مشتریان داخلی هرگز به منابع عمومی نرسند.

| جنبه | پیکربندی |
|---|---|
| اتصال به منابع | خروج فقط از Component پراکسی؛ دسترسی مشتریان داخلی به منابع عمومی ممنوع است |
| جریان artefact | منبع عمومی → پراکسی امدادی خارجی → مخزن کش داخلی → مشتریان داخلی |
| فرمت‌های بسته | پراکسی Nexus برای rpm/deb/pypi/npm/helm/raw |
| پایگاه‌های پیش‌بینی‌شده | `/repository/rpm-oraclelinux/`، `/repository/deb-ubuntu/`, `/repository/pypi/`, و غیره |
| مجوزرسی | مجوزرسی داخلی به‌صورت محلی مدیریت می‌شود؛ هدرهای مجوزرسی منبع ارسال نمی‌شوند |
| رفتار validate | پراکسی validateهای منابع محافظت می‌کند |

### مخازن/د瑞ج‌های میزبانی‌شده

**حالت استفاده**:teams داخلی artefactهای خود را منتشر و می‌خواهند.

| جنبه | پیکربندی |
|---|---|
| RBAC | نقش‌های reader/developer/admin در هر فضای نام/پروژه |
| cotas | cotas ذخیره‌سازی در هر پروژه/فضای نام |
| حفظ | قابل تنظیم: حفظ N نسخه، حفظ نسخه‌های قدیمی‌تر از X روز، برچسب‌های ناپذیر تغییر |
| ثبت‌نامAConscious | هر عملیات خواندن/نوشتن/حذف با کاربر/حساب سرویس، artefact و expert ثبت می‌شود |
| Backup/Restore | سناپ‌ Shot‌های روزانه دیتابیس + بلوک‌ها؛ بازسازی نقطه‌ای سی زما |

**پ contrast**: برای آینه‌سازی منبع عمومی مجاز از پراکسی استفاده کنید. برای امکانteams داخلی برای انتشار و استفاده از artefactهای خود از میزبانی‌شده استفاده کنید.

## ۱۰. رونمایی تیم/پروژه

1. پروژه Harbor یا مخزن Nexus را برای تیم بسازید.
2. نقش‌های RBAC (reader/developer/admin) را به اعضای تیم و حساب‌های سرویس تخصیص دهید.
3. cotas (حداکثر GB در هر تیم) را تنظیم کنید.
4. سیاست حفظ را تنظیم کنید (نحفظ N نسخه / برچسب‌های ناپذیر تغییر).
5. URL پایگاه پایا (`nexus.internal` یا `harbor.internal`) را به تیم ارائه دهید.
6. پیکربندی OIDC رنر CI برای push/pull را به تیم ارائه دهید.
7. قرارداد نام‌گذاری artefact و الزامات نسخه‌پینینگ تیم را سند کنید.

**نتیجه مورد انتظار**: تیم می‌تواند `docker push harbor.internal/team/app:1.2.3` و `dnf install` از `nexus.internal` را بدون credentials در متن خام انجام دهد.

## ۱۱. همگام‌سازی artefact

### گردش کار همگام‌سازی

1. منابع معتبر را در فهرست مجاز تعریف کنید (تیم پلتفرم).
2. میزبان امدادی خارجی artefactهای منتخب را از منابع معتبر sync/کشد می‌کند.
3. validate (SHA-256) و امضا (cosign, GPG, apt-key) را زمانی که قابل Apply است تایید کنید.
4. artefactهای تایید شده را از طریق شبکه داخلی به مدیریت مخزن و د瑞ج داخلی منتقل کنید (`skopeo copy` برای OCI، `curl --upload-file` برای Nexus، `helm push` برای چارت‌ها).
5. فهرست مجاز artefact را در گام انتقال اجرا کنید (فقط نسخه‌های/نام‌های مجاز منتقل شوند).
6. artefact را در مخزن/د瑞ج داخلی مناسب (perwatch/کیش یا میزبانی‌شده) منتشر کنید.
7. دسترسی داخلی + validate کنید (آزمایش pull؛ validate `repomd.xml` / نمایش OCI readable).
8. وضعیت همگام‌سازی و رویدادهای ثبت‌نام را ثبت کنید (نام artefact+نسخه، URL منبع، SHA-256، وضعیت امضا، expert، نتیجه، مسیر مقصد).

### نسخه‌پینن و مرجع ناپذیر تغییر

- artefactها به نسخه دقیق Merje (مثلاً `python:3.11-slim`، `nginx:1.28.0`) Merje می‌شوند. هیچ تگ `latest` در تولید.
- digestهای Docker/OCI ناپذیر تغییر است: `harbor.internal/oci/owner-repo@sha256:<digest>`.
- نسخه‌های مخزن Nexus پس از انتشار ناپذیر تغییر است.

### مدیریت شکست همگام‌سازی

| شرط | اقدام |
|---|---|
| پاسخ غیر-2xx از منبع | ثبت با جزئیات خطا + وضعیت HTTP؛ تلاش مجدد با بک‌اوفس Ираксить (بیشترین ۵ تلاش، فاصله ۳۰ ثانیه) |
| validate ناموفق | همگام‌سازی ناکارآمد؛ artefact را PENDING علامت‌گذاری کنید؛ هشدار |
| امضا ناموفق | همگام‌سازی ناکارآمد؛ artefact را PENDING علامت‌گذاری کنید؛ هشدار (validate به تنهایی ثبوت اصالت artefact نیست) |
| شکست دائمی | بازآغاز دستی یا انتظار تا الدور بعدی |

## ۱۲. Backup و Restore

| Component | روش Backup | تكرکر | تست بازسازی |
|---|---|---|---|
| مخزن Nexus | Backup بلوک‌ستور + صادرات پیکربندی | روزانه | سه‌ماهه |
| د瑞ج Harbor | صادرات/وارد성 آفلاین + سناپ‌ Shot دیتابیس | روزانه | سه‌ماهه |
| پیکربندی Reverse Proxy | پیکربندی دستوری (فایل cfg HAProxy، conf Nginx) | در هر تغییر |according to need |
| کش امدادی خارجی | سناپ Shot کش | روزانه | سه‌ماهه |

**روند بازسازی**: بازسازی از پیکربندی backup + حالت backend فعلی; تایید pull/install از یک مشتری خالص.

## ۱۳. HA و بازسازی شکست

| شکست | تشخیص | بازسازی |
|---|---|---|
| گره backend ناکارآمد | بررسی سلامت Reverse Proxy (`/health`، `/service/rest/v1/status`، `/api/v2.0/health` برای Harbor) | از چرخه حذف فوری؛ هشدار |
| امدادی خارجی در دسترس نیست | هشadar شکست همگام‌سازی (>۱٪ نرخ شکست یا >۵ دقیقه خارج شدن) | artefact در PENDING می‌ماند؛ بازآغاز دستی در صورت بازیابی |
| امدادی خارجی تهدید شده | تشخیص تهدید | همه artefactهای همگام‌سازی شده را لغو کنید؛ validateされлируйте validateها در برابر منبع؛ ریشه‌های الثقة را قبل از retomettن کشیدن artefact به مشتری تغییر دهید |
| Reverse Proxy ناکارآمد | جستار VRRP/keepalived یا LB کلود | جستار به گره Reverse Proxy secundaria |

## ۱۴. دستورات validate و خروج‌های مورد انتظار

### اتصال شبکه

```bash
# تایید اینکه مشتری داخلی نمی‌تواند به اینترنت عمومی برسد (بسته بسته)
curl -I https://registry-1.docker.io/v2/
# خروج مورد انتظار: اتصال رد شده/time out (محدود شده)

# تایید اینکه میزبان امدادی خارجی می‌تواند به د瑞ج عمومی برسد
curl -I https://registry-1.docker.io/v2/
# خروج مورد انتظار: HTTP/1.1 200 OK
```

### دسترسی به مخزن از طریق پای پایا

```bash
# تایید مخزن پراکسی Nexus (داخل، از طریق DNS پایاده)
curl -I https://nexus.internal/repository/rpm-oraclelinux/
# خروج مورد انتظار: HTTP/1.1 200 OK

# تایید API Harbor (احراز‌هویت شده)
curl -k -H "Authorization: Bearer <token>" https://harbor.internal/api/v2.0/projects
# خروج مورد انتظار: لیست پروژه‌ها در قالب JSON
```

### validate مدیریت بسته

```bash
# خانواده RHEL: تایید متادیتا DNF
dnf repolist ol9-baseos
# خروج مورد انتظار: ol9-baseos با متادیتا فهرست شده است

# خانواده Debian: تایید APT
apt-get update
# خروج مورد انتظار: بدون خطای امضا; بسته‌ها از nexus.internal
```

### validate containerd

```bash
# تایید مرآة د瑞ج containerd
crictl info
# خروج مورد انتظار: runtime endpoint متصل؛ بدون خطای د瑞ج

# تایید کش تصویر از د瑞ج Harbor داخلی
crictl pull harbor.internal/oci/pause:3.9
# خروج مورد انتظار: تصویر کش شده است
```

### خلاصه نتایج مورد انتظار

| بررسی | خروج مورد انتظار |
|---|---|
| مشتری داخلی به اینترنت عمومی دسترسی دارد | Blocked (اتصال رد شده/Timeout) |
| میزبان امدادی خارجی به د瑞ج عمومی دسترسی دارد | 200 OK |
| پای پایا پایاده (`nexus.internal`) | 200 OK + متادیتای مخزن |
| containerd تصویر از `harbor.internal` کش می‌کند | تصویر کش شده است |
| متادیتا APT/DNF از مخزن داخلی | بدون خطا؛ بسته‌ها نصب می‌شوند |

## ۱۵. خطاهای رایج و عیب‌یابی

| علامت | علت محتمل | Raising |
|---|---|---|
| مشتری داخلی نمی‌تواند به اینترنت عمومی برسد | قانون جلوگیری از خروج در حال عملکرد صحیح | خطا نیست؛ از پای پایا داخلی استفاده کنید |
| `curl https://nexus.internal/` با خطای گواهینامه شکست می-CHAMD | CA داخلی در فروشگاه 신뢰 مشتری نیست | گواهینامه CA داخلی را توزیع کنید; فروشگاه را به‌روزرسانی کنید |
| `dnf install` شکست می‌دهد: متادیتای مخزن نامعتبر | پراکسی validateهای `repomd.xml` را محافظت نمی‌کند | پیکربندی پراکسی Nexus را تایید کنید که validateهای منبع را محافظت می‌کند |
| `crictl pull` شکست می‌دهد: unauthorized | imagePullSecret یا توکن ربات نامعتبر/ناسفة | حساب ربات Harbor را تنظیم کنید; imagePullSecret را اعمال کنید |
| artefact همگام‌سازی در PENDING علامت‌گذاری شده است | validate یا امضا ناموفق | در دسترس بودن منبع را بررسی کنید; validate را در برابر منبع بازآغاز کنید; artefact ناموفق را اجبار نکنید |
| backend از چرخه حذف شد | بررسی سلامت شکست می-CHAMD | پایگاه `/health` backend را بررسی کنید; گره را بازagain کنید یا جایگزین کنید |
| ارسال بلوک OCI بزرگ شکست می‌دهد | محدودیت اندازه بدنه بسیار کم است | محدودیت اندازه بدنه را افزایش دهید; آپلود التبستی را فعال کنید |

### راهنمای بازیابی

- **انقضای گواهینامه**: تمدید re-issue را از طریق cert-manager اجرا کنید؛ trusting CA داخلی را در مشتریان تایید کنید.
- **شکست همگام‌سازی**: لاگ‌های میزبان امدادی خارجی را بررسی کنید; فهرست مجاز URL منبع را تایید کنید; پس از باک‌اوفس تلاش مجدد کنید.
- **شکست احراز هویت**: scarf توکن OIDC/حساب ربات را تایید کنید; free RBAC را برای پروژه/فضای نام بررسی کنید.
- **backend در دسترس نیست**: پایگاه سلامت backend را تایید کنید; به گره secundaria جستار کنید; در صورت شکست دائمی هشدار دهید.

## ۱۶. محدودیت‌ها

- تیم完全ه آماده oof-line Ready ادعا نمی‌شود؛ این architektura یک مسیر همگام‌سازی متصل برایartifact acquisition فرض می‌کند.
- اجرای مدیریت مخزن و د瑞ج P10.1.4 را اصلاح یا جایگزین نمی‌کند.
- سرویس‌های Nexus، Harbor یا Proxy را در زیر Samenurse اجرا نمی‌کند.
- credentials یا رمزهای защиتى را در متن source Repo نمی‌ザード.
- نمونه‌های پیکربندی Illustrative قبل از تولید تایید نشده‌اند.
- Nexus تصویر scan/amضا Native ادعا نمی‌شود; Harbor برای scan/amضا تصاویر OCI (Trivy, Notary) استفاده می‌شود.

## مراجع

- [معماری دو cấp مخزن و د瑞ج (طراحی)](../../architecture/two-tier-repository-registry.md)
- [پیش‌نیازهای سیستم عامل](os-prerequisites.md)
- [پیکربندی مخزن](repository-configuration.md)
- [تهیه هسته و شبکه](kernel-networking-preparation.md)
- [پیش‌نیازهای Containerd](containerd-prerequisites.md)
- [ماتریس نسخه و سازگاری](../../compatibility/version-matrix.md)

---

*سند تولید شده برای WISS 004-P11.2 — معماری دو cấp مخزن و د瑞ج*
