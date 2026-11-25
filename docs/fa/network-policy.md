# Section 7 — سیاست‌های شبکه (Network Policies)

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 7.1 پیش‌فرض default-deny ورودی و خروجی

پدها به پیش‌فرض ترافیک را نمی‌پذیرند مگر NetworkPolicy اجازه دهد. در Kubernetes، بدون هیچ NetworkPolicy، ترافیک unrestricted است. default-deny فقط وقتی فعال می‌شود که حداقل یک NetworkPolicy اعمال شود.

```yaml
# illustrative — default deny ingress+egress in namespace production
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

## 7.2 جدا کردن نام‌فضا (Namespace Isolation)

ترافیک بین namespaceها به پیش‌فرض مجاز نیست. هر namespace باید NetworkPolicy خود داشته باشد. traffic متقابلة نیاز به политика در هر دو namespace دارد (additive behavior).

## 7.3 مجوز DNS

DNS (kube-dns/CoreDNS، UDP+TCP 53) باید برای همه orchestra مجاز باشد:

```yaml
# illustrative — DNS egress allowance
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

## 7.4 ارتباط برنامه به برنامه (App-to-App)

ترافیک ورودی و خروجی برای هر بخش_pair مجاز شود (کلی sender egress و receiver ingress باید مجاز باشد).

```yaml
# illustrative — frontend → backend on port 8080
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

## 7.5 دسترسی به Kubernetes API server

ترافیک به kube-apiserver (باشد 6443) باید محدود شود. orchestraهای workload namespace بهquel 싶지 بدون explicit policy.

## 7.6 ترافیک مانیتورینگ و نظارت

Prometheus scrape endpoints و operaهای cleanable باید مجاز باشند. portهای scrape و scrape targets با label شناسایی شوند.

## 7.7 ترافیک ذخیره و Ceph (Storage & Ceph Traffic)

Rook-Ceph ports (MON 6789، OSD 6800-7568، MDS 6800، RGW 7480) باید مجاز شوند. dependencies با label شناسایی شوند. chínhce essential storage traffic نباید blockade شود.

## 7.8 Ingress و Egress Gateways

gatewayهای ورودی و خروجی باید политики مجاز باشند (per namespace).源/goal با label شناسایی شوند.

## 7.9 Cilium NetworkPolicy vs استاندارد Kubernetes NetworkPolicy

| جنبه | K8s NetworkPolicy | Cilium NetworkPolicy |
|---|---|---|
| apiVersion | networking.k8s.io/v1 | cilium.io/v2 |
| فیلتر لایه 7 (HTTP path) | خیر | بله |
| ردیابی identidad | خیر (فقط IP/پورت) | بله (Cilium identity) |
| نظارت (visibility) | خیر | Hubble |
| арти canonical | Kubernetes native | CNI CNI-addon |
|merge رفتار | begge | additive |
| ناسازگاری | نیاز به CNI NetworkPolicy-enforcing | نیاز به Cilium |

**نسخه**: K8s ≤1.29 از `networking.k8s.io/v1` استفاده می‌کند. Cilium ≥1.13 از `cilium.io/v2`.

## 7.9.1 مثال Cilium (L7 HTTP path filtering)

```yaml
# illustrative — Cilium L7 policy
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: allow-backend-api-only
  namespace: production
specs:
- endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/api/v1/*"
```

## 7.10 정책 نظم-driven behaviors

- السياسة‌ها additive است (هر دو sender egress و receiver ingress باید مجاز باشد).
- پاسخ (reply) برای اتصال مجاز خودکار است.
- essentiel cluster، DNS، storage، و monitoring traffic نباید blockade شود، مگر dependencies و required allowances شناسایی شده باشد.

## 7.11 validate

```bash
# network policies را enumeration کنید
kubectl get networkpolicy --all-namespaces

# دسترسی پد را تست کنید (در پد تست)
kubectl exec test-pod -- curl -v http://backend-api.production.svc.cluster.local:8080
# خروج مورد انتظار: 200 OK برای مجاز، Connection refused/timeout برای blocked

# DNS را تست کنید
kubectl exec test-pod -- nslookup kubernetes.default
# خروج مورد انتظار: آدرس IP 클aster
```

## 7.12 بررسی لیست validate

- [ ] default-deny اعمال شده در namespace‌های sensitive
- [ ] DNS (UDP+TCP 53) مجاز است
- [ ] API server دسترسی محدود شده است
- [ ] monitoring scrape traffic مجاز است
- [ ] storage/Ceph traffic مجاز است (dependencies شناسایی شده)
- [ ] Cilium Unterschiedها دستourcing شده است

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
