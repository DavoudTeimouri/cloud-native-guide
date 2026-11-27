# Section 5 — اجرای سیاست و گذرance

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 5.1 پیشرفت امن (Safe Rollout Progression)

اجبار سیاست بلافاصله در کلaster producción بدون بررسی و برنامه-recommended نمی‌شود. پیشرفت زیر توصیه می‌شود:

1. **workflow موجود را بشناسید**: orchestraهای موجود، نام‌فضاها، 수준 دسترسی را القائمة کنید.
2. **violationهای فعلی را بشناسید**: السياسة را در `audit` اجرا کنید و violationها را محاسبه کنید.
3. **مالک سیاست و فرآیند exception را تعریف کنید**: هر política یک مالک، expiration، و فرآیند exception داشته باشد.
4. **سیاست‌ها را در audit/background اجرا کنید**: validationFailureAction: audit (Kyverno) یا dry-run (Gatekeeper).
5. **violationها را بررسی و orchestraها را اصلاح کنید**.
6. **اجبار را تدریجی فعال کنید**: enforce برای namespaceهای ausgewählte.
7. **admission failures را مانیتور کنید**.
8. **rollback و بازیابی راvalidate کنید**.

## 5.2 exceptionها و namespace استثناء

- namespace‌های `kube-system`، `kube-public` معمولاً exception دارند.
- exception باید در registry exception کلaster ثبت شود، expiration داشته باشد، و به namespace خاص محدود شود.
- exception دائمی مجاز نیست؛ بازبینی دوره‌ای مورد نیاز است.

## 5.3 نسخه‌بندی سیاست (Policy Versioning)

- politicaها باید در Git نگهداری شوند (GitOps).
- تغییر политиकी باید از طریق PR و code reviewPass شود.
- her politica یک نسخه، تاریخ ایجاد، و مالک داشته باشد.

## 5.4 بررسی تغییر (Change Review)

- تغییر السياسة باید در یک PR معادل بهologische change باشد.
- security architect یا مالک سیاست باید تایید کند.
- تاثیر orchestraهای موجود بررسی شود.

## 5.5 شواهد audit (Audit Evidence)

- violationهای admission باید no湖 logs ثبت شوند.
- deployment و enforce تاریخ‌ها ثبت شوند.
- exceptionها با理由 و مالک ثبت شوند.

## 5.6 تشخیص درِفت سیاست (Policy Drift Detection)

- Band scan دوره‌ای برای orchestraها که با politica contradت کنند.
- revelation違反ها باید هشدار دهند.

## 5.7 سازگاری به‌روزرسانی (Upgrade Compatibility)

- به‌روزرسانی Gatekeeper/Kyverno باید در staging ابتدا تست شود.
- APIهای السياسة (constrainttemplates، policies) باید با نسخه جدید سازگار باشند.

## 5.8 مالکیت عملیاتی (Operational Ownership)

- هر politika یک مالک محول شده باشد.
- مالک مسئولレビュー و excepción است.

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
