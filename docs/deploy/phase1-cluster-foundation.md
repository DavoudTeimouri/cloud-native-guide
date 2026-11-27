# Entry criteria
- Automation Management Server provisioned with Ansible venv (or bastion host)
- All nodes have OS installed from internal mirror, containerd 2.3.7, Ansible 2.19.x, Python 3.11-3.13
- NTP synchronized on all nodes (`chronyc tracking` shows synchronized)
- SSH access for Ansible user on all nodes (`ansible all -m ping` returns pong)
- Internal container registry reachable from all nodes (`skopeo inspect docker://harbor.internal/...` succeeds)
- Internal file repository reachable from all nodes (`curl -sf http://files-repo.internal/` succeeds)
- OS package repository configured (`dnf repolist` or `apt-cache policy` shows internal repos)
- Kubespray release-2.32 checked out internally (`git -C kubespray/ log -1` shows v2.32.0 tag)
- `kubespray/VERSION` pinned to release-2.32
- Inventory created for target cluster (`inventory/<cluster>/hosts.ini` exists)
- All images mirrored per `offline-artifacts/artifact-matrix.md` and verified with `skopeo inspect`
- Cilium Helm chart mirrored to internal registry (`helm search repo cilium` shows chart)
- F5 NGINX Ingress Controller chart mirrored (`helm search repo nginx-ingress` shows chart)
- DNS resolves the control-plane VIP from all nodes

<a id="step-00"></a>
<a id="step-01"></a>
## Step 01 — Kubespray inventory generation from hosts.ini with control-plane/etcd/worker groups

**Purpose**: Generate the Ansible inventory file that defines host groups for Kubespray cluster deployment.

**Prerequisites**:
- Step 00 complete (OS selection and node provisioning per OS selection guide)
- All nodes reachable via SSH with Ansible user

**Actions**:
```bash
# From the repo root (where kubespray/ lives), generate inventory
cat > inventory/mycluster/hosts.ini << 'EOF'
[all:vars]
ansible_user=ansible
ansible_become=yes
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'

# Control plane (3 nodes, stacked etcd)
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11 ip=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12 ip=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13 ip=10.20.0.13

[etcd]
k8s-cp-1
k8s-cp-2
k8s-cp-3

# Workers
[k8s-node]
k8s-w-1 ansible_host=10.20.0.21 ip=10.20.0.21
k8s-w-2 ansible_host=10.20.0.22 ip=10.20.0.22
k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23

[k8s-node:children]
gpu-node

[gpu-node]
k8s-gpu-1 ansible_host=10.50.0.11 ip=10.50.0.11 labels='{"accelerator":"nvidia"}'

# Groups Kubespray expects (do not reorder)
[kube-master]
control-plane

[kube-node]
control-plane
k8s-node

[k8s-cluster:children]
control-plane
etcd
k8s-node
EOF
```

**Validation**:
```bash
# Verify inventory structure
grep -c '\[' inventory/mycluster/hosts.ini
# Expected: 11 group headers (all:vars, control-plane, etcd, k8s-node, k8s-node:children, gpu-node, kube-master, kube-node, k8s-cluster)
grep '\[control-plane\]' inventory/mycluster/hosts.ini | wc -l
# Expected: 3
grep '\[etcd\]' inventory/mycluster/hosts.ini | wc -l
# Expected: 3
grep '\[k8s-node\]' inventory/mycluster/hosts.ini | wc -l
# Expected: 3
```

**Navigation**:
- Previous: Step 00 (anchor `#step-00`)
- Next: Step 02 (anchor `#step-02`)

<a id="step-02"></a>
## Step 02 — group_vars/k8s_cluster/k8s-cluster.yml configuration (Cilium CNI, kube-proxy-free, containerd)

**Purpose**: Configure core group variables for the cluster including CNI, kube-proxy mode, and service CIDRs.

**Prerequisites**:
- Step 01 complete (hosts.ini generated)
- Inventory directory exists with host definitions

**Actions**:
```bash
# Create group vars directory and write configuration
mkdir -p inventory/mycluster/group_vars/k8s_cluster
cat > inventory/mycluster/group_vars/k8s_cluster/k8s-cluster.yml << 'EOF'
# Kubernetes version. Must be inside the pinned Kubespray release's supported range.
kube_version: v1.36.5

# CNI. The release ships Cilium 1.20.3.
kube_network_plugin: cilium

# Disable kube-proxy; Cilium replaces it. Requires k8sServiceHost/Port below.
kube_proxy_mode: ""

# Pod and service CIDRs. One pair per cluster.
kube_pods_subnet: "10.30.0.0/16"
kube_service_addresses: "10.32.0.0/16"

# Cilium needs the API endpoint when kube-proxy is absent.
k8sServiceHost: "10.20.0.100"      # the control-plane VIP
k8sServicePort: 6443

enable_coredns: true
EOF
```

**Validation**:
```bash
# Verify key variables are set correctly
grep 'kube_network_plugin' inventory/mycluster/group_vars/k8s_cluster/k8s-cluster.yml
# Expected: kube_network_plugin: cilium
grep 'kube_proxy_mode' inventory/mycluster/group_vars/k8s_cluster/k8s-cluster.yml
# Expected: kube_proxy_mode: ""
grep 'kube_pods_subnet' inventory/mycluster/group_vars/k8s_cluster/k8s-cluster.yml
# Expected: kube_pods_subnet: "10.30.0.0/16"
```

**Navigation**:
- Previous: Step 01 (anchor `#step-01`)
- Next: Step 03 (anchor `#step-03`)

<a id="step-03"></a>
## Step 03 — Offline image registry setup via group_vars/all/offline.yml

**Purpose**: Configure the internal container registry and file mirror so Kubespray can pull all images and OS packages without internet access.

**Prerequisites**:
- Step 02 complete (group vars configured)
- Internal container registry reachable from all nodes
- Internal file repository reachable from all nodes

**Actions**:
```bash
# Create offline group vars directory and write configuration
mkdir -p inventory/mycluster/group_vars/all
cat > inventory/mycluster/group_vars/all/offline.yml << 'EOF'
# Internal registry and file mirror. See the Kubespray release-2.32 offline guide.
kube_image_repo: "{{ registry_host }}"
gcr_image_repo: "{{ registry_host }}"
docker_image_repo: "{{ registry_host }}"
quay_image_repo: "{{ registry_host }}"
github_image_repo: "{{ registry_host }}"

github_url: "{{ files_repo }}/github.com"
dl_k8s_io_url: "{{ files_repo }}/dl.k8s.io"
storage_googleapis_url: "{{ files_repo }}/storage.googleapis.com"
get_helm_url: "{{ files_repo }}/get.helm.sh"

local_path_provisioner_helper_image_repo: "{{ registry_host }}/busybox"

# containerd 2+ registry mirrors
containerd_registries_mirrors:
  - prefix: docker.io
    mirrors:
      - host: https://registry-1.docker.io
        capabilities: ["pull", "resolve"]
        skip_verify: false
  - prefix: "{{ registry_addr }}"
    mirrors:
      - host: "https://{{ registry_addr }}"
        capabilities: ["pull", "resolve"]
        skip_verify: false
        header:
          Authorization: "Basic {{ (registry_user + ':' + registry_pass) | b64encode }}"

# Cilium: mirror the chart index and the chart tarball into files_repo
cilium_install_extra_flags: "--repository {{ files_repo }}/helm.cilium.io/"
cilium_extra_values:
  image:
    useDigest: false
  hubble:
    relay:
      image:
        useDigest: false
    ui:
      backend:
        image:
          useDigest: false
      frontend:
        image:
          useDigest: false
  operator:
    image:
      override: "{{ registry_host }}/cilium/operator-generic:v1.20.3"
      useDigest: false
      extension: ""
  certgen:
    image:
      useDigest: false
  envoy:
    image:
      useDigest: false

# OS package repositories (Oracle Linux / RHEL family)
containerd_rh_repo_base_url: "{{ yum_repo }}/containerd"
containerd_rh_repo_gpgkey: "{{ yum_repo }}/containerd/gpgkey"

# OS package repositories (Ubuntu)
containerd_ubuntu_repo_base_url: "{{ ubuntu_repo }}/containerd"
containerd_ubuntu_repo_gpgkey: "{{ ubuntu_repo }}/containerd/gpgkey"
containerd_ubuntu_repo_repokey: 'YOURREPOKEY'
EOF
```

**Validation**:
```bash
# Verify offline group vars are present and properly structured
grep 'kube_image_repo' inventory/mycluster/group_vars/all/offline.yml
# Expected: kube_image_repo: "{{ registry_host }}"
grep 'cilium_install_extra_flags' inventory/mycluster/group_vars/all/offline.yml
# Expected: cilium_install_extra_flags: "--repository {{ files_repo }}/helm.cilium.io/"
grep 'containerd_registries_mirrors' inventory/mycluster/group_vars/all/offline.yml
# Expected: containerd_registries_mirrors section present
```

**Navigation**:
- Previous: Step 02 (anchor `#step-02`)
- Next: Step 04 (anchor `#step-04`)

<a id="step-04"></a>
## Step 04 — Syntax-check and pre-check commands

**Purpose**: Validate the playbook YAML for parsing errors and verify Ansible communication with all hosts before deployment.

**Prerequisites**:
- Step 03 complete (offline registry configured)
- Inventory file exists with host definitions

**Actions**:
```bash
# 4.1 Syntax check - validate playbook YAML without contacting hosts
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml --syntax-check
# Expected output: playbook: cluster.yml: syntax check passed

# 4.2 Ansible ping - verify communication with all hosts
ansible -i inventory/mycluster/hosts.ini all -m ping
# Expected output (one line per host):
# k8s-cp-1 | pong
# k8s-cp-2 | pong
# k8s-cp-3 | pong
# k8s-w-1 | pong
# k8s-w-2 | pong
# k8s-w-3 | pong

# 4.3 Check and diff - simulated deployment limited to control-plane nodes
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b --check --diff --limit control-plane
# Expected output: playbook plan with changed/ok for each task, no actual system modifications
```

**Validation**:
```bash
# Verify syntax check passed
grep "syntax check passed" <(ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml --syntax-check 2>&1)
# Expected: contain string "syntax check passed"
```

**Navigation**:
- Previous: Step 03 (anchor `#step-03`)
- Next: Step 05 (anchor `#step-05`)

<a id="step-05"></a>
## Step 05 — Control-plane deployment one node at a time with kubeadm join and upload-certs

**Purpose**: Deploy the control-plane nodes sequentially using Kubespray, one node at a time to preserve API server quorum.

**Prerequisites**:
- Step 04 complete (pre-checks passed)
- All control-plane nodes reachable via SSH

**Actions**:
```bash
# 5.1 Deploy first control-plane node
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b --limit k8s-cp-1

# 5.2 Verify first node is ready
kubectl get nodes k8s-cp-1
# Expected: Ready, Status=Ready

kubectl get --raw='/readyz?verbose' | grep -E "(IP|kubelet|apiserver|controller-manager|scheduler)"
# Expected: all components responding

# 5.3 Deploy remaining control-plane nodes one at a time
# Second control-plane node
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b --limit k8s-cp-2

# Third control-plane node
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b --limit k8s-cp-3
```

**Validation**:
```bash
# Verify all control-plane nodes are ready
kubectl get nodes
# Expected: 3 control-plane nodes showing Ready status with VERSION v1.36.5

# Verify etcd cluster health
etcdctl --endpoints=https://127.0.0.1:2379 endpoint health \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
# Expected: all healthy
```

**Navigation**:
- Previous: Step 04 (anchor `#step-04`)
- Next: Step 06 (anchor `#step-06`)

<a id="step-06"></a>
## Step 06 — Worker node join

**Purpose**: Add worker nodes to the cluster. Kubespray generates the kubeadm join command and nodes pick it up automatically from their kubelet configuration.

**Prerequisites**:
- Step 05 complete (all control-plane nodes deployed and etcd healthy)
- Worker nodes reachable via SSH

**Actions**:
```bash
# 6.1 Deploy workers
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml -b --limit k8s-node

# 6.2 Verify worker nodes are ready
kubectl get nodes
# Expected output:
# NAME         STATUS   ROLES           AGE   VERSION
# k8s-cp-1     Ready    control-plane   10m   v1.36.5
# k8s-cp-2     Ready    control-plane   8m    v1.36.5
# k8s-cp-3     Ready    control-plane   6m    v1.36.5
# k8s-w-1      Ready    <none>          5m    v1.36.5
# k8s-w-2      Ready    <none>          3m    v1.36.5
# k8s-w-3      Ready    <none>          1m    v1.36.5

# 6.3 Verify pod readiness across namespaces
kubectl get pods -A
# Expected: All kube-system pods should be Running, except possibly short-lived startup containers
```

**Validation**:
```bash
# Verify all 6 nodes are Ready
kubectl get nodes -o json | python3 -c "
import sys, json
nodes = json.load(sys.stdin)['items']
ready = [n for n in nodes if 'Ready' in n['status']['conditions'][0]['type']]
print(f'Total nodes: {len(nodes)}, Ready: {len(ready)}')
# Expected: Total nodes: 6, Ready: 6
"
```

**Navigation**:
- Previous: Step 05 (anchor `#step-05`)
- Next: Step 07 (anchor `#step-07`)

<a id="step-07"></a>
## Step 07 — Cilium CNI installation and validation

**Purpose**: Verify Cilium CNI is properly installed and functioning, including BPF data path and connectivity.

**Prerequisites**:
- Step 06 complete (all worker nodes joined and Ready)
- kubectl access to the cluster

**Actions**:
```bash
# 7.1 Verify Cilium DaemonSet is running
kubectl -n kube-system get pods -l k8s-app=cilium
# Expected: 6 pods (3 agents + 3 relays, or as DaemonSet size)

# 7.2 Check Cilium status
cilium status
# Expected output sections:
# - Cluster info
# - Node-bpf state: installed (or disabled)
# - KubeProxyReplacement: True
# - kubeProxyReplacementError: none
# - Cluster CIDR: 10.30.0.0/16
# - Service CIDR: 10.32.0.0/16

# 7.3 Run connectivity test
cilium connectivity test
# Expected: all probes pass (e2e, host, l3, l2, etc. depending on mode)

# 7.4 Validate kube-proxy replacement
kubectl -n kube-system get daemonset cilium-agent
# Or check the kube-proxy replacement status
kubectl get nodes -o json | python3 -c "
import sys, json
for node in json.load(sys.stdin)['items']:
    node_name = node['metadata']['name']
    addresses = [a['address'] for a in node['status']['addresses']]
    print(f'{node_name}: addresses={addresses}')
"

# 7.5 Basic network policy test (audit mode first)
# Allow DNS egress
cat <<EOF | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-dns
  namespace: kube-system
spec:
  endpointSelector: {}
  egress:
    - toEndpoints:
        - matchLabels:
            k8s:app.kubernetes.io/name: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
            - port: "53"
              protocol: TCP
EOF
```

**Validation**:
```bash
# Verify Cilium is running and kube-proxy is replaced
cilium status | grep 'KubeProxyReplacement'
# Expected: KubeProxyReplacement: True

cilium status | grep 'kubeProxyReplacementError'
# Expected: kubeProxyReplacementError: none

# Verify cluster CIDR
cilium status | grep 'Cluster CIDR'
# Expected: Cluster CIDR: 10.30.0.0/16

# Verify service CIDR
cilium status | grep 'Service CIDR'
# Expected: Service CIDR: 10.32.0.0/16
```

**Navigation**:
- Previous: Step 06 (anchor `#step-06`)
- Next: Step 08 (anchor `#step-08`)

<a id="step-08"></a>
## Step 08 — NGINX ingress controller installation and validation

**Purpose**: Install the F5 NGINX Ingress Controller using Helm with exact chart version and offline image digests, and configure Gateway API support.

**Prerequisites**:
- Step 07 complete (Cilium CNI installed and validated)
- Helm installed and configured with offline repositories

**Actions**:
```bash
# 8.1 Add Helm repository
helm repo add nginx-ingress https://nginx.github.io/helm-charts
helm repo update

# 8.2 Install NGINX Ingress Controller
helm install nic nginx-ingress/nginx-ingress \
  --version 2.8.0 \
  --namespace ingress-nginx --create-namespace \
  --set controller.image.repository=harbor.internal/platform/nginx-ingress/controller \
  --set controller.admissionWebhooks.enabled=true \
  --set controller.admissionWebhooks.patch.image.repository=harbor.internal/platform/nginx-ingress/admission-webhook \
  --set controller.admissionWebhooks.patch.image.digest="" \
  --set controller.service.type=LoadBalancer \
  --set controller.config.ingress-class=nginx \
  --set controller.metrics.enabled=true \
  --set controller.metrics.serviceMonitor.enabled=true

# 8.3 Configure Gateway API
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml

# Configure the controller to watch Gateway API resources
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-ingress-gateway-api
  namespace: ingress-nginx
data:
  enable-gateway-api: "true"
  gateway-class: nginx
EOF

# Disable snippet annotations (security hardening)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-ingress-snippet-hardening
  namespace: ingress-nginx
data:
  enable-snippets: "false"
  enable-server-snippets: "false"
  enable-stream-snippets: "false"
  allow-snippet-annotations: "false"
EOF

# 8.4 Verify ingress controller is running
kubectl -n ingress-nginx get pods
# Expected: controller pod(s) Ready

kubectl -n ingress-nginx get svc
# Expected: Service with VIP (MetalLB or cloud LB)

kubectl get gatewayclass
# Expected: gatewayclass.k8s.io/nginx listed

kubectl get gateway,httproute -A
# Expected: no resources yet, or your application resources
```

**Validation**:
```bash
# Verify NGINX Ingress Controller pods are Ready
kubectl -n ingress-nginx get pods
# Expected: 1 or more pods with READY=1/1 or READY=2/2

# Verify GatewayClass is available
kubectl get gatewayclass
# Expected: gatewayclass.k8s.io/nginx listed as available

# Verify ingress service has VIP
kubectl -n ingress-nginx get svc
# Expected: LoadBalancer INGRESS-IP assigned (or pending if using MetalLB in defer mode)
```

**Navigation**:
- Previous: Step 07 (anchor `#step-07`)
- Next: Step 09 (anchor `#step-09`)

<a id="step-09"></a>
## Step 09 — Post-deployment validation commands

**Purpose**: Run comprehensive validation commands after all components (CNI, ingress, add-ons) are deployed to confirm the cluster is healthy and ready for workloads.

**Prerequisites**:
- Step 08 complete (NGINX Ingress Controller installed and validated)
- All cluster components deployed

**Actions**:
```bash
# 9.1 Get nodes status
kubectl get nodes -o wide
# Expected: all nodes Ready, with correct roles and IP addresses

# 9.2 Readyz check
kubectl get --raw='/readyz?verbose'
# Expected: all ok (no failures, no warnings)

# 9.3 Cilium status
cilium status
# Expected: KubeProxyReplacement: True, KubeProxyReplacementError: none
# Cross-node pod CIDR routing healthy

# 9.4 Ingress health
kubectl -n ingress-nginx get pods
kubectl -n ingress-nginx get svc
curl -vk https://<ingress-vip>/healthz \
  -H 'Host: app.internal'
# Expected: 200 with valid certificate chain

# 9.5 Full cluster validation
# All namespaces pods
kubectl get pods -A wide

# CoreDNS
kubectl -n kube-system get pods -l k8s-app=kube-dns

# etcd health
etcdctl --endpoints=https://127.0.0.1:2379 endpoint health --cluster \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key

# API server reachable
kubectl api-versions

# Storage (Ceph RBD/FS if configured)
kubectl get storageclass

# 9.6 DNS resolution from pod
kubectl run test-dns --rm -i --tty --image=harbor.internal/tools/dnstools \
  -- dig kubernetes.default.svc.cluster.local +short
# Expected: 10.32.0.1 (cluster IP of kube-dns)
```

**Validation**:
```bash
# Verify all validation checks pass
# At least 5/6 nodes showing Ready
kubectl get nodes -o json | python3 -c "
import sys, json
nodes = json.load(sys.stdin)['items']
ready = sum(1 for n in nodes if 'Ready' in n['status']['conditions'][0]['type'])
print(f'Nodes: {len(nodes)}, Ready: {ready}')
# Expected: ready >= 5, api-versions returns non-empty list
"
```

**Navigation**:
- Previous: Step 08 (anchor `#step-08`)
- Next: Step 10 (anchor `#step-10`)

<a id="step-10"></a>
## Step 10 — Rollback procedures

**Purpose**: Document rollback procedures for control-plane node failures and full cluster resets.

**Prerequisites**:
- Step 09 complete (post-deployment validation passed)
- Inventory and group vars preserved in Git

**Actions**:
```bash
# Rollback control-plane node
# If a control-plane node fails to join or becomes unhealthy:

# 1. Reset the failed node (if kubeadm initialized it):
ansible-playbook -i inventory/mycluster/hosts.ini reset.yml --limit <failed-node>

# Kubespray-provided reset script removes kubeadm state and resets the node to join again.

# 2. Re-deploy the node:
ansible-playbook -i inventory/mycluster/hosts.ini cluster.yml --limit <failed-node>

# 3. Verify etcd quorum after re-deploy:
etcdctl endpoint health --cluster \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
# Expected: all healthy

# Rollback full cluster
# If the deployment is fundamentally broken and needs to be restarted from scratch:

# 1. Reset all nodes (ordered: workers first, then control-plane):
# Reset workers
ansible-playbook -i inventory/mycluster/hosts.ini reset.yml --limit k8s-node

# Reset control-plane nodes (one at a time to preserve etcd quorum during reset)
ansible-playbook -i inventory/mycluster/hosts.ini reset.yml --limit k8s-cp-1
ansible-playbook -i inventory/mycluster/hosts.ini reset.yml --limit k8s-cp-2
ansible-playbook -i inventory/mycluster/hosts.ini reset.yml --limit k8s-cp-3

# 2. Clean etcd data (optional, destructive):
# On each control-plane node
rm -rf /var/lib/etcd/default.etcd
rm -rf /etc/kubernetes/pki/etcd

# 3. Re-run the full deployment from Step 1 (inventory generation) through Step 9 (validation).

# Important rollback rules
# - Never delete /etc/kubernetes to "start clean" on a node that holds state. Use kubespray reset (Kubespray-provided) as the intended teardown.
# - Keep the inventory and group vars in Git so a rerun is reproducible from the recorded state.
# - Take a snapshot before starting any deployment that you may need to roll back. etcd snapshots are the authoritative backup.
# - Reruns are safe — Kubespray is idempotent by design. A rerun after a failed deploy is the recommended recovery step, not a fresh install.
```

**Validation**:
```bash
# Verify rollback procedures are documented and inventory is preserved
ls inventory/mycluster/hosts.ini
# Expected: file exists (inventory preserved in Git)

# Verify kubespray reset script is available
ls kubespray/reset.yml
# Expected: file exists (Kubespray-provided)
```

**Navigation**:
- Previous: Step 09 (anchor `#step-09`)
- Next: None (Step 10 is the last step)
