# Section 8 — امنیت زنجیرهٔ ارزشی (Supply Chain Security)

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 8.1 منابع تصویر معتبر (Trusted Image Sources)

- orchestraها باید تصویرها را فقط از registryهای داخلی معتبر (مثلاً harbor.internal) کش کنند.
- public registryها (docker.io، ghcr.io) باید از طریق External Upstream و Internal Proxy/Proxy-Cached (بخش TASK 004-P11.2)filtered شوند.
- allowlist تصویرهای مجاز تعریف شود.

## 8.2 اسکن تصویر با Trivy

Trivy یک اسکنر تصویر و dependency است که CVEs را شناسایی می‌کند. Trivy **فقط گزارش می‌دهد؛ سیاست اعمال نمی‌کند.**

```bash
# illustrative — scan an image for vulnerabilities
trivy image harbor.internal/platform/app:1.2.3
# خروج مورد انتظار: لیست CVEs با severity، یا خالی اگرfected نباشد

# 실패 scan (exit code 1 برای critical/high)
trivy image --exit-code 1 --severity CRITICAL,HIGH harbor.internal/platform/app:1.2.3
```

## 8.3 امضای تصویر با Cosign

Cosign برای امضا و تایید تصویر کंटینر استفاده می‌شود. امضای تصویر به orchestraها اجازه می‌دهد تایید کنند تصویر از منبع معتبر آمده و تغییر نیافته است.

```bash
# illustrative — sign an image
cosign sign --key <key-management-service> harbor.internal/platform/app:1.2.3

# illustrative — verify a signature
cosign verify --key <public-key> harbor.internal/platform/app@sha256:<digest>
```

## 8.4 تایید امضا و اجبار در admission (Signature Verification & Admission Enforcement)

تایید امضا باید در زمان admission (از طریق Kyverno/Gatekeeper + Cosign verifier) اعمال شود تا تصویرهای نامشخص اجرا نشوند.

- **اسکن (Scanning)**: Trivy CVE شناسایی می‌کند (گزارش، نه اجرا).
- **امضا (Signing)**: Cosign تصویر را امضا می‌کند (ثبات و منبع).
- **تایید امضا (Signature Verification)**: amضا در زمان اجرا بررسی می‌شود.
- **اجبار در admission (Admission Enforcement)**: Kyverno/Gatekeeper orchestraهای با تصویر نامشخص را رد می‌کند.

## 8.5 Pinning تصویر با digest (Image Digest Pinning)

orquestaها باید تصویر را با digest (`@sha256:<digest>`) یا تگ Version مشخص استفاده کنند، نه `latest`. digestها ناپذیر تغییر هستند.

## 8.6 SBOM و Provenance

- SBOM (Software Bill of Materials) برای هر تصویر تولید شود.
- provenance (منشأ و تاریخ ساخت) برای traceability ثبت شود.

## 8.7 Integrate CI/CD

- ترasmaهای CI/imageها باید در pipeline اسکن شوند.
- امضای تصویر در pipeline build انجام شود.
- تایید امضا در admission (Gatekeeper/Kyverno) اعمال شود.

## 8.8 Boundaries Nexus و Harbor

- **Nexus**: مخازن بسته (rpm/deb/pypi/npm/helm) و raw artifacts.
- **Harbor**: دoregistry OCI (تصاویر کانتینر)، تایید امضا، اسکن تصویر (Trivy)، Replication.
- هر کدام مسئولیت مجزایی دارند؛ همه قابلیت‌ها را در یک محصول pushing نکنید.

## 8.9 Difference: Scanning vs Signing vs Verification vs Enforcement

| کار | ابزار | هدف |
|---|---|---|
| Image Scanning | Trivy | شناسایی CVE (گزارش) |
| Image Signing | Cosign | ثبت منبع و ثبات تصویر |
| Signature Verification | Cosign | بررسی amضا قبل از اجرا |
| Admission Enforcement | Kyverno / Gatekeeper | رد orchestra با تصویر نامشخص |

**نکته**: اسکن یا امضا تنها سیاست اعمال نمی‌کند؛ besoin admission controller برای execução است.

## 8.10 عملیات در شبکه محدود/offline

- تصویرها باید از طریق Internal Repository/Registry Manager (بخش TASK 004-P11.2) کش شوند.
- orchestraها نباید مستقیماً به public registry دسترسی داشته باشند.

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
