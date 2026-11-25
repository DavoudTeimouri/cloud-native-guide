# Section 6 — RBAC و امنیت هویت

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 6.1 طراحی RBAC با دسترسی کمترین (Least-Privilege RBAC)

- هر service account، کاربر، و گروه باید فقط دسترسی‌های لازم برای وظیفه خود داشته باشد.
- cluster-admin باید تنها برای条件 necessity استفاده شود.
- default service accountهای namespaceها automountOAuthToken=false باید داشته باشند.

## 6.2 Role versus ClusterRole

| نوع | دامنه | کاربرد |
|---|---|---|
| `Role` | یک namespace | دسترسی به منابع در یک namespace خاص |
| `ClusterRole` | کلaster | دسترسی به کلaster، منابع cluster-level، و همه namespaceها |

## 6.3 RoleBinding versus ClusterRoleBinding

| نوع | دامنه | کاربرد |
|---|---|---|
| `RoleBinding` | یک namespace | connects یک Role به کاربر/سرویس در همان namespace |
| `ClusterRoleBinding` | کلaster | connects یک ClusterRole به کاربر/سرویس در کلaster |

## 6.4 امنیت حساب سرویس (Service Account Security)

- automountOAuthToken=false برای accountهای استفاده‌نشده.
- حساب سرویس مجزا برای هر orchestra.
- توکن‌های service account کوتاه‌عمر یا از طریق projections.

## 6.5 هویت انسانی و اتوماسیون

-은 umani از طریق OIDC/Keycloak احراز هویت شوند.
- اتوماسیون (CI/CD) از توکن‌های کوتاه‌عمر یا سرویس حساب مجاز استفاده کند.
- در extend Git، credentials یا توکن‌ها ذخیره نشوند.

## 6.6 Integrations Rancher و OIDC/Keycloak

- Rancher از طریق OIDC/Keycloak احراز هویت می‌کند (فرض نشده است کهIntegrate شده باشد).
- مرزهای OIDC/Keycloak مشخص شود: چه کاربران به چه clusterها دسترسی دارند.
- claim Rancher به Accountها مدیریت شود.

## 6.7 tránh cluster-admin غیرضروری

- cluster-admin تنها برای break-glass یا worker amministrazione.
- دسترسی خیلی广 (wildcard `*`) در production مجاز نیست.

## 6.8 بررسی دسترسی و ثبت‌نام audit

```bash
# بررسی دسترسی کاربر
kubectl auth can-i create deployments --as alice -n default
# خروج مورد انتظار: yes / no

# بررسی دسترسی سرویس‌حساب
kubectl auth can-i get pods --as system:serviceaccount:default:app-sa -n default

# لیست Roleها و RoleBindingها
kubectl get role,rolebinding --all-namespaces
kubectl get clusterrole,clusterrolebinding --all-namespaces
```

## 6.9 شناسایی دسترسی‌های بیش‌ازحد (Excessive Permissions)

- به clusteradmin برשים داشته باشند بررسی شوند.
- wildcard `*` در verbs یا resources بررسی شود.
- حساب‌های silent، dormant ۹۰+ روز غیرفعال شوند.

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
