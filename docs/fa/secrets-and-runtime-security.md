# Section 9 — رازها و امنیت در زمان اجرا (Secrets & Runtime Security)

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 9.1 محدودیت‌های Secret Kubernetes

- secretها در etcd ذخیره می‌شوند (base64 code نشده، رمزنگاری되지 به-default).
- secretها namespace-scoped هستند.
- کنترل دسترسی دقیق (fine-grained ACL) در secret وجود ندارد.
- volume mount secretها در فایل سیستم orchestra ظاهر می‌شوند.
- automountServiceAccountToken و secretها در وجود می‌توانند ل escalate کنند.
- image pull secrets جدا از secretهای کاربر هستند.
- Dockerfile/Image Layers می‌توانند secretها را در تاریخ/image layers به چرب کنند.

**Validate چک‌لیست**:
- [ ] secretها در etdc رمزنگاری نشده‌اند (معمولاً base64 فقط) → Vault/OpenBao استفاده شود
- [ ] секретها namespace-scoped هستند
- [ ] automountServiceAccountToken=false برای حساب‌هایunused

## 9.2 الگوهای یکپارچه‌سازی Vault/OpenBao

四 الگوها (تفاوت‌ها در جدول) :

| الگو | توضیح | نیاز به sidecar/CSI |
|---|---|---|
| **Sidecar Injector** | sidecar secretها را می‌فروchterد و از طریق env/volume project می‌کند | بله (sidecar) |
| **CSI Driver** | driver secretها را مستقیماً به عنوان volume فراهم می‌کند | بله (CSI driver) |
| **Init Container** | fetch یک‌بار قبل از شروع orchestra، به volume مشترک می‌نویسند | بله (init container) |
| **Direct API** | orchestra مستقیماً API broker را در startup می‌فروchterد (legacy) | خیر |

## 9.3 Rotating و کنترل دسترسی

سه استراتژی rotation:
- provider-managed TTL (dynamic secrets)
- periodic CronJob
- on-exposure (anned exposure)
- dynamic per-workload

کنترل دسترسی:
- یک credential برای هر orchestra (least privilege)
- RBAC روی Secretها
-�verlap غیرSHatter در cutover (rotation Never outage)

**Validate چک‌لیست**:
- [ ] هر credential مالک، TTL/rotation، و مسیر revocation شناخته شده باشد
- [ ] secretها در Git، manifest، log، یا image decision نیستند
- [ ] rotation non-breaking باشد (overlap old/new)

## 9.4 جلوگیری از secretها در Git، manifest، log، و container image

| vector | الگو جلوگیری |
|---|---|
| Git | pre-commit gitleaks، .gitignore |
| manifests | secretKeyRef فقط، مقادیر inline نشده |
| logs | application redaction secretها |
| container image | BuildKit secret args (بعد از استفاده حذف) |

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
