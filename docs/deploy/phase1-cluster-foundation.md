# Phase 1 — Cluster Foundation

**Purpose**: Deploy a Kubespray-managed Kubernetes cluster on bare-metal with Cilium CNI, kube-proxy-free mode, containerd runtime, and NGINX Ingress Controller. This phase covers inventory generation, group variable configuration, offline registry setup, pre-deployment validation, control-plane and worker node deployment, CNI and ingress installation, and post-deployment validation.

**Entry criteria**:
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

---

## 1. Kubespray inventory generation from hosts.ini with control-plane/etcd/worker groups

Generate the Ansible inventory file at `kubespray/inventory/<cluster>/hosts.ini`. This file defines host groups that Kubespray uses to orchestrate deployment.

### Inventory structure

```ini
[all:vars]
ansible_user=ansible
ansible_become=yes
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'

# ---------------------------------------------------------------------------
# Control plane (3 nodes, stacked etcd)
# ---------------------------------------------------------------------------
[control-plane]
k8s-cp-1 ansible_host=10.20.0.11 ip=10.20.0.11
k8s-cp-2 ansible_host=10.20.0.12 ip=10.20.0.12
k8s-cp-3 ansible_host=10.20.0.13 ip=10.20.0.13

[etcd]
k8s-cp-1
k8s-cp-2
k8s-cp-3

# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------
[k8s-node]
k8s-w-1 ansible_host=10.20.0.21 ip=10.20.0.21
k8s-w-2 ansible_host=10.20.0.22 ip=10.20.0.22
k8s-w-3 ansible_host=10.20.0.23 ip=10.20.0.23

[k8s-node:children]
gpu-node

[gpu-node]
k8s-gpu-1 ansible_host=10.50.0.11 ip=10.50.0.11 labels='{"accelerator":"nvidia"}'

# ---------------------------------------------------------------------------
# Groups Kubespray expects (do not reorder)
# ---------------------------------------------------------------------------
[kube-master]
control-plane

[kube-node]
control-plane
k8s-node

[k8s-cluster:children]
control-plane
etcd
k8s-node
```

### Rules
- Every worker, including GPU and storage nodes, must be in the `k8s-node` group.
- `etcd` members must also be in `control-plane` when etcd is stacked.
- A host must not appear in two `k8s-node` groups.
- `ip=` must be the address on the cluster network, not the management address.

---

## 2. group_vars/k8s_cluster/k8s-cluster.yml configuration

Configure core group variables for the cluster. These variables live at `kubespray/inventory/<cluster>/group_vars/k8s_cluster/k8s-cluster.yml`.

### Core configuration

```yaml
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
```

### Key settings explained

- `kube_proxy_mode: ""` — an empty value disables kube-proxy. This is required for Cilium's kube-proxy-free mode. The variable name is per-release — verify against the pinned release's `roles/kubespray_defaults/defaults/main/` before use.
- `kube_network_plugin: cilium` — tells Kubespray to install Cilium as the CNI plugin.
- `k8sServiceHost` / `k8sServicePort` — Cilium agent needs the API server endpoint when running in kube-proxy-free mode; these values must match the control-plane VIP and port.

### Reference
- `docs/kubespray/group-vars-template.md` — authoritative group vars template
- `docs/kubespray/inventory-and-variables.md` — inventory design reference

---

## 3. Offline image registry setup via group_vars/all/offline.yml

Configure the internal container registry and file mirror so Kubespray can pull all images and OS packages without internet access.

### Offline group variables

```yaml
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
```

### OS package repositories (Oracle Linux / RHEL family)

```yaml
containerd_rh_repo_base_url: "{{ yum_repo }}/containerd"
containerd_rh_repo_gpgkey: "{{ yum_repo }}/containerd/gpgkey"
```

### OS package repositories (Ubuntu)

```yaml
containerd_ubuntu_repo_base_url: "{{ ubuntu_repo }}/containerd"
containerd_ubuntu_repo_gpgkey: "{{ ubuntu_repo }}/containerd/gpgkey"
containerd_ubuntu_repo_repokey: 'YOURREPOKEY'
```

### Key variables

- `registry_host` — container image registry hostname (e.g. `harbor.internal`). If the internal registry uses the same repository paths as upstream, no per-image overrides are needed.
- `registry_addr` — registry as `[domain or ip]:[port]` only.
- `files_repo` — HTTP server or reverse proxy serving the static file tree. Include the version in the path so an upgrade does not change the URL.
- `yum_repo` / `debian_repo` / `ubuntu_repo` — internal OS package repository for the matching OS.
- `registry_user` / `registry_pass` — registry credentials, stored with `!vault`.

### Reference
- `docs/kubespray/kubespray-deployment.md` §F — offline image configuration
- `docs/kubespray/group-vars-template.md` — full group vars template

---

## 4. syntax-check and pre-check commands

Before any Kubespray playbook execution, run syntax and pre-checks to catch configuration errors early.

### 4.1 Syntax check

Validate the playbook YAML for parsing errors without contacting any hosts.

```bash
# From the repo root (where kubespray/ lives)
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml --syntax-check
```

Expected output: `playbook: cluster.yml: syntax check passed`

### 4.2 Ansible ping

Verify Ansible can communicate with all hosts.

```bash
ansible -i inventory/<cluster>/hosts.ini all -m ping
```

Expected output (one line per host): `k8s-cp-1 | pong`
`k8s-cp-2 | pong`
`k8s-cp-3 | pong`
`k8s-w-1 | pong`
`k8s-w-2 | pong`
`k8s-w-3 | pong`

### 4.3 Check and diff (control-plane limited run)

Run a simulated deployment limited to control-plane nodes, showing diffs without making changes.

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --check --diff --limit control-plane
```

Expected output: playbook plan with `changed`/`ok` for each task, no actual system modifications.

---

## 5. Control-plane deployment one node at a time with kubeadm join and upload-certs

Deploy the control-plane nodes sequentially. Kubespray handles `kubeadm init` under the hood, but the procedure is one node at a time to preserve API server quorum.

### 5.1 Deploy first control-plane node

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-1
```

### 5.2 Verify first node is ready

```bash
kubectl get nodes k8s-cp-1
# Expected: Ready, Status=Ready
kubectl get --raw='/readyz?verbose' | grep -E "(IP|kubelet|apiserver|controller-manager|scheduler)"
```

### 5.3 Deploy remaining control-plane nodes one at a time

```bash
# Second control-plane node
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-2

# Third control-plane node
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-3
```

### 5.4 Verify etcd cluster health

```bash
etcdctl --endpoints=https://127.0.0.1:2379 endpoint health \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
# Expected: all healthy
```

### 5.5 kubeadm join (if joining additional control-plane nodes outside Kubespray)

```bash
# On each additional control-plane node
kubeadm join <control-plane-vip>:6443 --control-plane --certificate-key <key>
```

**Note**: Kubespray manages the control-plane setup internally. The `kubeadm join --control-plane` command is only needed when adding extra control-plane nodes after the initial Kubespray deploy, or for recovery procedures.

---

## 6. Worker node join

Add worker nodes to the cluster. Kubespray generates the `kubeadm join` command and nodes pick it up automatically from their `kubelet` configuration.

### 6.1 Deploy workers

```bash
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-node
```

### 6.2 Verify worker nodes are ready

```bash
kubectl get nodes
# Expected output:
# NAME         STATUS   ROLES           AGE   VERSION
# k8s-cp-1     Ready    control-plane   10m   v1.36.5
# k8s-cp-2     Ready    control-plane   8m    v1.36.5
# k8s-cp-3     Ready    control-plane   6m    v1.36.5
# k8s-w-1      Ready    <none>          5m    v1.36.5
# k8s-w-2      Ready    <none>          3m    v1.36.5
# k8s-w-3      Ready    <none>          1m    v1.36.5
```

### 6.3 Verify pod readiness across namespaces

```bash
kubectl get pods -A
# All kube-system pods should be Running, except possibly short-lived startup containers
```

---

## 7. Cilium CNI installation and validation

Cilium is installed by Kubespray via the `kube_network_plugin: cilium` variable and the offline Helm chart configuration in `group_vars/all/offline.yml`.

### 7.1 Verify Cilium DaemonSet is running

```bash
kubectl -n kube-system get pods -l k8s-app=cilium
# Expected: 6 pods (3 agents + 3 relays, or as DaemonSet size)
```

### 7.2 Check Cilium status

```bash
cilium status
# Expected output sections:
# - Cluster info
# - Node-bpf state: installed (or disabled)
# - KubeProxyReplacement: True
# - kubeProxyReplacementError: none
# - Cluster CIDR: 10.30.0.0/16
# - Service CIDR: 10.32.0.0/16
```

### 7.3 Run connectivity test

```bash
cilium connectivity test
# Expected: all probes pass (e2e, host, l3, l2, etc. depending on mode)
```

### 7.4 Validate kube-proxy replacement

```bash
kubectl -n kube-system get daemonset cilium-agent
# Or check the kube-proxy replacement status
kubectl get nodes -o json | python3 -c "
import sys, json
for node in json.load(sys.stdin)['items']:
    node_name = node['metadata']['name']
    addresses = [a['address'] for a in node['status']['addresses']]
    print(f'{node_name}: addresses={addresses}')
"
```

### 7.5 Basic network policy test (audit mode first)

```bash
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

### 7.6 Hubble observability (optional but recommended)

```bash
cilium hubble status
cilium hubble relay status
cilium hubble ui status
```

### Reference
- `docs/kubernetes/networking/cilium.md` — full Cilium configuration and troubleshooting
- `docs/kubespray/offline-deployment-checklist.md` §F — CNI verification items

---

## 8. NGINX ingress controller installation and validation

Install the F5 NGINX Ingress Controller (retired the community `kubernetes/ingress-nginx` in March 2026). Use Helm with the exact chart version and offline image digests.

### 8.1 Add Helm repository

```bash
helm repo add nginx-ingress https://nginx.github.io/helm-charts
helm repo update
```

### 8.2 Install NGINX Ingress Controller

```bash
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
```

### 8.3 Configure Gateway API (required for the replacement controller)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml
```

Configure the controller to watch Gateway API resources:

```yaml
controller:
  config:
    enable-gateway-api: "true"
    gateway-class: nginx
```

Disable snippet annotations (security hardening):

```yaml
controller:
  config:
    enable-snippets: "false"
    enable-server-snippets: "false"
    enable-stream-snippets: "false"
    allow-snippet-annotations: "false"
```

### 8.4 Verify ingress controller is running

```bash
kubectl -n ingress-nginx get pods
# Expected: controller pod(s) Ready
kubectl -n ingress-nginx get svc
# Expected: Service with VIP (MetalLB or cloud LB)
kubectl get gatewayclass
# Expected: gatewayclass.k8s.io/nginx listed
kubectl get gateway,httproute -A
# Expected: no resources yet, or your application resources
```

### 8.5 TLS validation (cert-manager + Vault PKI)

Certificates are issued via cert-manager from the Vault PKI issuer (see `docs/kubernetes/ingress/nginx-ingress.md` §TLS). Validate a certificate:

```bash
kubectl -n ingress-nginx get secret <secret-name> -o jsonpath='{.data.tls\.crt}' | openssl x509 -noout -dates
```

### 8.6 External health check

```bash
curl -vk https://<ingress-vip>/healthz \
  -H 'Host: app.internal'
# Expected: 200 with valid certificate chain
```

### 8.7 Verify admission webhook failure policy

```bash
kubectl get mutatingwebhookconfiguration -A | grep nginx-ingress
# Confirm failurePolicy is Fail for application namespaces
```

### Reference
- `docs/kubernetes/ingress/nginx-ingress.md` — full F5 NGINX Ingress Controller configuration
- `docs/kubespray/offline-deployment-checklist.md` §G — Platform services items

---

## 9. Post-deployment validation commands

Run these commands after all components (CNI, ingress, add-ons) are deployed to confirm the cluster is healthy and ready for workloads.

### 9.1 Get nodes status

```bash
kubectl get nodes -o wide
# Expected: all nodes Ready, with correct roles and IP addresses
```

### 9.2 Readyz check

```bash
kubectl get --raw='/readyz?verbose'
# Expected: all ok (no failures, no warnings)
```

### 9.3 Cilium status

```bash
cilium status
# Expected: KubeProxyReplacement: True, KubeProxyReplacementError: none
# Cross-node pod CIDR routing healthy
```

### 9.4 Ingress health

```bash
kubectl -n ingress-nginx get pods
kubectl -n ingress-nginx get svc
curl -vk https://<ingress-vip>/healthz \
  -H 'Host: app.internal'
# Expected: 200 with valid certificate chain
```

### 9.5 Full cluster validation

```bash
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
```

### 9.6 DNS resolution from pod

```bash
kubectl run test-dns --rm -i --tty --image=harbor.internal/tools/dnstools \
  -- dig kubernetes.default.svc.cluster.local +short
# Expected: 10.32.0.1 (cluster IP of kube-dns)
```

---

## Rollback procedures

### Rollback control-plane node

If a control-plane node fails to join or becomes unhealthy:

1. **Reset the failed node** (if kubeadm initialized it):

   ```bash
   ansible-playbook -i inventory/<cluster>/hosts.ini reset.yml --limit <failed-node>
   ```

   *Kubespray-provided reset script removes kubeadm state and resets the node to join again.*

2. **Re-deploy the node**:

   ```bash
   ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml --limit <failed-node>
   ```

3. **Verify etcd quorum** after re-deploy:

   ```bash
   etcdctl endpoint health --cluster --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
     --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
   ```

### Rollback full cluster

If the deployment is fundamentally broken and needs to be restarted from scratch:

1. **Reset all nodes** (ordered: workers first, then control-plane):

   ```bash
   # Reset workers
   ansible-playbook -i inventory/<cluster>/hosts.ini reset.yml --limit k8s-node

   # Reset control-plane nodes (one at a time to preserve etcd quorum during reset)
   ansible-playbook -i inventory/<cluster>/hosts.ini reset.yml --limit k8s-cp-1
   ansible-playbook -i inventory/<cluster>/hosts.ini reset.yml --limit k8s-cp-2
   ansible-playbook -i inventory/<cluster>/hosts.ini reset.yml --limit k8s-cp-3
   ```

2. **Clean etcd data** (optional, destructive):

   ```bash
   # On each control-plane node
   rm -rf /var/lib/etcd/default.etcd
   rm -rf /etc/kubernetes/pki/etcd
   ```

3. **Re-run the full deployment** from Step 1 (inventory generation) through Step 9 (validation).

### Important rollback rules

- **Never delete `/etc/kubernetes` to "start clean"** on a node that holds state. Use `kubespray reset` (Kubespray-provided) as the intended teardown.
- **Keep the inventory and group vars in Git** so a rerun is reproducible from the recorded state.
- **Take a snapshot before starting** any deployment that you may need to roll back. etcd snapshots are the authoritative backup.
- **Reruns are safe** — Kubespray is idempotent by design. A rerun after a failed deploy is the recommended recovery step, not a fresh install.

---

## Cross-references

- `docs/kubespray/kubespray-deployment.md` — full Kubespray deployment guide (offline execution, best practices, validation)
- `docs/kubespray/group-vars-template.md` — authoritative group vars template with variable names
- `docs/kubespray/inventory-and-variables.md` — inventory design reference
- `docs/kubespray/inventory-template.ini` — inventory template
- `docs/kubernetes/networking/cilium.md` — Cilium CNI configuration, offline preparation, validation
- `docs/kubernetes/ingress/nginx-ingress.md` — F5 NGINX Ingress Controller installation, Gateway API, TLS
- `docs/kubespray/offline-deployment-checklist.md` — end-to-end offline deployment checklist
- `compatibility/version-matrix.md` — supported Kubernetes/Cilium/NGINX versions per release
