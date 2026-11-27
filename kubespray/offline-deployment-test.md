# Offline Deployment Test Procedure



[Previous step](../storage/ceph/cephadm-deployment.md) | [Next step](../management-cluster/rancher/rancher.md)



---



## A. Purpose and scope



**Offline deployment test** = Verified end-to-end procedure for deploying Kubespray/Kubernetes in an air-gapped environment with no external egress. This procedure validates that all required artifacts (container images, OS packages, Helm charts, binaries) are properly mirrored and that the bootstrap process completes successfully without any external network connections.



**Air-gapped** = zero egress from any node at any stage. All artifacts are mirrored to internal infrastructure before any node is installed.



Cross-references: `kubespray/kubespray-deployment.md` §F (Offline image configuration), `offline-artifacts/artifact-matrix.md`, `offline-artifacts/nexus-harbor-integration.md`, `compatibility/version-matrix.md`.



## B. Test prerequisites



| # | Item | VERIFY |

|---|------|--------|

| B1 | Air-gapped test environment isolated from external networks | `ping -c 3 external.domain.com` fails or times out |

| B2 | Internal container registry reachable | `skopeo inspect docker://registry.internal:5000/kubespray:v2.32.0` succeeds |

| B3 | Internal OS package repository reachable | `dnf repolist` or `apt-cache policy` shows internal repos |

| B4 | Internal Helm repository reachable | `helm repo add internal https://chartmuseum.internal` and `helm search repo cilium` succeeds |

| B5 | Mirror directory populated with all artifacts | See artifact-matrix.md for complete inventory |

| B6 | Bootstrap validation scripts available | `ls kubespray/offline-bootstrap.sh` exists |



## C. Phase 1: Image mirroring validation



| # | Item | VERIFY |

|---|------|--------|

| C1 | Kubespray container image mirrored | `skopeo inspect docker://registry.internal:5000/kubespray/kubespray:v2.32.0` returns digest |

| C2 | Kubernetes control plane images mirrored | `skopeo inspect docker://registry.internal:5000/k8s/kube-apiserver:v1.36.5` returns digest |

| C3 | etcd image mirrored | `skopeo inspect docker://registry.internal:5000/k8s/etcd:3.6.15` returns digest |

| C4 | CNI plugin images mirrored (Cilium) | `skopeo inspect docker://registry.internal:5000/cilium/cilium:v1.20.3` returns digest |

| C5 | containerd shim image mirrored | `skopeo inspect docker://registry.internal:5000/k8s/containerd:v2.3.7` returns digest |

| C6 | All images in version-matrix.md mirrored | Check each row's internal destination matches |

| C7 | Image digests recorded | `skopeo inspect --raw` digest matches artifact-matrix.md records |



## D. Phase 2: OS package mirroring validation



| # | Item | VERIFY |

|---|------|--------|

| D1 | OS package repository configured on all nodes | `dnf repolist` shows internal baseos/appstream repos (OL9) or `apt-cache policy` shows internal mirrors (Ubuntu 24.04) |

| D2 | containerd package installed from internal repo | `containerd --version` shows 2.3.7 |

| D3 | kubectl, kubeadm, kubelet binaries fetched from internal server | `kubectl version --client` shows v1.36.5 without external download |

| D4 | Helm binary fetched from internal server | `helm version` shows v3.22.0 |

| D5 | OS-specific packages (nfs-kernel-server, conntrack, etc.) from internal mirror | `rpm -qa` or `dpkg -l` shows internal package versions |



## E. Phase 3: Helm chart mirroring validation



| # | Item | VERIFY |

|---|------|--------|

| E1 | Cilium Helm chart mirrored to internal repo | `helm search repo cilium` shows chart from internal registry |

| E2 | cert-manager Helm chart mirrored | `helm search repo cert-manager` shows chart from internal registry |

| E3 | MetalLB Helm chart mirrored | `helm search repo metallb` shows chart from internal registry |

| E4 | CoreDNS Helm chart mirrored | `helm search repo coredns` shows chart from internal registry |

| E5 | Chart provenance verified | `helm verify <chart>` passes for all mirrored charts |



## F. Phase 4: Bootstrap validation (air-gapped deploy)



| # | Item | VERIFY |

|---|------|--------|

| F1 | Kubespray inventory uses internal image repo | `grep kube_image_repo kubespray/inventory/<cluster>/group_vars/all/offline.yml` points to `registry.internal:5000` |

| F2 | containerd registry mirrors configured | `cat /etc/containerd/config.toml` shows mirrors to `registry.internal:5000` |

| F3 | Kubeadm/kubespray pre-check passes | `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml --syntax-check` succeeds |

| F4 | Control-plane nodes bootstrap successfully | `kubectl get nodes` shows control-plane Ready after `ansible-playbook cluster.yml -b --limit control-plane` |

| F5 | Worker nodes join cluster | `kubectl get nodes` shows all workers Ready after full deploy |

| F6 | etcd cluster healthy | `etcdctl endpoint health --cluster --endpoints=https://127.0.0.1:2379` shows all healthy |

| F7 | API server reachable and responding | `kubectl get --raw='/readyz?verbose'` returns all ok |

| F8 | DNS resolves from within cluster | `kubectl run test-dns --rm -i --tty --image=harbor.internal/tools/dnstools -- dig kubernetes.default.svc.cluster.local +short` returns IP |

| F9 | Cluster operates without external egress | `tcpdump -i any -n -t port 80 or port 443 or port 8080` captures zero outbound connections during bootstrap |



## G. Phase 5: Post-deployment validation



| # | Item | VERIFY |

|---|------|--------|

| G1 | All expected add-ons deployed | `kubectl -n kube-system get pods` shows cilium, coredns, metallb, cert-manager |

| G2 | Storage provisioning works (if Ceph/RBD configured) | PVC binds to Ceph RBD volume |

| G3 | Network policies apply correctly | `kubectl get networkpolicy -A` shows expected policies |

| G4 | Ingress gateway responds | `curl -sf https://<ingress-url>/healthz` returns 200 |

| G5 | Telemetry/monitoring operational | `kubectl -n monitoring get pods` shows expected components |



## H. Sign-off



| Role | Name | Date | Notes |

|------|------|------|-------|

| Platform Engineer | | | Offline deployment test completed |

| Security Engineer | | | No external egress detected during test |

| SRE | | | Bootstrap validated; cluster operational |



## I. Cross-references



- `kubespray/kubespray-deployment.md` §F — Offline image configuration

- `kubespray/kubespray-deployment.md` §G — Deployment execution

- `kubespray/kubespray-deployment.md` §M — Best practices

- `offline-artifacts/artifact-matrix.md` — Complete artifact inventory

- `offline-artifacts/nexus-harbor-integration.md` — Nexus/Harbor integration

- `compatibility/version-matrix.md` — Version pins

- `kubespray/multi-version-support.md` — Release directory structure



---
