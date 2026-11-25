# Section 10 — Validate و عیب‌یابی امنیتی (Security Validation & Troubleshooting)

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 10.1 بررسی اجزای اعتراش (Admission Policy Validation)

```bash
# لیست سیاست‌های Kyverno اجرا شده
kyverno policy list --all --report-validate

# لیست constraintهای Gatekeeper
kubectl get constraints --all-namespaces
kubectl get constrainttemplates --all-namespaces

# simulate orchestra contravene policy
kubectl apply -f non-compliant-pod.yaml --dry-run=server
# خروج مورد انتظار اگر non-compliant: خطای admission با پیام السياسة
```

**Expected vs unexpected**:
- compliant orchestra → اجرا مجاز
- non-compliant orchestra → admission رد، پیام السياسة نمایش داده می‌شود

## 10.2 Validate RBAC

```bash
kubectl auth can-i create deployments --as alice -n default
# خروج مورد انتظار: yes / no
```

## 10.3 Validate NetworkPolicy

```bash
kubectl get networkpolicy --all-namespaces
kubectl exec test-pod -- curl -v http://backend-api.production.svc.cluster.local:8080
# خروج مورد انتظار: 200 OK برای مجاز، Connection refused/timeout برای blocked
```

## 10.4 Validate Pod Security Context

```bash
kubectl get pod <pod> -o jsonpath='{.spec.containers[].securityContext.runAsNonRoot}'
# خروج مورد انتظار: true

kubectl get pod <pod> -o jsonpath='{.spec.containers[].securityContext.allowPrivilegeEscalation}'
# خروج مورد انتظار: false
```

## 10.5 Validate Image Signature

```bash
cosign verify --key <public-key> harbor.internal/platform/app@sha256:<digest>
# خروج مورد erwart: verified با جزئیات amضا
```

## 10.6 Validate Secret Access

```bash
kubectl auth can-i get secrets --as system:serviceaccount:default:app-sa -n default
# خروج مورد انتظار: yes (فقط orchestra‌های مجاز)
```

## 10.7 Validate Falco Runtime Events

```bash
# Falco rule firing verification (일을 لسه ثبت نشده است)
# برای Falco: لاگ Falco و webhook destination را بررسی کنید
```

## 10.8 Troubleshooting Workflow

| مرحله | عمل |
|---|---|
| 1 | Symptom را ثبت کنید (مثلاً orchestra خطای forbidden، image pull Falied) |
| 2 | dashboard و alertهای مربوطه را بررسی کنید |
| 3 | دستورات validate اولیه را اجرا کنید (Sections 10.1-10.7) |
| 4 | لایه شکست را مشخص کنید (admission، network، secret، runtime) |
| 5 | root-cause را بررسی کنید |
| 6 | اصلاح امن را اعمال کنید |
| 7 | بازیابی راvalidate کنید |

### Examples troubleshooting

| Symptom | Reason | Fix |
|---|---|---|
| orchestra خطای forbidden اجرا نمی‌شود | PSS restricted یا politika admission | security context را مطابق پایگاه اصلاح کنید |
| image pull Falied | image registry مجاز نیست یا secret ImagePullMissing | image registry را به allowed list اضافه کنید، imagePullSecret تنظیم کنید |
| Falco Falied | Falco agent اجرا نمی‌شود | Falco deployment را بررسی کنید |
| secret access denied | RBACServiceAccount دسترسی ندارد | Role/RoleBinding را اصلاح کنید |

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
