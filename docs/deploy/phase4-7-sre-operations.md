# Phase 4-7 — SRE Operational Guides

**Purpose**: Site reliability engineering operational procedures for the cloud-native platform, covering Observability (Steps 31-33), Scaling & Expansion (Steps 34-37), Maintenance (Step 38), and Troubleshooting (Step 39). All procedures follow the prerequisites→actions→validation→navigation pattern of this step-by-step guide.

**Entry criteria**:
- Step 30 complete (storage validation exit criteria pass).
- Phase 1 (cluster foundation) complete: Kubernetes cluster provisioned with Kubespray, Cilium CNI, NGINX ingress reachable.
- Phase 2 (management layer) complete: Rancher, Argo CD, Keycloak OIDC, Vault deployed and integrated.
- Phase 3 (storage lifecycle) complete: Ceph/Rook-Ceph storage deployed and validated.
- All nodes have OS installed per Step 00 and containerd 2.3.7 from internal mirror.

**Exit criteria**:
- All 10 steps complete and reviewed.
- Validation commands produce expected healthy state.
- Post-deployment SLO check passes (error budget within target).
- Rollback procedures documented and the team has exercised at least one recovery in a non-production context.

---

<a id="step-31"></a>
## Step 31 — Observability: Prometheus Operator, node-exporter, kube-state-metrics, cAdvisor

**Purpose**: Install the metrics foundation (Prometheus Operator stack) and verify every scrape target reports healthy.

**Prerequisites**:
- Step 30 complete (storage validation exit criteria pass).
- Kubernetes cluster reachable via `kubectl`.
- Helm chart `kube-prometheus-stack` mirrored to `harbor.internal/charts/`.

**Actions**:

```bash
# Create the monitoring namespace
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

# Install Prometheus Operator stack from internal Helm chart
helm upgrade --install kube-prometheus-stack harbor.internal/charts/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f monitoring/prometheus-values.yaml
```

**Validation**:

```bash
# All monitoring pods Running with 0 restarts
kubectl -n monitoring get pods

# Every scrape target reports health: "up"
curl -s http://localhost:9090/api/v1/targets | \
  jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# kube-state-metrics returns data
curl -s "http://localhost:9090/api/v1/query?query=kube_deployment_status_replicas" | \
  python3 -m json.tool

# cAdvisor container metrics present
curl -s "http://localhost:9090/api/v1/query?query=container_memory_usage_bytes" | \
  python3 -m json.tool
```

# Expected: all targets report `health: "up"`; both queries return numeric values, not empty results.

**Navigation**:
- Previous: Step 30 (anchor `#step-30`)
- Next: Step 32 (anchor `#step-32`)

---

<a id="step-32"></a>
## Step 32 — Observability: Grafana dashboards, Loki + Promtail, Alertmanager routing

**Purpose**: Deploy dashboards as code via Argo CD, aggregate logs with Loki + Promtail, and route alerts to PagerDuty/Slack.

**Prerequisites**:
- Step 31 complete (Prometheus targets all healthy).
- Grafana provisioning files stored in the `obs-monitoring` GitLab project under `dashboards/`.
- Alertmanager configuration stored in Git and applied by Argo CD.

**Actions**:

```bash
# Install Loki
helm upgrade --install loki grafana/loki \
  --namespace monitoring \
  --create-namespace \
  -f loki-values.yaml

# Verify Loki and Promtail pods
kubectl -n monitoring get pods -l app=loki
kubectl -n monitoring get pods -l app=promtail

# Test Loki query via port-forward
kubectl -n monitoring port-forward svc/loki 3100:3100 &
curl -s "http://localhost:3100/loki/api/v1/query?query={job=\"promtail\"} | json"
```

**Validation**:

```bash
# Grafana application synced via Argo CD
kubectl -n argocd wait application mgmt-grafana --for=condition=Healthy --timeout=300s

# Grafana dashboard provisioned
kubectl -n monitoring get grafanadashboard node-metrics -o jsonpath='{.metadata.name}'

# Alertmanager config validates
amtool validate config alertmanager.yml
kubectl -n monitoring get svc alertmanager
```

# Expected: Argo CD application Healthy; dashboard name returned; Alertmanager config valid.

**Navigation**:
- Previous: Step 31 (anchor `#step-31`)
- Next: Step 33 (anchor `#step-33`)

---

<a id="step-33"></a>
## Step 33 — Observability: Alert rules validation

**Purpose**: Validate that required alert rules are loaded into Prometheus and expressions resolve.

**Prerequisites**:
- Step 32 complete (Alertmanager routing configured).
- Alert rule YAML files stored under `monitoring/rules/`.

**Actions**:

```bash
# Validate rules in CI/local
promtool check rules /path/to/prometheus-rules.yml

# Verify rules are loaded
kubectl -n monitoring get prometheusrules

# Test a specific alert expression
curl -s http://localhost:9090/api/v1/query?query='up{job="node-exporter"}'
```

**Validation**:

```bash
# Required alert coverage — each must return data or evaluate without error
for alert in APIServerDown NodeNotReady etcdNoLeader NodeMemoryPressure CephHealthError CephPoolNearFull CertificateExpiringSoon; do
  echo "=== $alert ==="
  curl -s "http://localhost:9090/api/v1/query?query=$alert" | python3 -m json.tool | head -5
done
```

# Expected: `promtool check rules` passes; all `prometheusrules` present; each alert query evaluates without error.

**Navigation**:
- Previous: Step 32 (anchor `#step-32`)
- Next: Step 34 (anchor `#step-34`)

---

<a id="step-34"></a>
## Step 34 — Scaling & Expansion: Add worker node

**Purpose**: Add a worker node to the cluster with post-deployment SLO validation.

**Prerequisites**:
- Step 33 complete (alert rules validated).
- New node OS installed per Step 00, containerd 2.3.7 from internal mirror, SSH access, NTP synchronized.
- `inventory/<cluster>/hosts.ini` writable.

**Actions**:

```bash
# Add node to inventory under [k8s-node]
cat >> inventory/<cluster>/hosts.ini << 'EOF'
k8s-w-4 ansible_host=10.20.0.24 ip=10.20.0.24
EOF

# Run Kubespray limited to the new worker
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-w-4
```

**Validation**:

```bash
# New node Ready
kubectl get nodes k8s-w-4

# Post-deployment SLO validation
kubectl get pods -o wide --field-selector spec.nodeName=k8s-w-4

# Error budget within target
curl -s http://localhost:9090/api/v1/query?query='sum(rate(job:requests:errors_total[5m])) / sum(rate(job:requests:total_requests[5m]))'
```

# Expected: `k8s-w-4` shows `Ready`; all pods scheduled to it Running; error budget within SLO target.

**Navigation**:
- Previous: Step 33 (anchor `#step-33`)
- Next: Step 35 (anchor `#step-35`)

---

<a id="step-35"></a>
## Step 35 — Scaling & Expansion: Add control-plane node

**Purpose**: Add a control-plane node one at a time while preserving etcd quorum.

**Prerequisites**:
- Step 34 complete (worker node added and validated).
- Current control-plane quorum healthy (3 of 3 or 2 of 3).
- New node OS installed per Step 00, etcd data directory on local SSD/NVMe.

**Actions**:

```bash
# Add node to inventory under [control-plane] and [etcd]
cat >> inventory/<cluster>/hosts.ini << 'EOF'
k8s-cp-4 ansible_host=10.20.0.14 ip=10.20.0.14
EOF

# Run Kubespray one control-plane node at a time
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-4
```

**Validation**:

```bash
# New control-plane node Ready
kubectl get nodes k8s-cp-4

# etcd quorum healthy on new node
kubectl -n kube-system get pods -l component=etcd --field-selector spec.nodeName=k8s-cp-4
kubectl -n kube-system exec etcd-k8s-cp-4 -- etcdctl endpoint health --cluster
```

# Expected: `k8s-cp-4` Ready; etcd endpoint health shows all members healthy.

**Navigation**:
- Previous: Step 34 (anchor `#step-34`)
- Next: Step 36 (anchor `#step-36`)

---

<a id="step-36"></a>
## Step 36 — Scaling & Expansion: Add GPU node

**Purpose**: Add a GPU worker node with NVIDIA driver and verify `nvidia-smi` from a pod.

**Prerequisites**:
- Step 35 complete (control-plane node added and validated).
- GPU node hardware with NVIDIA GPU installed.
- NVIDIA driver DaemonSet image mirrored to internal registry.

**Actions**:

```bash
# Create gpu-node group in inventory
cat >> inventory/<cluster>/hosts.ini << 'EOF'
[gpu-node]
k8s-gpu-1 ansible_host=10.50.0.11 ip=10.50.0.11 labels='{"accelerator":"nvidia"}'
EOF

# Deploy NVIDIA device plugin DaemonSet
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Label GPU node
kubectl label node k8s-gpu-1 nvidia.com/gpu.count=1 nvidia.com/gpu.type=H100
```

**Validation**:

```bash
# GPU visible from a test pod
kubectl run nvidia-test --rm -it --restart=Never --image=nvidia/cuda -- nvidia-smi

# Node labeled correctly
kubectl get nodes -l nvidia.com/gpu.count=1
```

# Expected: `nvidia-smi` displays GPU information; node shows the GPU label.

**Navigation**:
- Previous: Step 35 (anchor `#step-35`)
- Next: Step 37 (anchor `#step-37`)

---

<a id="step-37"></a>
## Step 37 — Scaling & Expansion: Add Ceph OSD

**Purpose**: Add a Ceph OSD when cluster capacity headroom drops below 85%.

**Prerequisites**:
- Step 36 complete (GPU node added and validated).
- Ceph cluster healthy (`ceph -s` shows HEALTH_OK).
- New data disk ready on a Ceph host.

**Actions**:

```bash
# Verify capacity headroom before adding
ceph df
# Ensure: used / total < 0.85 (CephPoolNearFull alert threshold)

# List available devices
cephadm shell -- ceph orch device ls

# Create OSD on the new disk
cephadm shell -- ceph orch apply osd <host> --data-devices /dev/sdb --db-devices /dev/nvme1n1
```

**Validation**:

```bash
# New OSD appears and is up/in
ceph osd tree
ceph -s

# All PGs active+clean
ceph pg stat
```

# Expected: new OSD in `up`+`in` state; `ceph -s` HEALTH_OK; all PGs `active+clean`.

**Navigation**:
- Previous: Step 36 (anchor `#step-36`)
- Next: Step 38 (anchor `#step-38`)

---

<a id="step-38"></a>
## Step 38 — Maintenance: OS patching, kernel updates, cert rotation, kubespray upgrades

**Purpose**: Perform routine maintenance: OS patching, kernel updates, certificate rotation, and Kubespray upgrades — one node at a time.

**Prerequisites**:
- Step 37 complete (Ceph OSD added and validated).
- Pre-maintenance health check passed (all nodes Ready, disk < 80%, memory < 90%, cert expiry > 30 days).
- etcd snapshot taken before any Kubespray upgrade.

**Actions**:

```bash
# Pre-maintenance health check (6 concrete checks)
kubectl get nodes                          # all Ready
kubectl get --raw='/readyz?verbose'        # all ok
openssl x509 -noout -dates -enddate <cert> # expiry > 30d
ssh <node> "df -h /var/lib/kubelet/pods"   # disk < 80%
kubectl top nodes                          # memory < 90%
kubectl get certificaterequest -A          # no pending failures
```

**OS patching — Oracle Linux 9**:

```bash
# One node at a time
sudo dnf clean all
sudo dnf upgrade --refresh -y
sudo reboot
uname -r
kubectl get nodes
```

**OS patching — Ubuntu 22.04 LTS**:

```bash
sudo apt-get update
sudo apt-get install -y update-manager-core
sudo do-release-upgrade -d
# Follow prompts; reboot when complete
```

**Certificate rotation** (intermediate CA every 180 days; leaf certs renewed by cert-manager):

```bash
# Manual renewal fallback if cert-manager hasn't auto-renewed within 7 days of expiry
kubectl cert-manager renew <certname>

# Verify
openssl s_client -connect <api-host>:6443 -servername <api-host>
kubectl get secret <secret> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates
```

**Kubespray upgrade** (never all control-plane nodes simultaneously):

```bash
# 1. etcd snapshot
# 2. Upgrade control-plane nodes one at a time
ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml -b --limit k8s-cp-1
# 3. Upgrade worker nodes one at a time (drain, run cluster.yml --limit, uncordon)
# 4. Post-upgrade verification
kubectl get nodes -o wide
# 5. Update kubespray/VERSION and group vars in Git
```

**Validation**:

```bash
# All nodes Ready after maintenance
kubectl get nodes -o wide

# No pod restarts from maintenance
kubectl get pods -A | grep -v Running | grep -v Completed

# Cert expiry > 30 days
kubectl get certificaterequest -A
```

# Expected: all nodes Ready; no unexpected pod restarts; certificates valid > 30 days.

**Navigation**:
- Previous: Step 37 (anchor `#step-37`)
- Next: Step 39 (anchor `#step-39`)

---

<a id="step-39"></a>
## Step 39 — Troubleshooting: Top 10 issues as numbered procedures

**Purpose**: Diagnose and remediate the most frequent platform issues using numbered steps (diagnose → root-cause → remediation → verify → rollback).

**Prerequisites**:
- Step 38 complete (maintenance procedures validated).
- `kubectl`, `cilium`, `etcdctl`, `vault`, `amtool` available.

**Actions** — Node NotReady:
```bash
# 1. Diagnose
kubectl describe node <node>
kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'
journalctl -u kubelet -f

# 2. Remediation
kubectl cordon <node>
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
systemctl restart kubelet

# 3. Verify
kubectl get nodes <node>  # Ready
kubectl get pods -o wide --field-selector spec.nodeName=<node>  # rescheduled
```

**Actions** — kubelet failure:
```bash
systemctl status kubelet
journalctl -u kubelet --no-pager -n 50
# Renew certs if expired (Step 38), then:
systemctl restart kubelet
```

**Actions** — CNI failure:
```bash
cilium status --verbose
cilium connectivity test
# Fix MTU if needed:
#   set ipv4.mtu: 1450 in Cilium values, then helm upgrade
```

**Actions** — DNS problems:
```bash
kubectl run nettest --rm -it --restart=Never --image=busybox -- nslookup kubernetes.default.svc.cluster.local
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system logs -l k8s-app=kube-dns
# Add DNS egress NetworkPolicy (UDP 53) if blocked
```

**Actions** — Certificate problems:
```bash
openssl x509 -noout -dates -enddate <cert>
kubectl cert-manager renew <cert>
kubectl auth can-i --list
openssl s_client -connect <api>:6443
```

**Actions** — Disk pressure:
```bash
ssh <node> "df -h"
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
journalctl --vacuum-time=2d
```

**Actions** — Memory pressure:
```bash
kubectl top nodes
kubectl drain <node> --ignore-daemonsets
kubectl get pods --all-namespaces --sort-by=.status.containerStatuses[0].restartCount
```

**Actions** — Stuck terminating pods:
```bash
kubectl get pods <pod> -o jsonpath='{.status.terminationMessage}'
kubectl patch pod <pod> -p '{"metadata":{"finalizers":[]}}' --type=merge
kubectl delete pod <pod> --grace-period=0 --force
```

**Actions** — Scheduling failures:
```bash
kubectl describe pod <pod> -o yaml
kubectl get nodes -o jsonpath='{.items[*].status.allocatable}'
# Add node (Step 34) or fix taints/affinity
```

**Actions** — Node registration failures:
```bash
kubectl get nodes <new-node> --ignore-not-found
journalctl -u kubelet -k
kubectl delete node <old-name>
kubectl reset node <new-name>
# Re-add node per Step 34
```

**Validation**:

```bash
# After any remediation:
kubectl get nodes        # all Ready
kubectl get pods -A      # no CrashLoopBackoff, no stuck Terminating
cilium connectivity test # all pass (if CNI-related)
```

# Expected: all nodes Ready; no stuck pods; CNI/DNS healthy after remediation.

**Navigation**:
- Previous: Step 38 (anchor `#step-38`)
- Next: Step 40 (anchor `#step-40`)

---

<a id="step-40"></a>
## Step 40 — SRE exit criteria and rollback procedures

**Purpose**: Confirm the SRE operational phase is complete and document rollback for failed maintenance.

**Prerequisites**:
- Step 39 complete (troubleshooting procedures validated).
- All steps 31-39 reviewed.

**Actions**:

```bash
# Final SLO check
curl -s "http://localhost:9090/api/v1/query?query=sum(rate(job:requests:errors_total[5m])) / sum(rate(job:requests:total_requests[5m]))"

# Error budget status
# Phrase: "Error budget is X% consumed with Y% of the window remaining — within SLO"

# Disaster recovery drill record (quarterly)
#   Velero restore one app + checksums
#   Annual drill: full rebuild per docs/lifecycle/disaster-recovery/index.md
```

**Validation**:

```bash
# All 10 SRE steps verified:
kubectl get nodes -o wide              # all Ready
kubectl get --raw='/readyz?verbose'    # all ok
kubectl get pods -A | grep -c CrashLoopBackOff  # 0
kubectl get --raw='/livez'             # API server responsive
```

# Expected: all nodes Ready; readyz all ok; zero CrashLoopBackOff pods; API server live.

**Rollback procedures**:

- **Failed OS patch**: reboot to previous kernel/GRUB entry; re-run patch on remaining nodes one at a time.
- **Failed Kubespray upgrade**: restore etcd snapshot, revert group vars, re-run Kubespray on affected node.
- **Failed cert rotation**: revert to previous certificate from backup; restart affected services.
- **Failed scaling**: remove the added node (cordon, drain, remove from inventory, run Kubespray removal).
- **Failed observability change**: `helm uninstall <component> -n monitoring`; redeploy from previous values snapshot.

**Navigation**:
- Previous: Step 39 (anchor `#step-39`)
- Next: Return to main guide index (`index.md`)

---

**End of Phase 4-7 — SRE Operational Guides (Steps 31-40)**
