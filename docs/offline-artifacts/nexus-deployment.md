# Nexus Deployment Guide (Offline Artifact Repository)

Nexus Repository Manager hosts OS packages (RPM/DEB), Helm charts (classic),
PyPI, npm, Go modules, and raw binary artifacts for offline/air-gapped
deployments. Harbor is used for OCI container images; Nexus handles everything
else.

See `docs/offline-artifacts/nexus-harbor-architecture.md` for the architecture
and role-assignment matrix. This guide covers the step-by-step deployment.

## Prerequisites

- A Linux host (Oracle Linux 9 or Ubuntu 24.04) dedicated to Nexus.
- At least 16 GB RAM and 100 GB disk for the Nexus volume.
- `kubectl` or direct host access depending on deployment mode.
- Internal DNS entry: `nexus.internal`.

## Deployment Mode A — Kubernetes (Recommended for In-Cluster)

### Step 1 — Create Namespace

```bash
kubectl create namespace nexus
```

### Step 2 — Deploy Nexus via Helm

```bash
helm repo add sonatype https://sonatype.github.io/helm3-nexus-chart/
helm repo update

helm install nexus sonatype/nexus \
  --namespace nexus \
  --create-namespace \
  --set persistence.enabled=true \
  --set persistence.size=100Gi \
  --set service.type=ClusterIP \
  --set resources.limits.memory=4Gi \
  --set resources.requests.memory=2Gi
```

### Step 3 — Expose Nexus (Ingress)

```yaml
# nexus-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nexus
  namespace: nexus
spec:
  ingressClassName: nginx
  rules:
  - host: nexus.internal
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nexus
            port:
              number: 8081
```

```bash
kubectl apply -f nexus-ingress.yaml
```

### Step 4 — Retrieve Admin Password

```bash
kubectl -n nexus get secret nexus-admin-credential -o jsonpath='{.data.password}' | base64 --decode; echo
```

Log in at `https://nexus.internal` with user `admin` and the retrieved password.

## Deployment Mode B — Standalone Host (For Offline Registry Host)

### Step 1 — Download Nexus

```bash
wget https://download.sonatype.com/nexus/3/latest-unix.tar.gz
tar -xvf latest-unix.tar.gz
```

### Step 2 — Create Nexus User

```bash
useradd -r -m -U -d /opt/nexus -s /bin/bash nexus
chown -R nexus:nexus /opt/nexus*
```

### Step 3 — Configure JVM Heap

Edit `/opt/nexus/bin/nexus.vmoptions`:

```
-Xms2g
-Xmx2g
-XX:MaxDirectMemorySize=2g
```

### Step 4 — Run Nexus

```bash
su - nexus -c "/opt/nexus/bin/nexus start"
```

Nexus starts on port 8081. Log in at `http://<host>:8081` with `admin` /
`admin123` (change immediately).

## Step 5 — Configure Repositories

Create the following repositories in the Nexus UI (or via REST API):

| Repository Name | Format | Type | Purpose |
|-----------------|--------|------|---------|
| `rpm-internal` | yum (hosted) | Hosted | Internal Oracle Linux / RHEL RPMs |
| `rpm-upstream-proxy` | yum (proxy) | Proxy | Upstream Oracle Linux / RHEL |
| `deb-internal` | apt (hosted) | Hosted | Internal Ubuntu DEBs |
| `deb-upstream-proxy` | apt (proxy) | Proxy | Upstream Ubuntu repos |
| `pypi-internal` | pypi (hosted) | Hosted | Internal Python packages |
| `pypi-upstream-proxy` | pypi (proxy) | Proxy | pypi.org |
| `npm-internal` | npm (hosted) | Hosted | Internal npm packages |
| `npm-upstream-proxy` | npm (proxy) | Proxy | registry.npmjs.org |
| `go-internal` | go (hosted) | Hosted | Internal Go modules |
| `go-upstream-proxy` | go (proxy) | Proxy | proxy.golang.org |
| `helm-classic` | helm (hosted) | Hosted | Classic Helm charts |
| `helm-oci` | helm (oci) | Hosted | OCI Helm charts (secondary to Harbor) |
| `raw-internal` | raw (hosted) | Hosted | Binaries, ISOs, Vendor files |

## Step 6 — Configure Repository Groups (Optional)

Create a group repository that combines hosted + proxy so clients point to one
URL:

- `rpm-all` group: `rpm-internal` + `rpm-upstream-proxy`
- `deb-all` group: `deb-internal` + `deb-upstream-proxy`
- `pypi-all` group: `pypi-internal` + `pypi-upstream-proxy`

## Step 7 — Configure Clients

### Yum/DNF (Oracle Linux / RHEL)

```ini
# /etc/yum.repos.d/nexus.repo
[nexus-rpm]
name=Nexus RPM Repository
baseurl=http://nexus.internal/repository/rpm-all/
enabled=1
gpgcheck=0
sslverify=0
```

### APT (Ubuntu)

```bash
echo "deb http://nexus.internal/repository/deb-all/ noble main restricted universe multiverse" | \
  tee /etc/apt/sources.list.d/nexus.list
apt-get update
```

### pip

```ini
# ~/.pip/pip.conf
[global]
index-url = http://nexus.internal/repository/pypi-all/simple
```

### npm

```bash
npm config set registry http://nexus.internal/repository/npm-all/
```

## Validation Commands

```bash
# Nexus is reachable
curl -k http://nexus.internal:8081/service/rest/v1/status

# Repository list
curl -k -u admin:<password> http://nexus.internal:8081/service/rest/v1/repositories

# Test RPM repo
curl -k http://nexus.internal/repository/rpm-all/ | head -5

# Test PyPI repo
curl -k http://nexus.internal/repository/pypi-all/simple/ | head -5
```

## Rollback

```bash
# Kubernetes mode
helm uninstall nexus -n nexus
kubectl delete namespace nexus

# Standalone mode
su - nexus -c "/opt/nexus/bin/nexus stop"
userdel -r nexus
rm -rf /opt/nexus /opt/sonatype-work
```
