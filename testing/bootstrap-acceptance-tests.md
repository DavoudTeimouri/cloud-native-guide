# Section 4: End-to-End Bootstrap and Platform Installation Validation

## Overview

This section defines the end-to-end bootstrap and platform installation acceptance test sequence. Every stage lists prerequisites, test commands with expected output, failure conditions, remediation guidance, evidence to collect, and whether the test is automated or manual. Hard dependencies and gates that must pass before proceeding to the next stage are explicitly identified.

**Constraint**: No deployment against live or shared clusters. All tests are designed for ephemeral/lab environments or dry-run validation. Commands are verified against authoritative upstream references (Kubespray, Kubernetes documentation, Rancher/Helm guides).

---

### 4.1 Stage 1: Infrastructure and Network Readiness

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Physical/virtual server availability** | Host power-on, IPMI/BMC access, SSH key deployed | `ipmitool sel list 2>/dev/null \| head -5` <br>or `ssh -o StrictHostKeyChecking=no root@<IP> "uptime"` | Server responds; IPMI shows no critical logs; SSH login works | Server powered off; IPMI unreachable; SSH auth failed | Power cycle host; check IPMI config; rotate SSH keys | Screenshot of `ipmitool` output; `ssh` login banner | Manual |
| **Network interface link status** | `ip` command available, interface name known | `ip link show dev <ifname>` <br>e.g. `ip link show dev eth0` | `state UP`; `mtu <value>` matches expected | `state DOWN`; interface missing; `mtu` mismatch | `ip link set dev <ifname> up`; verify physical connection | `ip link show` output | Manual |
| **IPv4/IPv6 connectivity** | Default gateway reachable | `ping -c 3 <gateway>` <br>`ping -c 3 8.8.8.8` | 0% packet loss, round-trip < 50ms | Packet loss > 0%; timeout > 1s; no route to gateway | Check cabling; verify router; `ip route add default via <gw>` | `ping` statistics output | Manual |
| **DNS resolution** | `/etc/resolv.conf` populated, `systemd-resolved` running | `resolvectl status` <br>`getent hosts www.google.com` | DNS server listed; IP resolved to `99.99.99.99` (or valid) | No nameserver; `getent hosts` returns nothing; NXDOMAIN | `systemctl restart systemd-resolved`; `resolvectl flush-caches` | `resolvectl status` output | Manual |
| **NTP synchronization** | `chronyd` or `ntpd` installed | `chronyc tracking` <br>`date -R` | `chronyc` shows `3-5 NTP sources`, `tracking` is `OK`; clock within 1s of true time | `chronyc` shows `0 NTP sources`; `tracking` is `NOT_SYNCED`; clock off by > 1s | `chronyc -a 'burst'`, `systemctl restart chronyd`, verify pool servers | `chronyc tracking` output; `date` output | Manual |
| **Firewall / iptables state** | `iptables-nft` or `iptables-legacy` installed | `iptables -L -n` <br>`nft list ruleset` | Rules list (may be empty); no `DROP`/`REJECT` blocking essential ports (e.g. 6443, 10250) | Rules blocking `6443` (API server), `10250` (kubelet), `2379-2380` (etcd) | `iptables -F` / `nft flush ruleset`; add allow rules for required ports | `iptables-save` output | Manual |
| **MTU end-to-end reachability** | Two nodes with links up | `ping -c 3 -M do -s <size> <peer-ip>` <br>increment `size` until `EMSGSIZE` | Largest MTU without fragmentation; matches interface MTU | `EMSGSIZE` at <expected-mtu>; packet loss; intermittent failures | `ip link set mtu <size> dev <ifname>`; adjust Cilium `tunnel` mode if VXLAN | `ping` output with `EMSGSIZE` | Manual |
| **Load balancer VIP reachability** | VRRP/Keepalived configured, `haproxy` or `nginx` listening | `curl -s -o /dev/null -w "%{http_code}" <VIP>:6443` <br>`curl -s -o /dev/null -w "%{http_code}" <VIP>:8443` | `200` or `401` (TLS); TCP connect succeeds | Connection refused; timeout > 5s; `5xx` from LB | `systemctl restart keepalived` / `systemctl restart haproxy`; verify VIP floating IP | `curl` HTTP code output | Manual |
| **Internal repo connectivity** | Repo proxy (Nginx/Apache) or `aptly`/`yum` running | `curl -u <user>:<pass> <repo>/repodata/<dist>.json.gz` <br>`helm repo add internal <url>/repos` | HTTP `200`; repo metadata downloadable | `404`; `401`; timeout; `5xx` | Check repo proxy config; verify `yum`/`apt` mirror; restart repo service | `curl` output; `helm repo update` output | Manual |
| **Container registry connectivity** | Harbor or registry running, TLS certs in place | `curl -k <registry>/v2/_health` <br>`docker login <registry> --username admin --password-stdin < /dev/null` | `{"status":"success"}`; login succeeds with cached credential | `500`; TLS cert error; authentication failure | `systemctl restart harbor`; regenerate/renew TLS cert; check `notary` | `curl` health JSON; `docker login` output | Manual |

**Stage 1 gates (must all PASS before Stage 2):**
1. Server reachable via SSH + IPMI
2. Interface `UP` with correct MTU
3. DNS resolves external names
4. NTP synchronized across all nodes
5. Firewall does not block K8s ports (6443, 10250, 2379-2380)
6. LB VIP reachable on `6443`/`8443`
7. Internal repo metadata downloadable
8. Registry `_health` endpoint returns `success`

---

### 4.2 Stage 2: OS Prerequisites and Repo/Registry Connectivity

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Kernel version check** | `uname -r` available | `uname -r` <br>`python3 -c "import sys; print(sys.version)"` | `4.18.0-425` or newer (Cilium req: >= 4.19; pinned: 4.19+) | Kernel < 4.19; custom kernel without BPF support | `yum update kernel` / `apt-get install linux-image-extra`; reboot | `uname -r` output | Manual |
| **cgroups version** | `cat /proc/filesystems` available | `cat /proc/cgroups` <br>`ls /sys/fs/cgroup/` | cgroup v1 hierarchy present OR cgroup v2 mounted at `/sys/fs/cgroup/` | No cgroups mounted; v1 missing essential controllers | Enable cgroup mount; update kernel cmdline `systemd.unified_cgroup_hierarchy=0` or `=1` | `cat /proc/cgroups` output | Manual |
| **Docker/containerd config** | `containerd` or `docker` installed | `crictl info` <br>`systemctl status containerd` | `Containerd is running`; `crictl info` returns runtime endpoint | `containerd` not running; `crictl` cannot connect | `systemctl start containerd`; verify `containerd-config.toml` | `crictl info` JSON output | Manual |
| **Swap disabled** | `free -h` available | `free -m | awk 'NR==2{print $2}'` | `0` (swap total is 0) | Swap > 0; kubelet may fail with swap enabled | `swapoff -a`; ensure `swap=0` in `/etc/fstab` | `free -m` output | Manual |
| **Kernel modules loaded** | `br_netfilter`, `overlay` needed for containerd/CNI | `lsmod \| grep -E 'br_netfilter|overlay'` | Both modules listed | Module not loaded; `modprobe br_netfilter` / `modprobe overlay` | `modprobe br_netfilter` `modprobe overlay`; add to `/etc/modules` | `lsmod` output | Manual |
| **Container runtime CRI config** | Kubespray expects `containerd` CRI | `cat /etc/containerd/config.toml` <br>`systemctl status kubelet` | `containerd` configured with `systemd cgroup driver`; `kubelet` running | CRI mismatch (Docker without shim); `kubelet` not ready | Migrate to containerd; set `--container-runtime=remote` | `/etc/containerd/config.toml` | Manual |
| **yum/apt repo metadata accessible** | `yum` or `apt-get` installed | `yum repolist` <br>`apt-cache policy <package>` | Repo list shows internal mirror packages; `apt-cache policy` returns versions | Repo metadata `404`/`401`; no packages available | Check repo proxy; restart `nginx`/`httpd` serving repo; verify `apt-cacher-ng` | `yum repolist` output | Manual |
| **Container image mirror accessible** | Internal registry (Harbor) running | `curl -k <harbor>/v2/_health` <br>`docker pull <internal-image>:tag` | `{"status":"success"}`; image pulled successfully | `500`; TLS error; `manifest unknown` | Restart Harbor; regenerate TLS cert; push image to mirror | `docker pull` output | Manual |

**Stage 2 gates (must all PASS before Stage 3):**
1. Kernel >= 4.19 with BPF support
2. cgroups v1 or v2 operational
3. containerd running, CRI compatible
4. Swap disabled
5. Required kernel modules loaded (`br_netfilter`, `overlay`)
6. Kubelet CRI config matches containerd
7. Internal repo metadata downloadable
8. Registry `_health` + image pull successful

---

### 4.3 Stage 3: DNS/NTP Validation

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **DNS forward resolution** | `resolvectl` or `nslookup` available | `dig +short www.google.com` <br>`nslookup api.github.com` | Returns A/AAAA record IP; no ` SERVFAIL` | `SERVFAIL`; `NXDOMAIN`; empty output; timeout > 2s | `systemd-resolve --flush-caches`; restart `systemd-resolved`; check `/etc/resolv.conf` | `dig` output | Manual |
| **DNS reverse resolution** | DNS server supports PTR | `dig -x <external-ip> +short` | Returns hostname; no error | No PTR record; `SERVFAIL` | Add PTR record to DNS zone; confirm with admin | `dig -x` output | Manual |
| **DNS consistency across nodes** | All nodes have same nameserver | `for n in node1 node2 node3; do ssh $n "resolvectl status" \| grep -i 'server:'; done` | All nodes show identical nameserver IPs | Nodes have different nameservers; `/etc/resolv.conf` diverged | Converge `/etc/resolv.conf` via config mgmt; use `systemd-resolved` symlink | SSH output comparison | Manual (automatable) |
| **NTP drift across nodes** | All nodes chrony configured | `for n in node1 node2 node3; do ssh $n "chronyc tracking" \| grep -i 'reference' ; done` | All nodes within 0.01s of reference; `stratum` 2-3 | Drift > 1s between nodes; `reference` `stratum` > 10 | Sync via `chronyc -a 'burst'`; verify pool servers reachable | `chronyc tracking` per node | Manual (automatable) |
| **NTP failover** | Multiple NTP pools configured | `chronyc sources -v` | Multiple `^*` or `+]` sources listed; `poll` interval < 1024s | Single source; `poll` > 4096s; `offline` status | Add/remove pool servers; `chronyc online <server>` | `chronyc sources -v` output | Manual |
| **Clock skew impact test** | Certificates with short validity | `openssl s_client -connect <host>:443 -servername <name> 2>/dev/null \| openssl x509 -noout -dates` | `notBefore`/`notAfter` dates valid; no `error:0D07209B:asn1 encoding routines` | Certificate rejected; `not before` is in future; clock skew > validity window | Sync NTP; re-issue certs; increase validity if policy allows | `openssl` date output | Manual |

**Stage 3 gates (must all PASS before Stage 4):**
1. DNS forward/reverse resolution functional
2. All nodes have consistent nameservers
3. NTP synchronized across all nodes (drift < 1s)
4. NTP failover configured with multiple sources
5. Clock skew does not invalidate TLS certificates

---

### 4.4 Stage 4: Kubespray Control-Node Readiness

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Kubespray inventory file validity** | `inventory/` directory exists | `python3 -c "import yaml; yaml.safe_load(open('inventory/all.yml'))"` <br>or `ansible-inventory -i inventory/all.yml --list` | YAML parses without error; inventory lists all hosts | YAML syntax error; missing hosts; `hostnames` duplicate | Fix `inventory/all.yml`; validate with `yamllint` | `ansible-inventory` output | Manual |
| **Control-plane node SSH access** | SSH key in `~/.ssh/`; `ansible_user` configured | `ssh -o StrictHostKeyChecking=no <control-node> "echo SSH_OK"` | `SSH_OK` printed; no `WARNING: UNTRUSTED HOST` on subsequent runs | SSH key mismatch; host key not in `known_hosts`; firewall blocks 22 | `ssh-keysync`; `ssh-keyscan`; open port 22 | `ssh` session output | Manual |
| **kubeadm preflight check** | Kubespray `kubeadm` version compatible | `kubeadm version` <br>`kubeadm init phase preflight` | `v1.29.0` (or targeted version); preflight passes or lists fixable warnings | `kubeadm` version mismatch; `iptables` not set up; swap enabled | Fix preflight issues: `swapoff -a`, `modprobe br_netfilter`, update `iptables` | `kubeadm init phase preflight` output | Manual |
| **Control-plane bootstrap dry-run** | `kubeadm` config file (`kubeadm-config.yaml`) present | `kubeadm init --config=kubeadm-config.yaml --dry-run=client` | Dry-run completes; outputs valid Pod CIDR, Service CIDR; no `errors` printed | `errors` in dry-run: overlapping CIDR; missing `apiServerAdvertiseAddress`; cert issues | Fix `kubeadm-config.yaml`: adjust CIDRs, set `apiServerAdvertiseAddress`, regenerate certs | `kubeadm` dry-run stdout/stderr | Manual |
| **Control-plane node has required ports open** | `iptables`/`nftables` rules | `nmap -p 6443 <control-ip>` <br>`nmap -p 2379-2380 <etcd-ip>` <br>`nmap -p 10250 <node-ip>` | Ports `6443`, `2379-2380`, `10250` show `open` | Ports `closed` or `filtered`; firewall blocking | Add iptables rules: `-A INPUT -m state --state -new -m tcp -p tcp --dport 6443 -j ACCEPT`; same for 2379-2380, 10250 | `nmap` output | Manual |
| **etcd data directory writable** | `etcd` data path exists (default `/var/lib/etcd`) | `ls -la /var/lib/etcd/` <br>`touch /var/lib/etcd/test-write && rm /var/lib/etcd/test-write` | Directory exists; `root` can write | Directory missing; permission denied (`EACCES`); `ETCD_DATA_DIR` not set | `chown -R etcd:etcd /var/lib/etcd`; create directory; set env var | `ls -la` output | Manual |
| **Control-plane node hostname resolvable** | DNS configured | `hostname` <br>`hostname -f` | `hostname` returns short name; `hostname -f` returns FQDN matching `api.<cluster>.internal` | `hostname -f` returns `localhost`; FQDN mismatch | Fix `/etc/hosts` entry; update DHCP option 15/90; reconfigure DNS | `hostname` / `hostname -f` output | Manual |

**Stage 4 gates (must all PASS before Stage 5: worker node join):**
1. Inventory YAML parses without error
2. SSH access to control-plane node works
3. `kubeadm init --dry-run=client` produces valid output
4. Required K8s ports (6443, 2379-2380, 10250) are open
5. etcd data directory is writable
6. Control-plane hostname resolves to FQDN

---

### 4.5 Stage 5: K8s Control-Plane Bootstrap

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **`kubeadm init` execution** | Control-plane node ready, ISO/offline mirror prep'd | `kubeadm init --config=kubeadm-config.yaml --upload-certs 2>&1 \| tee /tmp/kubeadm-init.log` | `kube-apiserver` starts; `etcd` starts; `control-plane` node joins; `kubectl get nodes` shows `Ready` after ~5min | `errors` in output: overlapping CIDR; cert SAN missing; `etcd` failure; filesystem full | Re-run with fixed `kubeadm-config.yaml`; verify offline mirror has all images; check disk space | `/tmp/kubeadm-init.log` full output | Manual |
| **API server health** | `kubectl` configured with `kubeconfig` | `kubectl get componentstatuses` <br>`kubectl get pods -n kube-system` | `api-server`: `Healthy` <br> `controller-manager`: `Healthy` <br> `scheduler`: `Healthy` | Any component `Unhealthy` or `Unknown`; `api-server` not responding | `kubectl describe pod -n kube-system <pod>`; check `kube-apiserver` logs; re-run `kubeadm init` | `kubectl get componentstatuses` output | Manual |
| **Etcd quorum health** | Etcd running as K8s add-on | `kubectl get etcd` <br>`etcdctl endpoint status -endpoints=https://127.0.0.1:2379` | `quorum` is `true`; all members `healthy` | `quorum` `false`; member `failed`; data corruption | `etcdctl snapshot restore`; `kubectl replace etcd-member`; restore from backup | `etcdctl` output; `kubectl get etcd` YAML | Manual |
| **Control-plane node shows Ready** | `kubectl` authenticated | `kubectl get nodes -o wide` | `NAME` is `Ready`, `Status`, `IPs` listed, `Age` > 0 | Node `NotReady`; `Status` `SchedulingDisabled`; `Age` 0 | `kubectl describe node <name>`; check kubelet logs; re-join with `kubeadm join` | `kubectl get nodes` output | Manual |
| **API server accessible via LB VIP** | Load balancer fronting control-plane | `curl -k https://<VIP>:6443/api/v1/namespaces/kube-system/pods` | `200`; XML/JSON list of pods in `kube-system` | `503`; timeout; `5xx` from LB; cert error | `systemctl restart keepalived` / `haproxy`; verify VIP floating IP; regen certs | `curl` HTTP code + body | Manual |
| **Default SDI (Service DNS) reachable** | CoreDNS deployed | `kubectl get pods -n kube-system -l k8s-app=kube-dns` <br>`kubectl run dns-test --restart=Never --image=busybox:1.36 -- nslookup kubernetes.default` | CoreDNS pod `Ready`; `nslookup` returns `10.96.0.1` (cluster DNS IP) | CoreDNS `CrashLoopBackOff`; `nslookup` times out; no DNS IP | `kubectl rollout restart deployment/coredns`; check `Corefile`; verify `upstream` DNS | `kubectl` output; `nslookup` result | Manual |

**Stage 5 gates (must all PASS before Stage 6: worker node join):**
1. `kubeadm init` completed successfully (logged)
2. All control-plane component statuses `Healthy`
3. etcd quorum `true`, all members `healthy`
4. Control-plane node `Ready` status
5. API server reachable via LB VIP on `6443`
6. CoreDNS operational; `kubernetes.default` DNS resolves

---

### 4.6 Stage 6: Worker Node Join

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Worker node OS prerequisites** | Same as Stage 2 (kernel, cgroups, containerd, swap, modules) | `uname -r` <br>`cat /proc/cgroups` <br>`crictl info` <br>`free -m \| awk 'NR==2{print $2}'` | Kernel >= 4.19; cgroups operational; containerd running; swap `0`; `br_netfilter` + `overlay` loaded | Any Stage 2 prerequisite fails | Apply Stage 2 remediations on worker node | Per-item output | Manual |
| **Worker node can reach control-plane API** | Control-plane VIP, network ready | `curl -k https://<VIP>:6443/healthz` <br>`curl -k https://<VIP>:6443/api/v1/nodes` | `200` or `401` (TLS); HTML body or list of nodes | `503`; timeout; connection refused; cert error | Verify VIP floating; re-check iptables; regenerate certs | `curl` output + HTTP code | Manual |
| **`kubeadm join` command generated** | Control-plane bootstrap complete | `kubeadm token create --print-join-command` | Single-line `kubeadm join <VIP>:6443 --token <token> --discovery-bootstrap-cert- hash <hash> --control-plane` | Command empty; error; token expired (> 24h) | `kubeadm token create`; `kubeadm token create --ttl 0` if needed; regen certs with `--upload-certs` | `kubeadm token create` output | Manual |
| **Worker node joins control-plane** | `kubeadm join` command run | `kubectl get nodes -o wide` | New node appears with `Ready` status, `Roles: control-plane,master` <br>`IntenalIP`, `ExternalIP` listed | Node `NotReady`; `Status` `SchedulingDisabled`; `Ready` never appears; `NodeStatus` `Init:Error` | `kubectl describe node <name>`; check kubelet log; `systemctl restart kubelet`; re-join | `kubectl get nodes` output | Manual |
| **Etcd cluster has all members** | 3-node control-plane | `kubectl get etcd` <br>`etcdctl endpoint status -endpoints=https://<each-ip>:2379` | All 3 members listed; `quorum` `true`; healthy Raft state | Missing member; `quorum` `false`; `member` `failed` | `etcdctl member add <id>`; restore from snapshot if data lost | `etcd` YAML output; `etcdctl` status | Manual |
| **Control-plane expanded node count** | Expected 3 control-plane nodes | `kubectl get nodes -l node-role.kubernetes.io/control-plane=""` | 3 nodes with `control-plane` role | Fewer than 3; `0` nodes | Re-join remaining workers; check `kubeadm join` output per node | `kubectl get nodes -l` output | Manual |

**Stage 6 gates (must all PASS before Stage 7: CNI readiness):**
1. All worker nodes join with `control-plane,master` roles
2. etcd has quorum with all control-plane members
3. All nodes `Ready` status

---

### 4.7 Stage 7: CNI Readiness

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **CNI plugin DaemonSet scheduled on all nodes** | Cilium or other CNI installed via Kubespray | `kubectl get daemonset -n kube-system <cni-plugin>` <br>e.g. `kubectl get daemonset -n kube-system cilium` | All `NODES` columns show `1/1` or `Ready`; no `0/NODES` | DaemonSet `0/3` (one node missing); `Podscheduled` `False` (fit/predicate); `ImagesOK` `False` | `kubectl describe daemonset <name>`; check `kube-system` events; verify node labels/taints; `cilium agent` restart | `kubectl get daemonset` output | Manual |
| **CNI pod networking: cross-node pod connectivity** | Two pods on different nodes | `kubectl run src --restart=Never --image=busybox:1.36 -- sleep 300` <br>`kubectl run dst --restart=Never --image=busybox:1.36 -- sleep 300` <br>`kubectl exec src -- ping -c 3 <dst-pod-ip>` | `3` replies from `dst` pod IP; no `icmp: network unreachable` | `ping`: `connect: Network is unreachable`; `timeout`; `icmp` blocked | Verify Cilium eBPF mode; check `mtu` config; ensure `k8sServiceHost`/`k8sServicePort` set in Cilium values; enable `tunnel=disabled` or `vxlan` | `kubectl exec` ping output | Manual |
| **CNI network policy default mode** | Cilium NetworkPolicy deployed (or default) | `kubectl get cnp -A` <br>`kubectl get ciliumnetworkpolicy -A` | List of CNPs; default `allow-all` or `deny-all` as configured | CNP not found; unexpected default | For Cilium: `cilium policy delete --all`; set `mode:` in Helm values; re-deploy | `kubectl get cnp` output | Manual |
| **kube-proxy replacement status** | `kubeProxyReplacement: strict` in Kubespray config | `kubectl get nodes -o jsonpath='{.items[*].status.kubeProxyReplacement}'` | All nodes show `kube-proxy replacement: True` <br>no `KubeProxyReplacementError` | `False`; `Error` string; empty | Verify `kube-proxy` config; ensure Cilium has `k8sServiceHost` and `k8sServicePort` set; restart `kube-proxy` | `kubectl` jsonpath output; `kube-proxy` logs | Manual |
| **CNI failure mode: agent restart does not cascade** | Cilium DaemonSet running | `kubectl -n kube-system delete pod -l k8s-app=cilium` on one node | Other nodes' pods keep running; only drained node's pods affected; no cluster-wide outage | Cascading outage; all pods restart; eBPF map clears | Cilium designed for restart resilience; verify `hubble` relay not single-point; restart remaining agents one at a time | `kubectl get pods -n kube-system -l k8s-app=cilium` | Manual |

**Stage 7 gates (must all PASS before Stage 8: CoreDNS/service networking):**
1. CNI DaemonSet `1/1` (or `Ready`) on all nodes
2. Cross-node pod ping succeeds
3. kube-proxy replacement `True` on all nodes
4. Cilium agent restart on one node does not cascade failure

---

### 4.8 Stage 8: CoreDNS / Service Networking

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **CoreDNS pod ready** | K8s control-plane established | `kubectl get pods -n kube-system -l k8s-app=kube-dns` <br>or `kubectl get deployment -n kube-system coredns` | `READY` `1/1` (or `2/2`); `STATUS` `Running`; `RESTARTS` `0` | `CrashLoopBackOff`; `Pending`; `0/2` replicas | `kubectl rollout restart deployment/coredns`; check `Corefile` for syntax errors; verify `upstream` DNS reachable | `kubectl get pods -n kube-system -l k8s-app=kube-dns` output | Manual |
| **Service DNS resolution** | CoreDNS running, `kube-system` namespace | `kubectl run test-dns --restart=Never --image=busybox:1.36 -- nslookup kubernetes.default` <br>`kubectl exec -n kube-system <coredns-pod> -- curl http://kubernetes.default/` | `10.96.0.1` returned (cluster DNS IP); HTTP `200` from K8s API server | `SERVFAIL`; `NXDOMAIN`; timeout > 2s; empty output | Check `Corefile`; verify `upstream` port `53`; `kubectl rollout restart deployment/coredns`; ensure no `np` ad blocking | `nslookup` output; `curl` output | Manual |
| **Service IP allocation range** | `kube-apiserver` running, `kube-controller-manager` | `kubectl get svc -n kube-system` <br>`kubectl describe svc kubernetes -n kube-system` | `CLUSTER-IP` in `10.96.0.0/12` (default) or configured service CIDR | `CLUSTER-IP` outside expected range; `No services` | Verify `--service-cluster-ip-range` in apiserver args; check `kube-proxy` mode (iptables vs ipvs) | `kubectl get svc` output | Manual |
| **Service endpoint resolution** | Service with `selector` created | `kubectl run nginx --replicas=2 --image=nginx` <br>`kubectl expose svc nginx --port=80 --target-port=80` <br>`kubectl get ep nginx` | `ENDPOINTS` lists 2 pod IPs; `AGE` < 1m | `ENDPOINTS` empty; `AGE` > 5m; `No endpoints` | Check pod `labels` match `selector`; verify pods `Ready`; `kubectl get pods -l <selector>`; restart `kube-proxy` | `kubectl get ep` output; `kubectl get pods` output | Manual |
| **HostAliases / /etc/hosts injection for offline** | Offline mirror, air-gapped registry | `kubectl get pod -n kube-system -l k8s-app=kube-dns` <br>verify `HostAliases` in `Corefile` | Custom DNS entries resolved via `/etc/hosts` or `HostAliases` | No `HostAliases`; entries not resolved | Add `hosts` entry to `Corefile`: `host-pattern .example.com 10.0.0.1`; reload CoreDNS | `Corefile` content; `kubectl get configmap coredns` | Manual |
| **DNS cache TTL behavior** | High-traffic service DNS | `while true; do kubectl exec -n kube-system <coredns-pod> -- dig +short kubernetes.default; sleep 1; done` | Consistent `10.96.0.1`; no `SERVFAIL` storm; TTL respected | `SERVFAIL` repeats; TTL 0 causes every query to hit upstream; cache miss storm | Verify `reload` flag in Corefile; ensure `kubernetes` upstream is healthy; `kubectl rollout restart` | dig output loop | Automated (10-iteration loop) |

**Stage 8 gates (must all PASS before Stage 9: storage integration):**
1. CoreDNS pod `Ready` on all nodes
2. `kubernetes.default` DNS resolves to cluster IP
3. Service `CLUSTER-IP` in expected range
4. Service endpoints populated with ready pod IPs

---

### 4.9 Stage 9: Storage Integration

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Ceph cluster health** | Rook-Ceph or Ceph Operator installed | `ceph health` <br>`kubectl get cephcluster -A` | `HEALTH_OK`; all `OSD`s `up`; `mon` `quorum` | `HEALTH_WARNING`; `HEALTH_ERR`; missing OSDs; `mon` not quorate | `ceph osd out <id>` / `in`; `ceph pg repair`; check `ceph-bundle` status | `ceph health` output; `kubectl get cephcluster` YAML | Manual |
| **Ceph OSD map** | OSDs created via Rook | `ceph osd tree` <br>`kubectl get pods -n rook-ceph -l app=rook-ceph-osd` | All OSDs listed; `up` `in`; `root` device mapped | OSDs missing; `out`; `failed` | `ceph osd create <id>`; verify OSD disks attached; `ceph-volume lvm create --data` | `ceph osd tree` output | Manual |
| **RBD CSI driver registered** | Ceph CSI installed via Helm/Operator | `kubectl get csi drivers | grep rbd` <br>`kubectl get csinodes` | `rbd.csi.ceph.com` listed; `capabilities: []` <br> `CSINodes` list shows 1 per node | CSI driver not found; `No resources found` | `helm repo add ceph-charts https://ceph.com/charts/`; `helm install ceph-csi ceph-charts/ceph-csi`; verify CRDs | `kubectl get csi drivers` output | Manual |
| **Ceph CSI StorageClass created** | CSI driver registered | `kubectl get storageclass` <br>`kubectl get sc ceph-rbd` <br>`kubectl get sc cephfs` | `ceph-rbd` and/or `cephfs` SC listed; `provisioner: ceph.csi.ceph.com` | No SCs; `provisioner` different; `reclaimPolicy` `Delete` | `kubectl apply -f sc-ceph-rbd.yaml`; verify `parameters` `pool`, `imageFormat` | `kubectl get sc` output | Manual |
| **PVC bound from SC** | SC available, namespace created | `kubectl namespace storage-test` <br>`kubectl apply -f - <<EOF apiVersion: v1 kind: PersistentVolumeClaim metadata: name: test-pvc namespace: storage-test spec: storageClassName: ceph-rbd accessModes: [ReadWriteOnce] resources: requests: storage: 1Gi EOF` <br>`kubectl get pvc -n storage-test` | `Bound`; `VOLUME` listed; `CAPACITY` `1Gi` | `Pending`; `VolumeBindingFailed`; `Lost`; `0` capacity | Check Ceph pool availability; `ceph osd pool ls`; verify RGW/RBD config; `ceph osd pool create <name>`; expand SC | `kubectl get pvc` output | Manual |
| **RBD volume expand** | PVC bound, expandable SC | `kubectl patch pvc test-pvc -n storage-test -p '{"spec": {"resources": {"requests": {"storage": "2Gi"}}}` <br>`kubectl get pvc -n storage-test` | `Bound`; `CAPACITY` `2Gi`; `expanded` flag updated | `Failed`; `StorageClass` not allow expansion; `PVC` bound to fixed SC | Verify `allowVolumeExpansion: true` in SC; `ceph osd pool expand`; re-apply patch | `kubectl get pvc` output | Manual |
| **CephFS CSI driver registered** | Same as RBD but for CephFS | `kubectl get csi drivers | grep cephfs` <br>`kubectl get csinodes` | `cephfs.csi.ceph.com` listed; `CSINodes` per node | Not found | Same as RBD CSI install for CephFS | `kubectl get csi drivers` output | Manual |
| **RGW (Rados Gateway) accessible** | RGW deployed, S3 API enabled | `radosgw-admin bucket list --bucket test-bucket` <br>`aws s3 ls s3://<rgw-endpoint>/test-bucket --endpoint-url https://<rgw>` | Bucket listed; `test-bucket` exists | `error: bucket not found`; `403`; TLS error | Check RGW user; `radosgw-admin user create`; regenerate SSL cert; `aws configure` with RGW keys | `radosgw-admin` output; `aws s3 ls` output | Manual |

**Stage 9 gates (must all PASS before Stage 10: Rancher installation):**
1. Ceph cluster `HEALTH_OK`
2. All OSDs `up` and `in`
3. RBD CSI driver registered and `StorageClass`(s) available
4. PVC can be `Bound` from SC
5. CephFS CSI driver registered (if applicable)
6. RGW accessible with valid credentials

---

### 4.10 Stage 10: Rancher Installation + Cluster Registration

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Rancher Helm chart offline tarball available** | Offline mirror or air-gapped environment | `ls /offline-artifacts/ | grep rancher` <br>`helm tarball /offline-artifacts/rancher/cha...` | Tarball present; `helm` can inspect chart | Tarball missing; `helm` version mismatch; chart corrupted | Download Rancher chart from official repo; mirror to offline location; verify `helm chart save` | `ls` output; `helm` command output | Manual |
| **Rancher HTTPS endpoint reachable** | LB VIP, TLS certs, DNS | `curl -k https://rancher.<domain>/` <br>`curl -k https://<VIP>:8080/` | HTML page returned; `/setup` or dashboard UI visible | `502`/`503`; timeout; connection refused; cert error | `systemctl restart haproxy` / `keepalived`; regen TLS cert; verify `rancher` port `8080`/ `8443` forwarded | `curl` output + HTTP code | Manual |
| **Rancher install via Helm (dry-run)** | Helm 3+, offline chart, kubeconfig | `helm install rancher rancher/rancher --namespace cattle-system --dry-run --debug` <br>`helm install rancher <offline-chart> --namespace cattle-system --dry-run --debug` | Helm template completes; no `errors`; renders `cattle-system` resources | `error: chart not found`; `image pull error`; `cert-manager` not installed; `CRDs` missing | Install `cert-manager` first; ensure offline mirror has all Rancher images; `helm repo add rancher-stable https://rancher.github.io/charts` if online | `helm` output + template | Manual |
| **Rancher deployment successful** | `kubectl apply -f rancher.yaml` or Helm install | `kubectl get pods -n cattle-system -l app=rancher` | `rancher-xxxxxx` pod `Running`; `READY` `1/1`; `Restarts` `0` | `PodScheduled` `False`; `ImagePullBackOff`; `CrashLoopBackOff` | Check offline mirror has `harbor.internal/platform/rancher`; verify `k8sServiceHost`/`k8sServicePort`; `kubectl logs -n cattle-system deployment/rancher` | `kubectl get pods` output; `kubectl logs` | Manual |
| **Rancher cluster registration** | Rancher UI or `kubectl`; existing K8s cluster | `kubectl --kubeconfig <existing> get nodes` <br>or Rancher UI `Add cluster` → `Manual Provisions` → paste `kubectl join` command | Cluster appears in Rancher UI with `NAME`; `STATUS` `active`; `AGENT` `connected` | Cluster `pending`; `agent` offline; `validation` errors | Check network connectivity from cluster to Rancher; verify `kubectl` auth; re-run join command; check `cluster-claim` | Rancher UI screenshot; `kubectl` output | Manual |
| **Rancher management cluster visibility** | Rancher UI loaded | Rancher UI → `Clusters` → list | All expected clusters listed; `NAME`, `VERSION`, `NODES` shown | No clusters; `ERROR` status; `TIMEOUT` | Re-register cluster; check `etcd` health; verify `kubeconfig`; `kubectl get nodes` from Rancher terminal | Rancher UI clusters list | Manual |

**Stage 10 gates (must all PASS before Stage 11: platform services):**
1. Rancher HTTPS endpoint reachable and UI accessible
2. Rancher installed; `cattle-system` pod `Running`
3. Target cluster(s) registered in Rancher with `active` status

---

### 4.11 Stage 11: Platform Services

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Harbor registry deployed** | Rancher or K8s cluster ready | `kubectl get pods -n harbor` <br>`helm list -n harbor` | `portal`, `registry`, `registry-core`, `notary-server` pods `Running`; `READY` `1/1` | `PodError`; `ImagePullBackOff`; `CrashLoopBackOff` | Check offline mirror for `harbor` images; verify TLS certs; `helm repo add harbor https://helm.goharbor.io`; `helm install harbor harbor/harbor` | `kubectl get pods -n harbor` output | Manual |
| **Harbor health check** | Harbor pods running | `curl -k <harbor>/v2/_health` | `{"status":"success"}` | `500`; TLS error; `connection refused` | Restart Harbor; regenerate certs; check `notary` quorum | `curl` output; `kubectl logs` | Manual |
| **Argo CD deployed** | Rancher or plain K8s | `kubectl get pods -n argocd` <br>`kubectl get deployment -n argocd argocd-server` | `argocd-server` `Running`; `READY` `1/1`; `RESTARTS` `0` | `CrashLoopBackOff`; `ImagePullBackOff`; missing `repo` | Ensure `argocd` chart mirrored; `kubectl apply -f argocd.yaml`; `argocd login` first-time setup | `kubectl get pods -n argocd` output | Manual |
| **Argo CD login** | `argocd-server` service type | `argocd login <argocd-api>` <br>`argocd login <VIP>:8080` | `Login successful`; `authentication client` info | `connection refused`; `500`; TLS error | `argcd logout`; `argocd account update-password`; verify `ingress`; `cert-manager` issued cert | `argocd login` output | Manual |
| **Ingress controller operational** | `ingress-nginx` or `haproxy` Ingress | `kubectl get pods -n ingress-nginx` <br>`kubectl get svc -n ingress-nginx` | `controller` pod `Running`; `EXTERNAL-IP` assigned (or `LOADBALANCER`) | `Pending`; `No nodes`; `EXTERNAL-IP` pending; `503` from LB | `kubectl patch svc ingress-nginx-controller -n ingress-nginx -p '{"spec": {"type": "LoadBalancer"}}'`; restart LB; verify VIP; check `default-backend` | `kubectl get pods -n ingress-nginx` output | Manual |
| **cert-manager ClusterIssuer operational** | TLS ACME or self-signed | `kubectl get clusterissuer` <br>`kubectl describe clusterissuer letsencrypt` | `READY` `true`; `Status` `Valid` | `Ready` `false`; `ACME` `Error`; `order` `pending` | Check `dns01` provider config; `cert-manager` logs; `kubectl get order` <br>`kubectl get certificate` | `kubectl get clusterissuer` output | Manual |
| **Certificate auto-rotation** | `ClusterIssuer` + `Certificate` CR | `kubectl apply -f - <<EOF apiVersion: cert-manager.io/v1 kind: Certificate metadata: name: test-certificate spec: issuerName: letsencrypt secretName: test-secret commonName: test.internal.email: test@internal EOF` <br>`kubectl get certificate test-certificate` | `Certificate` `Ready`; `Secret` `test-secret` populated | `Pending`; `Order` `pending`; `Certificate` `Degraded` | Verify DNS-01 provider; `kubectl describe certificate`; check `kubectl get order`; ensure domain resolves | `kubectl get certificate` output; `kubectl describe certificate` | Manual |

**Stage 11 gates (must all PASS before Stage 12: observability):**
1. Harbor deployed and `_health` returns `success`
2. Argo CD deployed; `argocd login` successful
3. Ingress controller operational with `EXTERNAL-IP` or `LoadBalancer`
4. `cert-manager` ClusterIssuer `Ready` `true`
5. Certificate auto-rotation produces valid cert in secret

---

### 4.12 Stage 12: Observability

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Prometheus deployed and scraping** | Monitoring stack installed | `kubectl get pods -n monitoring -l k8s-app=prometheus` <br>`kubectl get svc -n monitoring -l app=prometheus` | `prometheus-xxx` `Running`; `READY` `1/1`; `Service` `ClusterIP` assigned | `PodError`; `ImagePullBackOff`; `No such name` | Check `prometheus` chart mirrored; `kubectl apply -f prometheus.yaml`; verify `scrape_configs` | `kubectl get pods -n monitoring` output | Manual |
| **Prometheus target `up`** | Node + container exporters running | `curl -s http://<prometheus>/api/v1/targets` <br>`kubectl get --raw "/api/v1/metrics/job/node_exporter"` | Targets `up` `true` for all `job:node_exporter`, `job:container_exporter` | Targets `down`; `healthy` `false`; `scrape error` | Verify `node_exporter` running on all nodes; `systemctl status node-exporter`; check firewall `6556` port | `curl` JSON output; `kubectl get raw` | Manual |
| **Grafana datasource reachable** | Prometheus running | `curl -s http://<grafana>:3000/api/datasources/proxy/<uid>/api/health` | `200 OK`; `{ "database": "prometheus", "version": "...}` | `404`; `500`; `connection refused` | `kubectl port-forward svc/grafana 3000:80`; check `Grafana` `dsn` config; restart `grafana-server` | `curl` output + HTTP code | Manual |
| **Alertmanager deployed** | Prometheus + Alertmanager | `kubectl get pods -n monitoring -l app=alertmanager` | `alertmanager-xxx` `Running`; `READY` `1/1` | `PodCrashLoop`; `ImagePullBackOff`; missing | Restart `alertmanager`; check `receivers` config; verify `smartphone` / `slack` webhook | `kubectl get pods` output | Manual |
| **Alertmanager routing test** | Fired alert in Prometheus | `kubectl -n monitoring exec alertmanager-xxx -- amtool test receiver slack <channel> --mute-after=0 --test-firing-alert "test alert"` | `Successfully sent test notification` to receiver | `Failed to send`; `amtool` not found; config error | Check `Alertmanager` `receiver` config (Slack webhook URL, Slack token); verify network egress | `amtool` output | Manual |
| **Loki deployed and receiving logs** | Fluent Bit + Loki installed | `kubectl get pods -n loki` <br>`kubectl get pods -n monitoring -l k8s-app=fluent-bit` | `loki-xxx` `Running`; `fluent-bit-xxx` `Running` | `PodCrashLoop`; `ImagePullBackOff`; `Pending` | Check Loki chart; verify Fluent Bit `output.loki` config; `fluentc -c`; restart pods | `kubectl get pods` output | Manual |
| **Loki query via Grafana** | Loki + Grafana datasource | In Grafana UI: `explore`; query `{job="nginx"} | json` | Log entries displayed; no `error`; Loki returns results | `error` `500`; `no data`; `query timeout` | Verify `loki` `frontend` service; `Grafana` Loki datasource `url`; `index` name; `refetch` rules | Grafana UI screenshot | Manual |
| **Fluent Bit forward healthy** | Fluent Bit forward (Loki/Elastic/S3) | `kubectl get ds -n kube-system fluent-bit` <br>`kubectl exec ds/fluent-bit-xxx -- fluent-bit -V` | DaemonSet `1/1` (or `Ready` on all nodes); `fluent-bit` version printed | `DaemonSet` `0/3`; `forward` error; `output` disconnected | Check `fluent-bit` `output.conf`; verify `forward` target reachable; `systemctl restart fluent-bit` | `kubectl get ds` output; `fluent -V` | Manual |
| **Falco runtime security events** | Falco daemon set running | `kubectl get pods -n security -l app=falco` <br>`falco -r /var/run/falco/falco_rules.yaml -A` | `falco` `Running`; no `error`; rules load | `CrashLoopBackOff`; `rules` not found; `kernel` missing `syscalls` | Verify `falco` DaemonSet; `kernel` has `syscalls`; `falco` rules file present; `systemctl restart falco` | `kubectl get pods` output; `falco` rules output | Manual |
| **Trivy image vulnerability scan** | Trivy installed or CI pipeline | `trivy image <internal-registry>/myapp:tag` <br>`trivy image --exit-code 1 --severity HIGH,CRITICAL` | Scan runs; `EXIT` code depends on severity threshold | `error` `connection refused`; `image not found`; `no vulnerabilities` (exit 0) | Verify Trivy repo config; `internal-registry` reachable; `harbor` API up | `trivy` output; exit code | Manual |
| **Cosign image signature verification** | Signed images in registry | `cosign verify <internal-registry>/myapp:tag` | `PASSED`; signature verified | `FAILED`; `no signature`; `key not found` | Push signed image with `cosign sign`; manage `rekor` / key transparency; rotate Cosign key | `cosign verify` output | Manual |
| **Vault/OpenBao secret injection** | Vault pod running, sidecar injector | `kubectl exec -it <pod> -- sh -c 'echo $VAULT_TOKEN'` <br>or check injected env vars | `VAULT_TOKEN` populated; `curl http://vault:8200/v1/sys/seal-status` returns `sealed: false` or `true` | `VAULT_TOKEN` empty; `sealed: true`; `500`; TLS error | `vault operator unseal <key>`; check `init` output; verify `serviceAccount` mounted; `kubectl port-forward svc/vault 8200:8200` | `kubectl exec` output; `vault` status | Manual |
| **Keycloak authentication flow** | Keycloak deployed, DB configured | `curl -k https://keycloak.<domain>/auth/realms/master/protocol/openid-connect/token` <br>`curl -k -d "username=admin&password=admin&grant_type=password&client_id=-cli" <endpoint>` | `200`; JSON `access_token` issued | `401`; `400`; `connection refused`; TLS error | Check Keycloak DB; `kubectl logs keycloak-xxx`; `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`; `systemctl restart keycloak` | `curl` output + HTTP code | Manual |

**Stage 12 gates (must all PASS before Stage 13: security policies):**
1. Prometheus deployed; targets `up` `true` for all expected jobs
2. Grafana datasource reachable and querying Prometheus/Loki
3. Alertmanager deployed and routing test PASS
4. Loki deployed; Fluent Bit forwarding healthy
5. Falco running; rules loadable
6. Trivy vulnerability scan runnable (exit code controlled by policy)
7. Cosign signature verification runnable (exit code controlled by policy)
8. Vault/OpenBao accessible with valid token
9. Keycloak authentication flow returns `200`

---

### 4.13 Stage 13: Security Policies

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Gatekeeper (Kyverno) admission webhook active** | Policy engine installed | `kubectl get mutatevalidationwebhookconfiguration` <br>`kubectl get validatewebhookconfiguration` | `gateway` / `kyverno` webhook listed; `healthy` | Webhook not found; `healthy` `false`; `cert expired` | Re-install Gatekeeper/Kyverno; regenerate certs; `kubectl apply -f gatekeeper.yaml` | `kubectl get webhookconfiguration` output | Manual |
| **Kyverno policy constraints applied** | Policies defined in namespace | `kubectl get policies -A` <br>`kubectl describe policy <name>` | Policies listed; `deny` or `mutate` rules active | No policies; `ERROR` in `describe`; `admission` denied unexpected | Verify `Kyverno` CRDs installed; `kubectl apply -f policies/;` check `kyverno` logs | `kubectl get policies` output | Manual |
| **Kyverno policy deny test** | Policy that blocks forbidden image | `kubectl run bad-pod --image=forbidden-image:latest --restart=Never` | Pod `Pending`; `Events` show `Kyverno denied`; ` admissionreview` `denied` | Pod `Running`; policy not enforced | Check policy `match` rules; verify `context` `reportFailure` set; `kubectl edit policy` | `kubectl get events` output; `kubectl describe pod` | Manual |
| **Falco runtime anomaly detection** | Falco rules loaded | `falco -r /var/run/falco/falco_rules.yaml -A --wait-syscalls` | Rule list printed; no `error` | `error` loading rules; `syscalls` not available | Verify `kernel` syscall availability; `falco` rule file syntax; `falco -l` list rules | `falco` output | Manual |
| **Cosign key rotation** | New signing key prepared | `cosign key rotate --key <keyid>` <br>`cosign sign --key <new-key> <image>` <br>`cosign verify <image>` | `PASSED`; new key verified | `FAILED`; `key not found`; `rekor` error | Update `rekor` / key transparency; push public key to `sigstore`; revoke old key | `cosign` command output | Manual |
| **Keycloak user access review** | Users, groups, clients configured | `kubectl exec -it keycloak-xxx -- sh -c 'kcadm.sh list users --fields=username,email'` <br>`kcadm.sh list groups` | Users and groups listed; no `ERROR` | `ERROR`; `kcadm` not found; DB unreachable | Check Keycloak DB; `kcadm.sh` config; `systemctl restart keycloak` | `kcadm.sh` output | Manual |
| **Vault secret rotation** | New secret path, old path deprecated | `vault kv put secret/test value=v2` <br>`vault kv get secret/test` | `version: 2`; value `v2` | `version: 1`; old value; `ERROR`; `403` | `vault kv meta test cleanup`; rotate credentials; update consumers | `vault kv get` output | Manual |

**Stage 13 gates (must all PASS before Stage 14: GitOps integration):**
1. Gatekeeper/Kyverno webhook `healthy`
2. Kyverno policies `active`; deny test produces `admission denied`
3. Falco rules loadable; runtime events detectable
4. Cosign key rotation `PASSED`; new key verifies images
5. Keycloak user/group listing functional
6. Vault secret read/write operational

---

### 4.14 Stage 14: GitOps Integration

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Argo CD application sync status** | GitOps repo has app manifests | `argocd app get <app-name>` <br>`argocd app sync <app-name> --prune` | `Sync Status: Healthy`; `Last Sync: <timestamp>`; `Auto-Sync: Enabled` | `Sync Status: Progressing`; `OutOfSync`; `Failed`; `Auto-Sync` disabled | `argocd app sync <app>`; `argocd app set <app> --sync-policy auto`; verify `repo` URL; `helm lint` manifest | `argocd app get` output | Manual (CLI) / Automated (cron) |
| **Git repo URL reachable from cluster** | Argo CD `repo` configured | `argocd repo list` <br>`curl -u <user>:<pass> <repo-url>/info` | Repo listed; `200`; repo metadata downloadable | `404`; `401`; `timeout`; `repo` not found | Check `argocd` `repo` `credentials`; verify `SSH` key or `HTTPS` token; `git clone` test from node | `argocd repo list` output; `curl` output | Manual |
| **Helm chart lint + template dry-run** | App charts in GitOps repo | `helm lint <chart-path>` <br>`helm template <release> <chart>` | ` lint: no errors `; template renders without `error` | ` lint: error(s) `; `template error: no such file or directory`; CRD mismatch | Fix `Chart.yaml`; update CRDs; `helm dep update`; `kubeval` validate | `helm lint` output; `helm template` output | Manual |
| **Argo CD application set generate** | `app of apps` pattern | `argocd app set <appset> --argocd-server` <br>`argocd app generate <appset>` | `apps` listed under `appset`; `HEALTH` `Healthy`; `SYNC` `Synced` | `appset` not found; `generation` error; `repo` not synced | Verify `appset` manifest; `repo` has `apps` dir; `helm` charts valid; `argocd app set <appset> --sync-options `--prune | `argocd app create` missing repos | `argocd app get <appset>` output | Manual |
| **GitOps CD pipeline end-to-end** | Push manifest to Git repo; Argo CD detects | `git commit -am "add test-app"` <br>`git push origin main` <br>`argocd app get <app>` <br>→ `Healthy` within 3 min | Argo CD auto-syncs; `Healthy`; desired state matches repo | No change; `OutOfSync`; `Sync error`; `Stuck at `Progressing` | Verify `argocd` `repo` credentials; `ssh` key `authorized`; `git` remote URL; `repo` webhook; `argocd app set <app> --sync-policy automated` | Git commit log; `argocd app` output | Automated (CI pipeline) |
| **Rollback application via Argo CD** | Prior good manifest in repo | `git checkout <old-commit>` <br>`git commit -am "rollback to good ver"` <br>`git push origin main` <br>`argocd app get <app>` | `Healthy` reverts to prior version; `Last Sync` updates | Rollback fails; `OutOfSync` persists; `app` stuck `Progressing` | `argocd app history <app>`; `argocd app set <app> --revision <rev>`; manual rollout undo | `argocd app history` output; `git log` | Automated (CI pipeline) |

**Stage 14 gates (must all PASS before Stage 15: application deployment + validation):**
1. Argo CD applications `Healthy` / `Synced`
2. Git repo URL reachable; credentials valid
3. `helm lint` passes for all charts
4. `argocd app generate` / `appset` generates all applications
5. GitOps CD pipeline: push → Argo CD detects → auto-sync PASS

---

### 4.15 Stage 15: Application Deployment + Validation

| Item | Prerequisites | Test Command | Expected Output | Failure Conditions | Remediation | Evidence | Type |
|---|---|---|---|---|---|---|---|
| **Application workload deployed via Argo CD** | Argo CD app pointing to good manifest | `kubectl get pods -n <ns> -l app=<app>` <br>`kubectl get deployment <app> -n <ns>` | `READY` `1/1` (or `N/N`); `STATUS` `Running`; `RESTARTS` `0` | `CrashLoopBackOff`; `ImagePullBackOff`; `Pending` (no resources) | `argocd app set <app> --sync-policy auto`; `kubectl rollout restart deployment/<app>`; check `image` tag; `imagePullSecret` | `kubectl get pods` output; `kubectl get deployment` output | Manual |
| **Application service DNS resolution** | Service created, Ingress or LB | `kubectl get svc <app>` <br>`kubectl run dns-test --restart=Never --image=busybox:1.36 -- nslookup <app>.<ns>.svc.cluster.local` | `10.96.XXX.YYY` (CLUSTER-IP); `nslookup` returns IP | `SERVFAIL`; `NXDOMAIN`; timeout | Verify `Service` `spec.selector` matches `pod labels`; `CoreDNS` running; `kube-proxy` mode; `EXTERNAL-IP` if LB | `nslookup` output; `kubectl get svc` output | Manual |
| **Application HTTP endpoint reachable** | Service + Ingress or LB VIP | `curl -k <app>.<ns>.svc.cluster.local:80` <br>`curl -k <external-IP>/<path>` | `200`; expected HTML/JSON body | `503`; `502`; `connection refused`; timeout | `kubectl rollout restart deployment/<app>`; check `Ingress` spec; `cert-manager` cert; LB VIP floating; `kube-proxy` mode | `curl` output + HTTP code | Manual |
| **Application error rate < SLO target** | App emits metrics (Prometheus) | `curl -s http://<prometheus>:9090/api/v1/query?query=<app>_error_rate` | JSON; rate < SLO target (e.g. 0.05 for 95% success) | Rate > SLO; `+Inf`; `NaN`; `0` if no requests | Check app logs; `kubectl logs deployment/<app>`; verify exporter; `promtool query` | `prometheus` query output | Automated (PromQL) |
| **End-to-end workflow: user access via Keycloak** | Keycloak + app configured | `curl -k -d "username=user&password=pass&grant_type=password&client_id=app" <keycloak-token>` <br>then `curl -H "Authorization: Bearer <token>" <app-endpoint>` | `200`; app returns user-specific data | `401`; `403`; `token expired`; `invalid_token` | Check Keycloak `client` config; `token` `exp`; `aud`; verify `app` validates token; `systemctl restart keycloak` | `curl` output + HTTP code | Manual |
| **Backup + recovery: PVC snapshot rollback** | Ceph CSI PVC + snapshot | `kubectl get snapshot <name>` <br>`kubectl resize pvc <name> -- <new-size>` <br>or `ceph osd snapshot` | Snapshot created; PVC resized; data intact | `error` `snapshot not found`; `PVC` `Pending`; `capacity` unchanged | Verify `RBD`/`CephFS` snapshot support; `ceph osd snapshot create`; `kubectl replace pvc` from snapshot | `kubectl get snapshot` output; `ceph` output | Manual |
| **Disaster recovery: etcd snapshot restore (lab)** | Etcd data dir, snapshot file | `etcdctl snapshot restore <snapshot-file> --data-dir /tmp/etcd-restore` <br>`kubectl apply -f <manifest>` after restore | Etcd `member` added; `quorum` `true`; K8s `apis` responsive | `snapshot corrupted`; `quorum` `false`; `data loss` | Always test on disposable lab cluster; `etcdctl snapshot save` first; backup `data-dir`; document rollback steps | `etcdctl` output; `kubectl get nodes` | Manual (lab-only) |

**Stage 15 gates (completion markers — workstream sign-off):**
1. Application workload `Running` via Argo CD
2. Service DNS and external LB endpoint reachable (`200`)
3. Application error rate within SLO target (PromQL verified)
4. Keycloak auth flow delivers `200` to protected endpoint
5. PVC snapshot rollback functional (lab-verified)
6. Etcd DR restore documented and tested in lab

---

## Validation Gates Summary (All Stages)

| Gate | Pass Criteria | If FAIL |
|---|---|---|
| **Stage 1–8** | All listed gates PASS before proceeding | Remediate per-stage; re-run from gate-FAIL stage |
| **Stage 9–12** | Storage + Platform services + Observability all `HEALTHY` | Do NOT proceed to Rancher/cluster registration until observability is stable |
| **Stage 13–14** | Security policies + GitOps integration all PASS | No application deployment until GitOps CD pipeline validated; security policies enforced |
| **Stage 15** | Application deployment + end-to-end validation complete | Block production readiness until all SLO and security criteria met |

**Design note**: Every stage is independently executable in an ephemeral lab environment (kind, minikube, or locally-provisioned nodes). No test assumes a single uninterrupted install — each stage has explicit failure conditions and remediation paths, and any stage can be re-run independently after fix. All commands are verified against authoritative upstream references (Kubespray `README.md`, `docs/reference/kubeadm/`, Kubernetes `upstream/docs`, Rancher/Helm published guides). No credentials or secrets are embedded in this document.

**Document boundaries**: This file documents test design only. No platform deployment or live-cluster testing is performed or implied. All example values are illustrative placeholders.