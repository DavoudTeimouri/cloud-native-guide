# نقشه راه پیاده‌سازی

این سند نقشه راه ۱۵ فاز پیاده‌سازی استک کلود-بومی را تعریف می‌کند.

## اصول

- وابستگی‌محور: هر فاز پیش‌نیازهای صریح دارد.
- قابل اجرا: هر فاز تحویل‌های قابل اجرا و معیارهای پذیرش دارد.
- تجدیدپذیر: rollback برای هر فاز تعریف شده.
- اولویت‌بندی: کارهای GPU/AI، multi-site، multi-datacenter در فازهای افزودنی (نه مسیر اصلی) قرار دارند.

---

## فاز ۱ — نیازمادها و معماری

| | |
|---|---|
| **هدف** | مستندسازی نیازمادها، فرضیات، معماری مرجع، تصمیمات اولیه، و خط پایه نسخه |
| **پیش‌نیازها** | هیچ |
| **تحویل‌ها** | `requirements/requirements-and-assumptions.md`، `architecture/*`، `decisions/ADR-0001..0025`، `compatibility/version-matrix.md` اولیه |
| **معیارهای پذیرش** | هر تصمیم معلق D-01..D-14 ثبت شده؛ هر ادعای نسخه URL منبع + تاریخ بررسی دارد؛ جدول failure-domain در برابر توپولوژی سایت مرور شده |
| **ریسک‌ها** | تصمیمات معلق بدون Owner → churn بازسازی بعداً |
| **تلاش** | ۸-۱۵ روز |
| **Rollback** | مستندات بله؛ تأثیر runtime ندارد |

---

## فاز ۲ — زیرساخت آرتیفکت آفلاین

| | |
|---|---|
| **هدف** | استقرار Harbor، Nexus، GitLab داخلی و mirror کردن تمام آرتیفکت‌ها |
| **پیش‌نیازها** | خط پایه نسخه فاز ۱؛ Harbor + Nexus استقرار یافته (VM یا bare metal)؛ CA داخلی برای TLS |
| **تحویل‌ها** | `offline-artifacts/artifact-matrix.md` (پر شده)، `staging-and-import.md`، کانفیگ repo/registry، runbookهای کانفیگ کلاینت |
| **معیارهای پذیرش** | هر آرتیفکت در ماتریس در سیستم داخلی import می‌شود؛ یک نود پاک می‌تواند بسته‌ها install کند، ایمیج pull کند، و Helm chart deploy کند بدون اینترنت؛ `skopeo inspect` و `apt-get update` با منابع داخلی موفقیت‌آمیز |
| **ریسک‌ها** | RK-01 وابستگی transit گم شده → blocked mid-deploy. Mitigation: dry-run کامل استیج روی کلاسترthrowaway قبل از production |
| **تلاش** | ۱۵-۲۵ روز |
| **Rollback** | مخازن additive هستند؛ وابستگی production تا فاز ۷ نیست |

---

## فاز ۳ — زیرساخت بنیادین

| | |
|---|---|
| **هدف** | DNS، NTP، PKI، هویت، Load Balancer، پایه‌های SSH/sudo، قوانین فایروال |
| **پیش‌نیازها** | رجیستری‌های فاز ۲ قابل دسترس؛ قطعات شبکه تخصیص یافته |
| **تحویل‌ها** | DNS (CoreDNS + forwarders)، NTP (chrony)، PKI (CA داخلی)، هویت (Keycloak)، load balancer (keepalived/haproxy)، خطوط پایه SSH/sudo، قوانین فایروال از ماتریس |
| **معیارهای پذیرش** | DNS forward و reverse resolve می‌کند؛ clock skew < ۱۰۰ ms بین نودها؛ CA cert توزیع و trusted شده؛ Keycloak توکن صادر می‌کند؛ VIP LB بین نودها failover می‌کند؛ ماتریس فایروال پیاده و با `nmap`/`ss` از میزبان‌های مجاز و ممنوعه اثبات شده |
| **ریسک‌ها** | پیکربندی شبکه بعداً diagnóstico سخت است؛ نگهداری `firewall-rules-generation.md` mapping |
| **تلاش** | ۱۰-۱۸ روز |
| **Rollback** | سرویس‌های standalone؛ وابستگی کلاستر نیست |

---

## فاز ۴ — اتوماسیون

| | |
|---|---|
| **هدف** | سرور مدیریت اتوماسیون (Ansible + AWX)، GitLab Runner، Vault (standalone، ۳ نود)، inventories، overlayهای `site-<env>`، قالب‌های pipeline CI |
| **پیش‌نیازها** | هویت فاز ۳ + میزبان‌های Vault؛ GitLab نصب شده |
| **تحویل‌ها** | سرور مدیریت اتوماسیون (Ansible + AWX)، GitLab runner، Vault (standalone، ۳ نود)، inventories، overlayهای `site-<env>`، قالب‌های pipeline CI |
| **معیارهای پذیرش** | `ansible all -m ping` از AWX موفق؛ یک MR در GitLab lint → ansible syntax → helm lint → policy → scan و در صورت failure block می‌کند؛ Vault seal/unseal با shareهای آفلاین کار می‌کند؛ audit log AWX قابل بازیابی؛ snapshot بکاپ Vault ایجاد و verify شده |
| **ریسک‌ها** | RK-02 SPOF اتوماسیون → نود standby دوم + rebuild documented |
| **تلاش** | ۱۲-۲۰ روز |
| **Rollback** | Ansible/GitLab هنوز برای runtime workloads باربر نیستند |

---

## فاز ۵ — آماده‌سازی سیستم‌عامل

| | |
|---|---|
| **هدف** | خط پایه Oracle Linux 9 و Ubuntu 24.04 LTS: repo config، sysctl، security baseline، SSSD/realmd، TLS trust، agentهای monitoring/logging |
| **پیش‌نیازها** | اتوماسیون فاز ۴ + inventories؛ repoهای پکیج داخلی پیکربندی شده |
| **تحویل‌ها** | `operating-systems/oracle-linux/*`، `operating-systems/ubuntu/*`: repo config، sysctl، security baseline، SSSD/realmd، TLS trust، agentهای monitoring/logging |
| **معیارهای پذیرش** | هاست provision شده از bare metal تا node hardened، domain-joined، monitored با یک run Ansible؛ `ansible all -m setup` idempotent (۰ changed در run دوم)؛ SSBD login کار می‌کند؛ حساب break-glass local کار می‌کند؛ shipping `auditd`/`journald` verified؛ install پکیج با اینترنت disabled کار می‌کند |
| **ریسک‌ها** | SELinux/AppArmor مسدودکننده container runtime؛ mismatch پروفایل AppArmor روی Ubuntu؛ per-distro documented |
| **تلاش** | ۱۲-۲۰ روز |
| **Rollback** | Re-run playbook؛ هاست‌ها از PXE/ISO + Ansible rebuildable |

---

## فاز ۶ — زیرساخت ذخیره‌سازی

| | |
|---|---|
| **هدف** | استقرار Ceph (مسیر cephadm)، Rook-Ceph (مسیر in-cluster)، CRUSH map، worksheet ظرفیت، monitoring، رویه‌های recovery |
| **پیش‌نیازها** | OS سخت‌شده فاز ۵ روی نودهای storage؛ VLAN ذخیره‌سازی؛ repoهای فاز ۲ برای پکیج/ایمیج Ceph |
| **تحویل‌ها** | `storage/ceph/*` (مسیر cephadm)، `storage/rook-ceph/*` (مسیر in-cluster)، CRUSH map، worksheet ظرفیت، monitoring، رویه‌های recovery |
| **معیارهای پذیرش** | `ceph -s` HEALTH_OK گزارش می‌دهد؛ quorum ۳ MON از دست دادن یک MON survive می‌کند؛ شکست OSD rebalance خودکار trigger می‌کند؛ RBD + CephFS + RGW (در صورت انتخاب) functional test pass می‌کند؛ exporter Ceph به Prometheus feed می‌کند؛ worksheet ظرفیت با اعداد واقعی مرور شده |
| **ریسک‌ها** | RK-۰۴ collapse دامنه شکست → mapping CRUSH host/root؛ test pool تک‌میزبان production نیست |
| **تلاش** | ۱۵-۲۵ روز |
| **Rollback** | `ceph orch` decommission؛ وابستگی K8s هنوز نیست |

---

## فاز ۷ — استقرار کوبرنتیز

| | |
|---|---|
| **هدف** | استقرار کلاستر ک8س از طریق Kubespray با ایمیج‌های آفلاین |
| **پیش‌نیازها** | ذخیره‌سازی فاز ۶ (یا حداقل node prep)، اتوماسیون فاز ۴، ایمیج‌های فاز ۲ mirrored |
| **تحویل‌ها** | `kubespray/` inventories + group vars (version-pinned)، `kubernetes/control-plane/*`، config override ایمیج آفلاین |
| **معیارهای پذیرش** | `kubectl get nodes` ۳ control-plane Ready نشان می‌دهد؛ etcd ۳/۳ healthy؛ کنترل‌پلین node loss دسترسی API عبر VIP را قطع نمی‌کند؛ یک worker قابل حذف/إضافه توسط Kubespray است؛ هیچ `imagePullBackOff` با اینترنت disabled وجود ندارد؛ `kubectl get pods -A` همه Running/Completed |
| **ریسک‌ها** | RK-۰۵ drift متغیر Kubespray → pin release، نگه داشتن فایل `inventory/VERSION`، diff vars در upgrade |
| **تلاش** | ۱۲-۲۰ روز |
| **Rollback** | `kubespray reset` روی نود؛ rebuild کلاستر از inventory |

---

## فاز ۸ — سرویس‌های کلاستر

| | |
|---|---|
| **هدف** | Cilium CNI + Hubble، MetalLB IPAddressPool + L2Advertisement، NGINX Ingress + Gateway API، Rook-Ceph CSI + StorageClasses، ExternalDNS، cert-manager |
| **پیش‌نیازها** | کلاستر سالم فاز ۷ |
| **تحویل‌ها** | Cilium CNI + Hubble، MetalLB IPAddressPool + L2Advertisement، NGINX Ingress + Gateway API، Rook-Ceph CSI + StorageClasses، ExternalDNS، cert-manager |
| **معیارهای پذیرش** | Pod-to-pod و pod-to-service connectivity در کل نودها؛ NetworkPolicy enforce شده (test allowed و denied)؛ service `type: LoadBalancer` VIP می‌گیرد و reachable است؛ Ingress HTTP و TLS terminate به درستی route می‌کند؛ PVC bind و mount می‌شود، و online expand می‌کند؛ CSI snapshot و restore کار می‌کند |
| **ریسک‌ها** | MTU mismatch بین overlay و underlay → MTU اندازه‌گیری شده documented؛ issuance cert در offline fail می‌کند → internal CA پیکربندی شده |
| **تلاش** | ۱۵-۲۵ روز |
| **Rollback** | Helm uninstall به ازای هر کامپوننت؛ حذف StorageClass داده‌ها را نابود می‌کند → ابتدا backup |

---

## فاز ۹ — کلاستر مدیریت

| | |
|---|---|
| **هدف** | Rancher روی کلاستر ۳-node اختصاصی، ثبت کلاستر، Keycloak realm + OIDC clients، Argo CD با SSO، Velero روی هر دو کلاستر، داشبوردهای پلتفرم |
| **پیش‌نیازها** | فاز ۷ کامل؛ فاز ۳ هویت؛ فاز ۴ Vault |
| **تحویل‌ها** | Rancher روی کلاستر ۳-node اختصاصی، ثبت کلاستر، Keycloak realm + OIDC clients، Argo CD با SSO، Velero روی هر دو کلاستر، داشبوردهای پلتفرم |
| **معیارهای پذیرش** | Rancher کلاستر اپلیکیشن را register کرده و نودهای آن را می‌خواند؛ login Keycloak برای Rancher و Argo CD کار می‌کند؛ Argo CD یک test app را از GitLab sync می‌کند؛ بکاپ Velero کامل می‌شود و restore در namespace تازه succeed می‌کند؛ Rancher و Argo CD restart کلاستر مدیریت survive می‌کنند |
| **ریسک‌ها** | mismatch mapping claim/گروه OIDC → گروه‌ها به صراحت تست شده |
| **تلاش** | ۱۵-۲۵ روز |
| **Rollback** | Uninstall؛ کلاسترها به صورت مستقل در حال اجرا باقی می‌مانند |

---

## فاز ۱۰ — رازها و امنیت

| | |
|---|---|
| **هدف** | policies Vault، auth methods، PKI، یکپارچه‌سازی Kubernetes؛ `security/` constraints Gatekeeper، policies Kyverno، Pod Security Standards، ruleset Falco، pipeline Trivy/Cosign، baseline scripts CIS |
| **پیش‌نیازها** | فاز ۴ Vault؛ فاز ۹ Argo CD؛ فاز ۷ کلاسترها |
| **تحویل‌ها** | `secrets-management/vault/*` policies، auth methods، PKI، یکپارچه‌سازی Kubernetes؛ `security/` constraints Gatekeeper، policies Kyverno، Pod Security Standards، ruleset Falco، pipeline Trivy/Cosign، baseline scripts CIS |
| **معیارهای پذیرش** | App راز را از طریق روش تحویل انتخاب شده می‌خواند و در Git نیست؛ rotation مقدار تحویل‌شده را در بازه documented به‌روزرسانی می‌کند؛ Gatekeeper یک pod privileged را در audit mode بعد در enforce mode reject می‌کند؛ Falco یک test alert raise می‌کند؛ Trivy یک image CRITICAL را در pipeline block می‌کند؛ verification Cosign برای ایمیج‌های امضا شده pass و برای unsigned fail می‌کند |
| **ریسک‌ها** | over-blocking policy → deploy در audit mode اول، review violations، بعد enforce |
| **تلاش** | ۱۵-۲۵ روز |
| **Rollback** | Gatekeeper `failurePolicy: Ignore` / uninstall؛ policies Vault بدون restart قابل تنظیم |

---

## فاز ۱۱ — مانیتورینگ و لاگینگ

| | |
|---|---|
| **هدف** | `monitoring/` استک Prometheus Operator، маршруت‌های Alertmanager، داشبوردهای Grafana، recording rules، Thanos (در صورت انتخاب)؛ `logging/` Fluent Bit، Loki/OpenSearch، retention policy، قواعد redaction |
| **پیش‌نیازها** | کلاسترهای فاز ۷/۸؛ کلاستر مدیریت فاز ۹ |
| **تحویل‌ها** | `monitoring/` استک Prometheus Operator، مسیرهای Alertmanager، داشبوردهای Grafana، recording rules، Thanos (در صورت انتخاب)؛ `logging/` Fluent Bit، Loki/OpenSearch، retention policy، قواعد redaction |
| **معیارهای پذیرش** | Prometheus targetهای node، kube، etcd، CNI، CSI، Ceph، Argo CD، Vault، GitLab، Harbor، GPU را scrape می‌کند؛ یک test alert end-to-end به receiver fire می‌شود؛ یک pod's logs در ۵ دقیقه searchable است؛ یک رشته secret به طور عمدی تزریق شده در backend لاگ یافت نمی‌شود؛ dashboards برای هر domain render می‌شوند |
| **ریسک‌ها** | RK-۱۰ volume لاگ → sampling، retention، cardinality limits |
| **تلاش** | ۱۲-۲۰ روز |
| **Rollback** | Scale down/disable؛ تأثیری روی data plane ندارد |

---

## فاز ۱۲ — زیرساخت GPU و AI

| | |
|---|---|
| **هدف** | `gpu-ai/*` درایورها، GPU Operator، device plugin، scheduling labels/taints، matrix اشتراک‌گذاری، استقرار inference، رویه mirror مدل، داشبوردهای monitoring |
| **پیش‌نیازها** | کلاسترهای فاز ۷/۸؛ فاز ۲ آرتیفکت‌های GPU mirrored؛ سخت‌افزار GPU node آماده |
| **تحویل‌ها** | `gpu-ai/*` درایورها، GPU Operator، device plugin، scheduling labels/taints، matrix اشتراک‌گذاری، استقرار inference، رویه mirror مدل، داشبوردهای monitoring |
| **معیارهای پذیرش** | `kubectl get nodes -l nvidia.com/gpu.present=true` Ready نشان می‌دهد؛ یک GPU pod `nvidia-smi` اجرا کرده و GPU صحیح را می‌بیند؛ پارتیشن MIG به عنوان resource جداگانه visible است و حافظه hard-isolated است (test: allocate فراتر از profile و مشاهده failure)؛ time-slicing pod GPU را share می‌کند بدون isolate حافظه (documented)؛ vLLM یک مدل mirrored را serve کرده و completion برمی‌گرداند؛ متریک‌های DCGM در Prometheus visible هستند؛ دو tenant همزمان تحت MIG یکدیگر را OOM نمی‌کنند |
| **ریسک‌ها** | RK-۰۶ mismatch نسخه → استفاده از ماتریس driver/toolkit/operator؛ upgrade operator به طور کوتاه GPU pods را disrupt می‌کند → پنجره drain |
| **تلاش** | ۱۵-۲۵ روز |
| **Rollback** | taint برداشته شود، node drain شود، operator به نسخه پین شده roll back شود |

---

## فاز ۱۳ — GitOps و CI/CD

| | |
|---|---|
| **هدف** | `automation/gitlab-ci/` pipeline کامل با تمام ۱۴ مرحله، protected branches، approval gates، App-of-apps، job تشخیص drift |
| **پیش‌نیازها** | فاز ۹ Argo CD؛ فاز ۱۰ policies؛ فاز ۱۱ dashboards |
| **تحویل‌ها** | `automation/gitlab-ci/` pipeline کامل با تمام ۱۴ مرحله، protected branches، approval gates، App-of-apps، job تشخیص drift |
| **معیارهای پذیرش** | یک manifest به طور عمدی broken در مرحله ۵ reject می‌شود؛ یک secret در commit در مرحله ۷ reject می‌شود؛ job production نیازمند ۲ approval و از protected tag اجرا می‌شود؛ drift job یک drift دستی واقعی را بدون auto-fix گزارش می‌دهد؛ health check post-deploy در صورت unhealthy بودن pod pipeline را fail می‌کند |
| **ریسک‌ها** | over-blocking pipeline → bypass per-stage documented و audited |
| **تلاش** | ۱۲-۲۰ روز |
| **Rollback** | Revert به کانفیگ pipeline قبلی؛ Argo CD self-heal تحت تأثیر نیست |

---

## فاز ۱۴ — چرخه حیات و بازیابی

| | |
|---|---|
| **هدف** | `lifecycle/upgrades/*` per component، `lifecycle/backup/*`، `lifecycle/disaster-recovery/*` runbooks، `troubleshooting/*` |
| **پیش‌نیازها** | فازهای ۷-۱۳ کامل |
| **تحویل‌ها** | `lifecycle/upgrades/*` per component، `lifecycle/backup/*`، `lifecycle/disaster-recovery/*` runbooks، `troubleshooting/*` |
| **معیارهای پذیرش** | یک upgrade minor-version ک8س روی کپی staging کلاستر با هیچ data loss کامل می‌شود؛ یک full cluster restore از Velero به کلاستر جدید کار می‌کند؛ یک rebuild تک‌نود از Ansible + Kubespray unattended کامل می‌شود؛ یک complete-environment rebuild procedure در محیط offline بدون اینترنت اجرا شده و acceptance tests pass می‌کند؛ RTO/RPO بر اساس اهداف اعلام شده measured شده |
| **ریسک‌ها** | مسیر upgrade برای برخی کامپوننت‌ها one-way ممکن است → مراحل irreversible در هر doc upgrade پرچم‌گذاری شده |
| **تلاش** | ۲۰-۳۰ روز |
| **Rollback** | Per-component؛ برخی upgradeها irreversible و به این صورت documented |

---

## فاز ۱۵ — پذیرش و تحویل

| | |
|---|---|
| **هدف** | `tests/acceptance/` suite تست اجرا شده با evidence، `requirements/acceptance-criteria.md`، runbooks منتشر شده، محدودیت‌های شناخته شده ثبت شده، ماتریس ownership |
| **پیش‌نیازها** | فاز ۱۴ کامل |
| **تحویل‌ها** | `tests/acceptance/` suite تست اجرا شده با evidence، `requirements/acceptance-criteria.md`، runbooks منتشر شده، محدودیت‌های شناخته شده ثبت شده، ماتریس ownership |
| **معیارهای پذیرش** | هر acceptance test در `requirements/acceptance-criteria.md` با evidence ثبت شده و verdict pass/fail اجرا شده؛ failures یا fixed شده یا به عنوان accepted risk با owner ثبت شده؛ handover walkthrough با تیم operations کامل شده |
| **ریسک‌ها** | ادعاهای untested → فقط تست‌های اجرا شده passed marques می‌شوند |
| **تلاش" | ۱۰-۱۸ روز |
| **Rollback** | n/a (مستندات و sign-off) |

---

## خلاصه وابستگی‌ها

```text
1 ─► 2 ─► 3 ─► 4 ─► 5 ─► 6 ─► 7 ─► 8 ─► 9 ─► 10 ─► 11 ─► 12
                    │        │        │    │      │      │
                    └────────┴────────┴────┴──────┴──────┴──► 13 ─► 14 ─► 15
```

فازهای ۱۱ و ۱۲ می‌توانند بعد از فاز ۹ به صورت موازی اجرا شوند.

---

## فازهای آینده (خارج از مسیر حیاتی)

| فاز | موضوع | وابستگی |
|---|---|---|
| ۱۶ | Multi-site / Multi-datacenter | فاز ۱۵ کامل |
| ۱۷ | Service Mesh adoption | فاز ۱۰، ۱۳ |
| ۱۸ | Advanced AI/ML platform | فاز ۱۲ |
| ۱۹ | Edge/Remote cluster management | فاز ۹، ۱۴ |

---

*Status: DRAFT | Owner: Platform Architecture | Last reviewed: 2026-11-23*