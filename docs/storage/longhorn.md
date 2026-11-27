# Longhorn Deployment Guide

Longhorn is a lightweight, cloud-native distributed block storage system. Use it
as an alternative to Ceph/Rook for small-to-medium clusters that need replicated
block storage with a simple operator.

See `docs/storage/alternatives/storage-alternatives.md` for the comparison
matrix and adoption criteria.

## Prerequisites

- Kubernetes cluster is deployed and healthy (Phase 1 complete).
- Each node has at least one spare disk or partition for Longhorn data.
- Default storage class is not yet set to Longhorn (Ceph is the platform
  standard; Longhorn is optional).
- `kubectl` is configured to target the cluster.

## Step 1 — Add Helm Repository

```bash
helm repo add longhorn https://charts.longhorn.io
helm repo update
```

## Step 2 — Create Namespace

```bash
kubectl create namespace longhorn-system
```

## Step 3 — Deploy Longhorn

```bash
helm install longhorn longhorn/longhorn \
  --namespace longhorn-system \
  --create-namespace \
  --set persistence.defaultClassReplicaCount=2 \
  --set defaultSettings.defaultDataPath=/var/lib/longhorn \
  --set defaultSettings.backupTarget="" \
  --set defaultSettings.createDefaultDisk=true
```

Wait for Longhorn to be ready:

```bash
kubectl -n longhorn-system rollout status deployment/longhorn-manager --timeout=300s
kubectl -n longhorn-system rollout status daemonset/longhorn-driver-deployer --timeout=300s
kubectl -n longhorn-system rollout status daemonset/longhorn-instance-manager-e --timeout=300s
```

## Step 4 — Verify Longhorn Components

```bash
# All Longhorn pods running
kubectl -n longhorn-system get pods

# Longhorn storage class
kubectl get storageclass longhorn

# Longhorn manager status
kubectl -n longhorn-system get deployment longhorn-manager
```

## Step 5 — Access Longhorn UI (Optional)

```bash
kubectl -n longhorn-system port-forward svc/longhorn-frontend 8080:80 &
# Open http://localhost:8080 in a browser
```

## Step 6 — Create a StorageClass (Optional Override)

If you want Longhorn as the default storage class instead of Ceph:

```yaml
# longhorn-sc.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: driver.longhorn.io
parameters:
  numberOfReplicas: "2"
  staleReplicaTimeout: "28800"
  fromBackup: ""
  fsType: "ext4"
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

```bash
kubectl apply -f longhorn-sc.yaml
```

## Step 7 — Validate Volume Provisioning

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-test-pvc
  namespace: default
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
  storageClassName: longhorn
EOF

kubectl get pvc longhorn-test-pvc
# Should show Bound within 30-60 seconds
```

## Validation Commands

```bash
# Longhorn system health
kubectl -n longhorn-system get pods

# Storage class exists
kubectl get storageclass longhorn

# Volume created successfully
kubectl get pvc longhorn-test-pvc

# Longhorn node disk is healthy
kubectl -n longhorn-system get nodes -o wide | grep longhorn
```

## Rollback

```bash
kubectl delete pvc longhorn-test-pvc -n default
helm uninstall longhorn -n longhorn-system
kubectl delete namespace longhorn-system
```

> **Warning:** Longhorn and Ceph/Rook can coexist but having two distributed
> storage systems increases operational complexity. Choose one as the default
> storage class. Ceph remains the platform standard (ADR-0008).
