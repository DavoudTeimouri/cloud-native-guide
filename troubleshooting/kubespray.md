# Kubespray Troubleshooting

## A. Purpose and scope

Troubleshooting guide for Kubespray deployment failures. Covers Ansible connectivity, inventory validation, image pull failures, etcd bootstrap, and control-plane quorum. Cross-references `kubespray-deployment.md` for deployment procedures and `lifecycle/upgrades/kubespray.md` for upgrade procedures.

## B. Ansible connectivity failures

### Symptom: `unreachable` or `failed` on all hosts

**Possible causes:**
- SSH key not deployed to target hosts
- Wrong SSH user or port in inventory
- Firewall blocking SSH (port 22)
- Host not reachable from Automation Management Server

**Verification:**
```bash
ansible -i inventory/<cluster>/hosts.ini all -m ping
ansible -i inventory/<cluster>/hosts.ini all -m shell -a "hostname"
```

**Fix:**
- Verify SSH keys: `ssh -i <key> <user>@<host> hostname`
- Check inventory: `ansible -i inventory/<cluster>/hosts.ini all -m debug -a "var=ansible_host"`
- Test network: `ssh -i <key> <user>@<host> -p 22 exit`

## C. Inventory validation errors

### Symptom: `ERROR! conflicting settings` or missing variables

**Possible causes:**
- `group_vars/k8s_cluster/k8s-cluster.yml` missing required keys
- `group_vars/all/all.yml` missing required settings
- Mixing Kubespray release group_vars without diffing

**Verification:**
```bash
ansible -i inventory/<cluster>/hosts.ini all -m debug -a "var=kube_version"
ansible -i inventory/<cluster>/hosts.ini all -m debug -a "var=container_runtime"
```

**Fix:**
- Diff group_vars against new release's `inventory/sample`
- Never reuse group_vars across Kubespray releases without diffing
- Pin Kubespray release in `kubespray/VERSION`

## D. Image pull failures in offline environment

### Symptom: `ImagePullBackOff` or `ErrImagePull` on pods

**Possible causes:**
- Image not mirrored to internal Harbor
- containerd `hosts.toml` not configured for mirror
- Digest mismatch between manifest and image

**Verification:**
```bash
crictl inspecti <image-digest>
ctr -n k8s.io images list
```

**Fix:**
- Mirror image to `harbor.internal/platform/...` per `offline-artifacts/artifact-matrix.md`
- Update `group_vars/all/all.yml/containerd.yml` with registry mirror
- Restart containerd: `systemctl restart containerd`

## E. etcd bootstrap failures

### Symptom: etcd pod crash-looping, `etcd: member already exist`

**Possible causes:**
- Stale etcd data directory from previous deployment
- Wrong `etcd_deployment_type` or `etcd_storage_backend`
- Network partition between control-plane nodes

**Verification:**
```bash
kubectl -n kube-system get pods -l component=etcd
kubectl -n kube-system logs -l component=etcd -c etcd
```

**Fix:**
- Clean stale data directory: `rm -rf /var/lib/etcd/*` (on affected node only)
- Verify `etcd_deployment_type: stacked` or `external` in group_vars
- Restore from etcd snapshot if data is corrupted

## F. Control-plane quorum loss

### Symptom: `kubectl get nodes` returns error, API server unreachable

**Possible causes:**
- Multiple control-plane nodes down simultaneously
- etcd quorum lost (less than majority of members healthy)
- API server static pod not recreated by kubelet

**Verification:**
```bash
kubectl get nodes
kubectl get --raw='/readyz?verbose'
kubectl -n kube-system get pods -l component=kube-apiserver
```

**Fix:**
- Restart one control-plane node at a time, preserving quorum
- Restart kube-apiserver static pod (kubelet recreates on manifest change)
- Verify `kubectl auth whoami` with a federated user after each restart
- **Do not restart all control-plane nodes simultaneously**

## G. Cross-references

- `kubespray/kubespray-deployment.md` — Kubespray deployment procedures
- `lifecycle/upgrades/kubespray.md` — Kubespray upgrade procedures
- `architecture/02-deployment-topology.md` — Deployment topology
