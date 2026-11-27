# Kubespray Offline Deployment Checklist

## A. Purpose and scope

Document the end-to-end offline deployment checklist for Kubespray/Kubernetes in an air-gapped environment.

Every item must be completed before declaring the deployment ready. Items marked "VERIFY" require a successful test or command output.

Cross-references `kubespray/kubespray-deployment.md` §F (Offline image configuration), `offline-artifacts/artifact-matrix.md`, `offline-artifacts/nexus-harbor-integration.md`, `compatibility/version-matrix.md`.

## B. Phase 1: Infrastructure preparation

| # | Item | VERIFY |
|---|------|--------|
| B1 | Automation Management Server provisioned (Terraform + Ansible) | `terraform show` lists expected VMs |
| B2 | OS installed from internal mirror (Oracle Linux or Ubuntu) | `cat /etc/os-release` matches pinned version |
| B3 | containerd 2.3.7 installed from internal repository | `containerd --version` shows 2.3.7 |
| B4 | Ansible 2.19.x installed in virtualenv | `ansible --version` shows 2.19.x |
| B5 | Python 3.11-3.13 installed | `python3 --version` shows 3.11-3.13 |
| B6 | NTP synchronized on all nodes | `chronyc tracking` shows synchronized |
| B7 | SSH access for Ansible user on all nodes | `ansible all -m ping` returns pong |
| B8 | Internal registry reachable from all nodes | `skopeo inspect docker://harbor.internal/...` succeeds |
| B9 | Internal file repository reachable from all nodes | `curl -sf http://files-repo.internal/` succeeds |
| B10 | Internal OS package repository configured | `dnf repolist` or `apt-cache policy` shows internal repos |

## C. Phase 2: Image mirroring

| # | Item | VERIFY |
|---|------|--------|
| C1 | Kubernetes control plane images mirrored | `skopeo inspect docker://harbor.internal/platform/kubernetes/kube-apiserver:v1.36.5` |
| C2 | Kubespray container image mirrored | `skopeo inspect docker://harbor.internal/platform/kubespray/kubespray:v2.32.0` |
| C3 | etcd image mirrored | `skopeo inspect docker://harbor.internal/platform/etcd` |
| C4 | containerd image mirrored | `skopeo inspect docker://harbor.internal/platform/containerd` |
| C5 | CNI plugin images mirrored (Cilium) | `skopeo inspect docker://harbor.internal/platform/cilium` |
| C6 | Helm chart images mirrored | `skopeo inspect docker://harbor.internal/platform/...` |
| C7 | All images in artifact-matrix.md mirrored | Check each row's Internal destination |
| C8 | Image digests recorded in artifact-matrix.md | Digest matches `skopeo inspect --raw` output |

## D. Phase 3: Helm chart mirroring

| # | Item | VERIFY |
|---|------|--------|
| D1 | Cilium Helm chart mirrored to Nexus | `helm search repo cilium` shows chart |
| D2 | cert-manager Helm chart mirrored | `helm search repo cert-manager` shows chart |
| D3 | MetalLB Helm chart mirrored | `helm search repo metallb` shows chart |
| D4 | CoreDNS Helm chart mirrored | `helm search repo coredns` shows chart |
| D5 | Chart provenance verified | `helm verify` passes |

## E. Phase 4: Kubespray deployment

| # | Item | VERIFY |
|---|------|--------|
| E1 | Kubespray release-2.32 checked out internally | `git -C kubespray/ log -1` shows v2.32.0 tag |
| E2 | kubespray/VERSION pinned to release-2.32 | `cat kubespray/VERSION` shows release-2.32 |
| E3 | Inventory created for target cluster | `inventory/<cluster>/hosts.ini` exists |
| E4 | group_vars match version-matrix.md | kube_version: v1.36.5, containerd: 2.3.7 |
| E5 | Offline variables configured (group_vars/all/offline.yml) | kube_image_repo points to harbor.internal |
| E6 | containerd registry mirrors configured | hosts.toml points to harbor.internal |
| E7 | `--check --diff` run on control-plane | `ansible-playbook cluster.yml --check --diff --limit control-plane` succeeds |
| E8 | Full deploy run on control-plane | `ansible-playbook cluster.yml -b --limit control-plane` succeeds |
| E9 | Full deploy run on workers | `ansible-playbook cluster.yml -b --limit k8s-node` succeeds |
| E10 | All nodes Ready | `kubectl get nodes` shows all Ready |
| E11 | etcd cluster healthy | `etcdctl endpoint health --cluster` shows all healthy |
| E12 | API server reachable | `kubectl get --raw='/readyz?verbose'` returns all ok |

## F. Phase 5: CNI and add-ons

| # | Item | VERIFY |
|---|------|--------|
| F1 | Cilium installed from internal Helm repo | `kubectl -n kube-system get pods -l k8s-app=cilium` |
| F2 | Cilium kube-proxy replacement enabled | `cilium status` shows kube-proxy replacement |
| F3 | Hubble enabled | `cilium hubble status` shows healthy |
| F4 | CoreDNS deployed | `kubectl -n kube-system get pods -l k8s-app=kube-dns` |
| F5 | MetalLB deployed (if using external LB) | `kubectl -n metallb-system get pods` |
| F6 | Network policies applied | `kubectl get networkpolicy -A` |

## G. Phase 6: Platform services

| # | Item | VERIFY |
|---|------|--------|
| G1 | Vault deployed and unsealed | `vault status` shows unsealed |
| G2 | Keycloak deployed | `kubectl -n keycloak get pods` |
| G3 | Argo CD deployed | `kubectl -n argocd get pods` |
| G4 | Harbor deployed | `kubectl -n harbor get pods` |
| G5 | Rancher deployed (management cluster only) | `kubectl -n cattle-system get pods` |
| G6 | Monitoring deployed | `kubectl -n monitoring get pods` |

## H. Phase 7: Validation

| # | Item | VERIFY |
|---|------|--------|
| H1 | Pods can resolve DNS | `kubectl run test --rm -i --tty --image=harbor.internal/tools/dnstools -- dig kubernetes.default.svc.cluster.local +short` |
| H2 | Pods can reach external services (if configured) | `curl -sf https://kubernetes.default.svc.cluster.local` |
| H3 | Ingress works | `curl -sf https://<ingress-url>/healthz` |
| H4 | Storage provisioning works | PVC binds to Ceph RBD/CephFS |
| H5 | Backup works | `etcdctl snapshot save /tmp/test.db` succeeds |
| H6 | Restore works | `etcdctl snapshot status /tmp/test.db` shows healthy |

## I. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Platform Engineer | | | |
| Security Engineer | | | |
| SRE | | | |

## J. Cross-references

- `kubespray/kubespray-deployment.md` §F — Offline image configuration
- `kubespray/kubespray-deployment.md` §G — Deployment execution
- `kubespray/kubespray-deployment.md` §M — Best practices
- `offline-artifacts/artifact-matrix.md` — Complete artifact inventory
- `offline-artifacts/nexus-harbor-integration.md` — Nexus/Harbor integration
- `compatibility/version-matrix.md` — Version pins
- `kubespray/multi-version-support.md` — Release directory structure
