# Rancher HA Installation

[Previous step](../../kubespray/kubespray-deployment.md) | [Next step](../../network-matrix/external-load-balancer.md)

## A. Purpose and architecture

Rancher HA provides high availability for the Rancher server across three control-plane nodes. The deployment uses an external PostgreSQL database, embedded ETCD (on each control-plane node), and a load balancer for frontend access.

```text
  admin workstation
        |
  Rancher VIP (DNS + HAProxy)
        |
  3 x Rancher control-plane nodes
    ETCD embedded (multi-node cluster)
    PostgreSQL external (dedicated RDS instance)
    Rancher server pods (replicated x3)
  Management Cluster (3 control-plane + 3 infra workers)
```

## B. Deployment model

**HA requirement**: Rancher HA requires a minimum of 3 control-plane nodes. Each node runs the Rancher server pod and participates in the embedded ETCD cluster. An external PostgreSQL database is required for the Rancher system catalog.

Node count, vCPU, RAM and disk are inputs, not constants: the site generates `hosts-mgmt.ini` from the management worker count. Three control-plane nodes is the minimum for HA; one is acceptable for a lab and gives no rollout headroom for the Rancher upgrade itself.

The management cluster is built with Kubespray, like every other cluster, so it is reproducible from the same inventory and the same OS baseline.

## C. Prerequisites

| Component | Requirement |
|---|---|
| Kubernetes | v1.25+ with three control-plane nodes |
| ETCD | Embedded, multi-node cluster (3 nodes minimum) |
| PostgreSQL | External database, version 12+ |
| Load balancer | DNS + HAProxy or cloud LB, TLS termination |
| OS | Ubuntu 22.04 / Rocky Linux 9 on all nodes |
| Ports | 443 (TCP), 80 (TCP), 5432 (TCP), 2379-2380 (ETCD) |

## D. Server installation (Kubespray HA)

Build the management cluster with Kubespray configured for three control-plane nodes.

```bash
# Clone Kubespray and checkout the release
git clone https://github.com/kubernetes-sigs/kubespray.git
cd kubespray
git checkout release-2.26

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Generate inventory from existing or create new
ansible-inventory -i inventory/hosts -y > inventory.json

# Scale to 3 control-plane nodes
# Edit inventory to set count of etcd and control-plane nodes to 3
ansible-playbook -i inventory/hosts.yml site.yml --become --become-user root
```

After Kubespray completes, verify three control-plane nodes are ready:

```bash
kubectl get nodes -A | grep -E "control-plane|etcd"
```

## E. External PostgreSQL database setup

Rancher HA requires an external PostgreSQL database. Do not use the embedded database.

### 1. Provision RDS or self-hosted PostgreSQL

```bash
# Example: self-hosted PostgreSQL on the management cluster
kubectl create namespace cattle-system

# Create a PostgreSQL deployment with external access
cat > postgres.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: postgres-external
  namespace: cattle-system
spec:
  selector:
    app: postgres
  ports:
    - protocol: TCP
      port: 5432
      targetPort: 5432
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: cattle-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15
          env:
            - name: POSTGRES_DB
              value: rancher
            - name: POSTGRES_USER
              value: rancher
            - name: POSTGRES_PASSWORD
              value: <strong-password>
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          persistentVolumeClaim:
            claimName: postgres-pvc
      volumes:
        - name: postgres-data
          emptyDir: {}
EOF

kubectl apply -f postgres.yaml
```

### 2. Create the Rancher system database

```bash
# Connect and create the database
psql "postgresql://rancher:<password>@<postgres-host>:5432/rancher" -c \
  "CREATE SCHEMA IF NOT EXISTS cattle;"
```

### 3. Verify connectivity

```bash
PGPASSWORD=<password> psql -h <postgres-host> -U rancher -d rancher -c "SELECT 1;"
```

## F. TLS certificates

Rancher HA uses TLS certificates terminated at the load balancer. Generate certificates using cert-manager or provided scripts.

### 1. Generate certificates with cert-manager

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
  namespace: cattle-system
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySize: 4096
    solvers:
      - http01:
          ingressClassName: nginx
```

### 2. Create the TLS secret for Rancher

```bash
# Generate a signed certificate for rancher.internal
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout /etc/rancher/cert.key \
  -out /etc/rancher/cert.crt \
  -subj "/CN=rancher.internal"

# Create the Kubernetes secret
kubectl -n cattle-system create secret tls rancher-tls \
  --cert=/etc/rancher/cert.crt \
  --key=/etc/rancher/cert.key
```

### 3. Configure Rancher to use the TLS secret

```yaml
# values.yaml
tls:
  source: secret
  existingSecret: rancher-tls
```

### 4. Alternative: Terminate TLS at load balancer

Configure HAProxy or cloud load balancer to terminate TLS before forwarding to Rancher nodes. The internal Rancher communication uses self-signed certificates signed by the embedded ETCD cluster.

## G. Load balancer configuration

### 1. DNS setup

```dns
; DNS records for Rancher HA
$ORIGIN internal.
rancher    IN  A     <lb-node-1-ip>
           IN  A     <lb-node-2-ip>
           IN  A     <lb-node-3-ip>
_rancher   IN  SRV   0 0 443 rancher.internal.
```

### 2. HAProxy configuration

```haproxy
# /etc/haproxy/haproxy.cfg
global
  log /dev/log local0
  log /dev/log local1 notice
  maxconn 2000

defaults
  mode http
  option dontlognull
  timeout connect 5000ms
  timeout client 50000ms
  timeout server 50000ms

frontend http_front
  bind *:80
  redirect scheme https if !{ ssl_f }

frontend https_front
  bind *:443 ssl crt /etc/rancher/cert.pem
  option forwardfor
  default_backend rancher_backend

backend rancher_backend
  mode http
  balance roundrobin
  option httpchk HEAD /v3/health HTTP/1.1\r\nHost: rancher.internal
  http-check expect status 200
  server rancher1 rancher.internal:443 ssl verify none
  server rancher2 rancher.internal:443 ssl verify none
  server rancher3 rancher.internal:443 ssl verify none
```

### 3. Cloud load balancer (AWS ALB/NLB)

Configure TLS listener and target group pointing to the three Rancher control-plane nodes. Enable health check on `/v3/health`.

## H. Rancher HA Helm installation

Add the Rancher chart repository and install with HA values.

```bash
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm repo update
```

```bash
cat > values-ha.yaml << 'EOF'
hostname: rancher.internal
replicas: 3
ingress:
  enabled: true
  ingressClassName: nginx
  tls:
    source: secret
    existingSecret: rancher-tls
privateRegistry: harbor.internal
rancherImage: harbor.internal/platform/rancher/rancher
systemDefaultRegistry: harbor.internal
useBundledSystemChart: true
bootstrapPassword: ""            # from External Secrets, not inline
extraEnv:
  - name: CATTLE_SYSTEM_DB_TYPE
    value: "postgresql"
  - name: CATTLE_SYSTEM_DB_URL
    value: "postgresql://rancher:<password>@<postgres-host>:5432/rancher?sslmode=require"
  - name: CATTLE_ETCD_SERVERS
    value: "https://etcd-1.internal:2379,https://etcd-2.internal:2379,https://etcd-3.internal:2379"
EOF
```

```bash
helm install rancher rancher-stable/rancher \
  --namespace cattle-system --create-namespace \
  --values values-ha.yaml
```

## I. Validation

### 1. Verify Rancher pods are running

```bash
kubectl -n cattle-system get pods
```

Expected: 3 Rancher server pods, all in `Running` state.

### 2. Verify ETCD cluster health

```bash
# Check ETCD member status on each node
for node in etcd-1 etcd-2 etcd-3; do
  ssh $node "etcdctl member list \
    -w endpoints=https://localhost:2379 \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert /etc/kubernetes/pki/etcd/peer.crt \
    --key /etc/kubernetes/pki/etcd/peer.key"
done
```

### 3. Test Rancher UI via load balancer

```bash
curl -k https://rancher.internal/v3/health
```

Expected: `{"status":"healthy"}`.

### 4. Verify database connectivity

```bash
kubectl -n cattle-system exec -it <rancher-pod> -- \
  pg_isready -h <postgres-host> -U rancher -d rancher
```

### 5. Verify load balancer traffic distribution

```bash
# Check each Rancher node receives requests
for i in 1 2 3; do
  curl -k -s https://rancher.internal/v3/health | head -1
done
```

### 6. Expected validation output

```
$ kubectl -n cattle-system get pods
NAME                              READY   STATUS    RESTARTS   AGE
rancher-7d8f9b6c9-x8mlp           2/2     Running   0          10m
rancher-7d8f9b6c9-pd9jl           2/2     Running   0          10m
rancher-7d8f9b6c9-q9bhm           2/2     Running   0          10m
$ curl -k https://rancher.internal/v3/health
{"status":"healthy"}
$ etcdctl member list -w table https://localhost:2379
ID     NAME      PEER URLs                         Client URLs
-----------------------------   -------------------------------
...   ...       ...                               ...
```

[Previous step](../../kubespray/kubespray-deployment.md) | [Next step](../../network-matrix/external-load-balancer.md)
