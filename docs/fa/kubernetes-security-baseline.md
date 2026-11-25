# Section 3 — پایگاه امنیتی оркеسترا کانتینر

*مثالی است — پیکربندی‌های production-confirmed نیست. نشانه‌گذاری شدهIllustrative است. هیچ پیکربندی از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 3.1 بررسی اجزای پایگاه

این بخش پایگاه امنیتی orchestra را برای همه namespaceهای برنامه تعریف می‌کند. کنترل‌های وابسته به زیرساخت پایه را می‌پوشانند؛ کنترل‌های پایه برای هیچ نوع orchestraなければ-relax نشود.

**Classificazione**: 적용runtime — Pod Security Standard `restricted` + runtime (نحوه kubelet، پروفایل Seccomp، capacità drop، نوع پروفایل seccomp).

**Lایه‌های اجرا**:
- Admission-time: Pod Security Standard `restricted` (वेブ 훅 بر اساس برچسب namespace) یا کنترل‌های admission تکمیلی (Kyverno، Gatekeeper).
- Runtime: پیکربندی kubelet، پروفایل Seccomp،落ち کردن capacidad، نوع پروفایل seccomp.

> **نکته**: برچسب `pod-security.kubernetes.io/enforce` namespace تنها یک نشانه audit است. برای اجرا نیاز به وب훅 admission فعال است. نام‌فضای برچسب‌گذاری شده بدون admission فعال، پد را فقط با هشدار اجرا می‌کند.

## 3.2 کنترل‌های اجباری پایگاه

| کنترل | مقدار/شرایط | لایه اجرا | نکات |
|---|---|---|---|
| `runAsNonRoot` | `true` | Admission-time / Runtime | در security context تنظیم شود; runtime پدهای بدون آن را رد می‌کند. |
| `runAsUser` | `65532` (nobody) یا UID توزیع | Admission-time / Runtime | UID صریح تنظیم شود؛ default باقی نماند. |
| `runAsGroup` | `65532` (nobody) یا GID توزیع | Admission-time / Runtime | Context گروه تکمیلی. |
| `allowPrivilegeEscalation` | `false` | Admission-time / Runtime | représcale setuid/setgid غیرفعال. |
| `readOnlyRootFilesystem` | `true` | Admission-time / Runtime | تغییر در runtime را prevents می‌کند. |
| `capabilities.drop` | `["ALL"]` | Admission-time / Runtime | همه capacity drop شود؛ `add` تنها برای نیاز خاص (مثلاً `NET_RAW` برای CNI) با justification. |
| `seccompProfile.type` | `RuntimeDefault` | Admission-time / Runtime | پروفایل پیش‌فرض runtime (Docker/containerd). |
| `hostNetwork` | `false` | Admission-time | در پایگاه forbidden است؛ `true` نیاز به exception صریح دارد. |
| `hostPID` | `false` | Admission-time | در پایگاه forbidden است. |
| `hostIPC` | `false` | Admission-time | در پایگاه forbidden است. |
| `hostPath` | محدود | Admission-time | فقط مسیرهای مجاز با exception. |
| `hostPort` | محدود | Admission-time | فقط پورت‌های مجاز با exception. |
| `imagePullPolicy` | `IfNotPresent` یا `Always` | Admission-time | از `Never` tránh شود. |
| `serviceAccountTokenAutomount` | `false` | Admission-time | sauf اگر نیاز صریح باشد. |

## 3.3 excepcions و الزامات عملیاتی

exceptionها فقط برای orchestraهای legitim (مثلاً CNI که NET_RAW نیاز دارد، DB که hostPath برای حجم lokal نیاز دارد) قابل قبول است. exception باید:
- در registry exception کلaster ثبت شود
- با expiration تاریخ داشته باشد
- به namespace خاص محدود شود

## 3.4 مثال‌های orchestra

مثال orchestra يتوافق با پایگاه (رضایت):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: compliant-workload
spec:
  serviceAccountName: default
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    fsGroup: 65532
  containers:
  - name: app
    image: harbor.internal/platform/app@sha256:{{placeholder}}
    imagePullPolicy: IfNotPresent
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
      seccompProfile:
        type: RuntimeDefault
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

## 3.5 دستورات validate و نتیجه مورد انتظار

```bash
# Tایید برچسب PSS namespace
kubectl get ns default -o jsonpath='{.metadata.pod-security.kubernetes.io/enforce}'
# خروج مورد انتظار: restricted

# Tایید orchestra بدون privileged container
kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.spec.containers[].securityContext.privileged == true) | .metadata.name'
# خروج مورد aspettato: خالی (هیچ پد privilegi)

# Tایید seccomp profile
kubectl get pod compliant-workload -o jsonpath='{.spec.containers[].securityContext.seccompProfile.type}'
# خروج مورد انتظار: RuntimeDefault
```

## 3.6 عیب‌یابی و اصلاح

| علامت | دلیل محتمل | اصلاح |
|---|---|---|
| پد با خطای forbidden اجرا نمی‌شود | PSS restricted فعال و orchestra grading ندارد | security context را مطابق پایگاه اصلاح کنید |
| container با readOnlyRootFilesystem écrit نمی‌تواند | فایلシستم فقط خواندنی | حجم(emptyDir) برای نوشتن موقت اضافه کنید |
| container با CAP_NET_RAW خطا می‌دهد | capacity drop شده است | justified exception با `add: ["NET_RAW"]` |

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
