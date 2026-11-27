# راهنمای پیاده‌سازی استک کلود-بومی (فارسی)

به راهنمای پیاده‌سازی استک کلود-بومی خوش آمدید — یک راهنمای دو زبانه، Produktions-oriented برای استقرار و عملیات یک پلتفرم کلود-بومی در محیط‌های on-premises و air-gapped.

## شروع سریع

| نقش | شروع از اینجا |
|---|---|
| معماریست پلتفرم | [معماری مرجع](../architecture/00-overview.md) |
| مهندس DevOps | [نقشه راه پیاده‌سازی](../requirements/implementation-roadmap.md) |
| مهندس امنیت | [استانداردهای امنیت](../requirements/platform-standards.md) |
| مهندس ذخیره‌سازی | [استقرار Ceph](../storage/ceph/cephadm-deployment.md) |
| مهندس کوبرنتیز | [استقرار Kubespray](../kubespray/kubespray-deployment.md) |

## ساختار مستندات

| دایرکتوری | هدف |
|---|---|
| [architecture/](../architecture/) | معماری مرجع، توپولوژی، دامنه‌های شکست |
| [requirements/](../requirements/) | نیازمادها، نقشه راه، استانداردها، اعتبارسنجی، معیارهای پذیرش |
| [decisions/](../decisions/) | سوابق تصمیم معماری (ADR-0001..ADR-0027) |
| [compatibility/](../compatibility/) | ماتریس نسخه، محدودیت‌های سازگاری |
| [operating-systems/](../operating-systems/) | خط پایه Ubuntu 24.04 LTS، Oracle Linux 9 |
| [automation/](../automation/) | Ansible، GitLab CI، Terraform |
| [kubespray/](../kubespray/) | استقرار Kubespray، پشتیبانی چند نسخه |
| [kubernetes/](../kubernetes/) | CNI، CSI، Ingress، Add-onها، امنیت |
| [storage/](../storage/) | Ceph، Rook-Ceph، جایگزین‌ها |
| [management-cluster/](../management-cluster/) | Rancher، Argo CD، Keycloak |
| [identity/](../identity/) | Keycloak، SSSD/realmd، AD/LDAP |
| [secrets-management/](../secrets-management/) | Vault، PKI، یکپارچه‌سازی Kubernetes |
| [monitoring/](../monitoring/) | Prometheus، Grafana، Loki، Alertmanager |
| [logging/](../logging/) | خط لوله لاگ، Fluent Bit، Loki |
| [security/](../security/) | Gatekeeper، Kyverno، Falco، PSS |
| [service-mesh/](../service-mesh/) | ارزیابی و معیارهای採用 |
| [offline-artifacts/](../offline-artifacts/) | ماتریس آرتیفکت air-gap، staging |
| [lifecycle/](../lifecycle/) | ارتقاها، بکاپ، بازیابی disastro |
| [troubleshooting/](../troubleshooting/) | رن‌بوک‌های مبتنی بر علائم |
| scripts/ | بازخوانی نسخه، ژنراتور ماتریس‌ها، ژنراتور ADR |
| tests/ | خودآزمایی مخزن، تست‌های پذیرش |

## مستندات دو زبانه

| زبان | مکان |
|---|---|
| English | `docs/en/` |
| فارسی | `docs/fa/` (این دایرکتوری) |

## لینک‌های سریع

- [قالب راهنمای کامپوننت](../requirements/component-guide-template.md)
- [نقشه راه پیاده‌سازی](../requirements/implementation-roadmap.md)
- [ماتریس نسخه و سازگاری](../compatibility/version-matrix.md)
- [استانداردهای پلتفرم](../requirements/platform-standards.md)
- [معیارهای پذیرش](../requirements/acceptance-criteria.md)
- [استراتژی اعتبارسنجی](../requirements/validation-strategy.md)

## نشان‌های وضعیت

| نشان | معنی |
|---|---|
| **VERIFIED** | در تاریخ ثبت شده در برابر منبع رسمی بررسی شده |
| **UNVERIFIED** | هنوز تأیید نشده؛ رویه تأیید ثبت شده |
| **PROVISIONAL** | پیش‌فرض انتخابی در انتظار بازبینی؛ امن برای تغییر قبل از ساخت |

## مشارکت

برای قراردادهای ارتباط و سبک کار به [USER.md](../USER.md) مراجعه کنید.
برای قراردادهای ذخیرهاقعیت به [MEMORY.md](../MEMORY.md) مراجعه کنید.

## مجوز

این راهنما مستندات-به‌عنوان-کد است. برای شرایط به LICENSE مخزن مراجعه کنید.