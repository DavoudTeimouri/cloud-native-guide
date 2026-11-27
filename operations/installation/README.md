# Operations Installation Guides

## OS Provisioning

### Purpose
Provision bare metal or VM hosts from bare metal to hardened, domain-joined, monitored nodes.

### Prerequisites
- Internal package repositories configured (Nexus)
- Internal CA certificate distributed
- Ansible control node ready
- Inventory prepared

### Execution
```bash
# From automation server
cd /opt/ansible
ansible-playbook -i inventories/production/inventory.ini playbooks/os-provisioning.yml

# Verify
ansible all -m setup | grep -E "ansible_distribution|ansible_distribution_version"
```

### Validation
- `ansible all -m ping` succeeds
- `ansible all -m setup` idempotent (0 changed on second run)
- SSSD login works
- Break-glass local account works
- `auditd`/journald shipping verified
- Package install works with no internet

---

## Kubernetes Install

### Purpose
Deploy Kubernetes cluster via Kubespray with offline images.

### Prerequisites
- Phase 6 storage (or node prep)
- Phase 4 automation ready
- Phase 2 images mirrored to Harbor
- Internal registry configured

### Execution
```bash
# Prepare inventory
cp inventories/production/inventory.ini /opt/kubespray/inventory/production/

# Configure group vars
cp group_vars/k8s_cluster/k8s-cluster.yml /opt/kubespray/inventory/production/group_vars/k8s_cluster/

# Run Kubespray
cd /opt/kubespray
ansible-playbook -i inventory/production/inventory.ini cluster.yml \
  -e container_manager=containerd \
  -e kube_network_plugin=cilium \
  -e kube_version=v1.36.5 \
  -e kubespray_version=v2.32.0 \
  -e container_manager=containerd \
  -e docker_registry=harbor.internal:5000 \
  -e kube_image_repo=harbor.internal/k8s

# Verify
kubectl get nodes
kubectl get pods -A
```

### Validation
- `kubectl get nodes` shows 3 control-plane Ready
- etcd 3/3 healthy
- Control-plane node loss does not interrupt API via VIP
- Worker can be removed/re-added by Kubespray
- No `imagePullBackOff` with internet disabled
- `kubectl get pods -A` all Running/Completed

---

## Ceph Deployment

### Purpose
Deploy Ceph storage via cephadm on dedicated hosts.

### Prerequisites
- Phase 5 hardened OS on storage nodes
- Storage VLAN configured
- Phase 2 repos for Ceph packages/images

### Execution
```bash
# Bootstrap first MON
cephadm bootstrap --mon-ip 10.40.0.11 \
  --registry-url harbor.internal:5000 \
  --registry-username admin \
  --registry-password $HARBOR_PASSWORD \
  --initial-dashboard-user admin \
  --initial-dashboard-password $CEPH_DASHBOARD_PASSWORD

# Add remaining MONs
ceph orch host add ceph-st-2 10.40.0.12
ceph orch host add ceph-st-3 10.40.0.13
ceph orch apply mon 3

# Add OSDs
ceph orch daemon add osd ceph-st-1:/dev/nvme0n1
ceph orch daemon add osd ceph-st-2:/dev/nvme0n1
ceph orch daemon add osd ceph-st-3:/dev/nvme0n1

# Enable services
ceph orch apply mgr 3
ceph orch apply mds cephfs 2
ceph orch apply rgw rgw 2 --placement="2 ceph-st-1 ceph-st-2 ceph-st-3"

# Create pools
ceph osd pool create replicapool 64 64 replicated
ceph osd pool application enable replicapool rbd
ceph osd pool create cephfs_metadata 32 32 replicated
ceph osd pool create cephfs_data 64 64 replicated
ceph fs new cephfs cephfs_metadata cephfs_data

# Enable RBD mirroring (optional)
ceph mgr module enable rbddashboard
```

### Validation
- `ceph -s` reports HEALTH_OK
- 3 MON quorum survives one MON loss
- OSD failure triggers automatic rebalance
- RBD + CephFS + RGW functional test passes
- Ceph exporter feeds Prometheus

---

## Management Cluster Setup

### Purpose
Deploy Rancher, Argo CD, Keycloak on dedicated management cluster.

### Prerequisites
- Phase 7 cluster healthy
- Phase 3 identity (Keycloak) deployed
- Phase 4 Vault deployed

### Execution
```bash
# Install Rancher
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm install rancher rancher-stable/rancher \
  --namespace cattle-system --create-namespace \
  --version 2.15.2 \
  --set hostname=rancher.internal \
  --set replicas=3 \
  --set bootstrapPassword=admin \
  --set ingress.tls.source=secret \
  --set tls=external

# Install Argo CD
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd \
  --namespace argocd --create-namespace \
  --version 10.10.5 \
  --set server.autoscale.enabled=true \
  --set server.autoscale.minReplicas=2 \
  --set server.autoscale.maxReplicas=5 \
  --set configs.params.server.insecure=false \
  --set configs.cm.url=https://argocd.internal \
  --set configs.cm.oidc.config="
    name: Keycloak
    issuer: https://keycloak.internal/realms/platform
    clientID: argocd
    clientSecret: \$ARGOCD_OIDC_CLIENT_SECRET
    requestedScopes: ['openid', 'profile', 'email', 'groups']
  "

# Configure Keycloak OIDC client for Argo CD
# Configure Keycloak realm for Rancher
```

### Validation
- Rancher registers Application Cluster and reads nodes
- Keycloak login works for Rancher and Argo CD
- Argo CD syncs test app from GitLab
- Velero backup completes and restore into fresh namespace succeeds
- Rancher and Argo CD survive Management Cluster restart
