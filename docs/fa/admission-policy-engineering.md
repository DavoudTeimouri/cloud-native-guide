# Section 4 — مهندسی سیاست اعتراش (Gatekeeper و Kyverno)

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## 4.1 مقایسه Gatekeeper و Kyverno

| جنبه | Gatekeeper (OPA) | Kyverno |
|---|---|---|
| زبان политика | Rega (OPA) | Kubernetes-native (YAML/JSON) |
| contour mutation | به صورت جداگانه (موتاتورهای مجزا) | الأصليين (mutate rules) |
| contour validation | Constraints + ConstraintTemplates | 정책 rules (validate) |
| تایید امضای تصویر | با اضافه-ons | الأصليين (verifyImages) |
| contour scaffold | پیچیده‌تر | ساده‌تر |
| مناسبت برای | محدودیت‌های ساختار orchestra و cluster | تایید امضای تصویر، 생성 پد، mutate |

**مهم**: هر politica را فقط در یکی از این دو ابزار اجرا کنید، مگر مسئولیت‌ها از هم مشخص شده باشد (مثلاً Kyverno برای تایید امضای تصویر و Gatekeeper برای محدودیت ساختار). اجرا همزمانِ intertwined برای یک قانون باعث تعارض در admission می‌شود.

## 4.2سیاست‌های نمایند (Representative Policies)

### 4.2.1 اجبار درخواست و محدودیت منابع (Requests and Limits)

**هدف امنیتی**: جلوگیری از استهلاك نامحدود منابع و DoS تولیدی از طریق orchestraها.

**مثال Gatekeeper** (Illustrative):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sResourceRequirements
metadata:
  name: require-requests-limits
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  parameters:
    containers:
      - image: "*"
        resources:
          requests:
            cpu: true
            memory: true
          limits:
            cpu: true
            memory: true
```

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-requests-and-limits
spec:
  validationFailureAction: enforce
  background: true
  rules:
  - name: require-resources
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "CPU/memory requests and limits are required."
      pattern:
        spec:
          containers:
          -:
            resources:
              requests:
                cpu: "?"
                memory: "?"
              limits:
                cpu: "?"
                memory: "?"
```

**audit vs enforce**: ابتدا در `audit` (validationFailureAction: audit) اجرا کنید تا violationها را مشاهده کنید بدون مسدود کردن orchestra؛ سپس به `enforce` تغییر دهید.

**Validate compliant/non-compliant**:
- compliant: orchestra با requests+limits → اجازه اجرا
- non-compliant: orchestra بدون limits → admission رد شده، پیام بالا نمایش داده می‌شود

**exception/namespace scoping**: namespace‌های system (kube-system) را با matched `exclude` خارج کنید.

**safe rollout/rollback**: audit → enforce مدتی، rollerback با تغییر `validationFailureAction: audit`.

### 4.2.2禁止 privileged containers

**هدف امنیتی**: جلوگیری از orchestra با دسترسی کامل host.

**مثال Gatekeeper** (Illustrative):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedContainers
metadata:
  name: disallow-privileged-containers
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
```

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: no-privileged-containers
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "Privileged containers are forbidden."
      pattern:
        spec:
          containers:
          -:
            securityContext:
              privileged: null
          initContainers:
          -:
            securityContext:
              privileged: null
```

### 4.2.3اجبار اجرای غیر-root

**هدف امنیتی**: اجرای orchestra با کاربر غیر-root برای کاهش خطر verfügability.

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-non-root
spec:
  validationFailureAction: enforce
  rules:
  - name: require-non-root
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "runAsNonRoot must be true."
      pattern:
        spec:
          securityContext:
            runAsNonRoot: true
          containers:
          -:
            securityContext:
              runAsNonRoot: true
```

### 4.2.4اجبار عدم-Elevation-ajaize

**هدف امنیتی**: جلوگیری از setuid/setgid برای اجرای کد با دسترسی بالاتر.

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privilege-escalation
spec:
  validationFailureAction: enforce
  rules:
  - name: no-privilege-escalation
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "allowPrivilegeEscalation must be false."
      pattern:
        spec:
          containers:
          -:
            securityContext:
              allowPrivilegeEscalation: false
```

### 4.2.5اجبار نام‌مرحله‌های تصویر مجاز (Approved image registries)

**هدف امنیتی**: کشیدن تصویر فقط از دoregistryهای داخلی معتبر (مثلاً harbor.internal).

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-approved-image-registries
spec:
  validationFailureAction: enforce
  rules:
  - name: require-approved-registries
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "Images must come from approved registries."
      pattern:
        spec:
          containers:
          -:
            image:
              globPattern: "harbor.internal/*"
          initContainers:
          -:
            image:
              globPattern: "harbor.internal/*"
```

### 4.2.6اجبار digest/image-tag السياسة

**هدف امنیتی**: orchestraها باید تصویر را با digest (`@sha256:...`) یا تگ specific استفاده کنند، نه `latest`.

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-digest-or-specific-tag
spec:
  validationFailureAction: enforce
  rules:
  - name: no-latest-tag
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "Image tags 'latest' are forbidden; use digest or explicit version."
      pattern:
        spec:
          containers:
          -:
            image:
              notGlobPattern: "*:latest"
```

### 4.2.7اجبار محدودیت host networking و host PID/IPC

**هدف امنیتی**: جلوگیری از orchestra دسترسی به network/name spaces host.

**مثال Gatekeeper** (Illustrative):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoHostNetwork
metadata:
  name: disallow-host-network
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
```

### 4.2.8اجبار محدودیت hostPath volumes

**هدف امنیتی**: جلوگیری از orchestra دسترسی به فایل سیستم host از طریق hostPath.

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-hostpath-volumes
spec:
  validationFailureAction: enforce
  rules:
  - name: restrict-hostpath
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "hostPath volumes require explicit justification."
      pattern:
        spec:
          volumes:
          -:
            hostPath:
              path:
                globPattern: "/allowed/*"
```

### 4.2.9اجبار تنظیمات security context

**هدف امنیتی**: orchestraها باید security context با کنترل‌های پایه داشته باشند.

**مثال Kyverno** (Illustrative): همان Section 3.2 — runAsNonRoot، allowPrivilegeEscalation:false، readOnlyRootFS، capabilities drop.

### 4.2.10اجبار برچسب‌های تایید و مالکیت metadata

**هدف امنیتی**: orchestraها باید مالک،环، و برچسب free tracking داشته باشند.

**مثال Kyverno** (Illustrative):

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-approved-labels
spec:
  validationFailureAction: enforce
  rules:
  - name: require-labels
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "Labels app, team, environment are required."
      pattern:
        metadata:
          labels:
            app: "?"
            team: "?"
            environment: "?"
```

## 4.3 اعتبارسنجی سیاست (Policy Validation)

```bash
# Tایید السياسية‌های Kyverno اجرا شده
kyverno policy list --all --report-validate

# Tایید constrainedهای Gatekeeper
kubectl get constraints --all-namespaces
kubectl get constrainttemplates --all-namespaces

# Tایید orchestra migrar compatible با política
kubectl apply -f non-compliant-pod.yaml --dry-run=server
# خروج مورد انتظار اگر non-compliant: خطای admission با پیام سیاست
```

## 4.4 rollout و rollback امن

1. politique را در `audit` اجرا کنید (validationFailureAction: audit).
2. violationها را در namespaceهای target بررسی کنید.
3. orchestraهای contradicting را اصلاح کنید.
4. `enforce` را برای namespaceهای ausgewählte فعال کنید.
5. کلaster را به Dancing‌ها monitors کنید.
6. rollback: `validationFailureAction: audit` برگردانید.

---

*سند تولید شده برای WISS 004-P11.4 — پایگاه امنیتی و اجبار سیاست کانتینر*
