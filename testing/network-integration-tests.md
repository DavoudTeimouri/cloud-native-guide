# Section 5: Network and Service Integration Tests

**Purpose**: Cross-component tests for end-to-end network- and service-layer behavior in the Kubernetes cluster. Positive tests confirm expected connectivity; negative tests verify that prohibited traffic is actually blocked. All tests are designed against ephemeral/lab clusters only — no live or shared clusters are used.

> **Important**: Static YAML/schema checks are NOT proof of runtime functionality. A valid manifest may fail at runtime due to network policies, CNI constraints, RBAC, or service topology. Always validate against a live (ephemeral or staging) cluster when runtime behavior is the goal.

---

## 5.1 Node-to-Node Communication

| Field | Details |
|---|---|
| **Test ID** | NET-001 |
| **Scope** | Node-to-node connectivity (inter-node routing, CNI data-plane) |
| **Positive Test** | |
| **Preconditions** | Cluster nodes are Ready; CNI (Cilium/Calico) is running; IPv4 cluster network is allocated |
| **Test Command** | `kubectl exec -n kube-system <cilium-pod> -- cilium node discover` (or `kubectl node-ready` for simple reachability) |
| **Expected Output** | All nodes show `Ready` status; cilium connectivity check passes |
| **Failure Condition** | Node(s) show `NotReady`; cilium node discover reports lost connectivity |
| **Remediation** | Verify CNI pod logs; check etcd node records; confirm no IP conflicts in cluster CIDR |
| **Evidence** | `cilium node discover` output; `kubectl get nodes` |
| **Automated** | Yes — poll node readiness + cilium connectivity in a loop |
| **Manual** | Yes — `kubectl get nodes`, verify SSH/reachability between node IPs |
| **Negative Test (NET-001-NEG)** | |
| **Preconditions** | Same as positive; an explicit NetworkPolicy blocks inter-node traffic |
| **Test Command** | Deploy a pod that attempts `nc <other-node-ip> 22`; observe capture via `cilium monitor` |
| **Expected Output** | Connection refused or blocked; `cilium monitor` shows drop reason = policy |
| **Failure Condition** | Traffic passes through despite policy — indicates policy not enforced |
| **Remediation** | Review NetworkPolicy order; ensure `cilium-node` label is present; check `k8s.opsnetwork.io/enforce` |
| **Evidence** | `cilium monitor` capture; NetworkPolicy resource definition |
| **Automated** | Yes — capture baseline, apply policy, attempt connect, verify drop |
| **Manual** | Yes — use `cilium ssh` or `tcpdump` on source node |

---

## 5.2 Pod-to-Pod Across Workers

| Field | Details |
|---|---|
| **Test ID** | NET-002 |
| **Scope** | Pod-to-pod communication across different worker nodes (inter-node routing through CNI) |
| **Positive Test** | |
| **Preconditions** | Two pods scheduled on different nodes; both using the cluster network CNI; no restrictive NetworkPolicy in namespace |
| **Test Command** | `kubectl run tester --rm -i --restart=Never --image=appropriate/curl --rm=true -- curl -sS <target-pod-ip>:80` |
| **Expected Output** | HTTP 200 or expected payload from target pod |
| **Failure Condition** | Connection timeout; `E: Cannot connect to host`; target pod not in Ready state |
| **Remediation** | Verify both pods are Running; check `kubectl get pods -o wide` for node assignment; ping target IP from source node; ensure no SNAT/NAT breaking return path |
| **Evidence** | `curl` output; `kubectl get pods -o wide`; `kubectl exec` into source pod to run `ping` |
| **Automated** | Yes — scripted curl from pod A to pod B; assert exit code 0 |
| **Manual** | Yes — exec into one pod, `curl` the other pod's ClusterIP/NodeIP |
| **Negative Test (NET-002-NEG)** | |
| **Preconditions** | Same as positive; a Cilium NetworkPolicy or Calico NetworkPolicy blocks traffic between pod CIDRs or namespaces |
| **Test Command** | Apply a blocking NetworkPolicy (e.g., deny all between namespaces); then run the curl test from NET-002 positive |
| **Expected Output** | Connection refused; `curl` exit code 7; `cilium monitor` shows "policy drop" |
| **Failure Condition** | Traffic passes despite blocking policy — indicates policy order or selector mismatch |
| **Remediation** | Verify policy `order` number; confirm selector matches pod labels; check `egress`/`ingress` rules; ensure policy is not `disabled` |
| **Evidence** | Applied NetworkPolicy YAML; `cilium monitor` capture; `kubectl get networkpolicy` |
| **Automated** | Yes — apply policy, rerun NET-002 test, assert failure |
| **Manual** | Yes — apply via `kubectl apply -f`, then test manually |

---

## 5.3 Pod-to-Service Communication

| Field | Details |
|---|---|
| **Test ID** | NET-003 |
| **Scope** | Pod-to-Service (ClusterIP, NodePort, LoadBalancer) resolution and connectivity |
| **Positive Test** | |
| **Preconditions** | Service defined in namespace; endpoints created; CoreDNS resolvable; no split-horizon DNS |
| **Test Command** | `kubectl run tester --rm -i --restart=Never --image=appropriate/curl --rm=true -- curl -sS http://<service-name>.<namespace>.svc.cluster.local` |
| **Expected Output** | HTTP 200 (or expected payload); DNS resolves to service ClusterIP |
| **Failure Condition** | `curl: (3) <url> port` — DNS resolution fails; connection refused; service has 0 endpoints |
| **Remediation** | Check `kubectl get svc`; verify endpoints with `kubectl get endpoints`; restart CoreDNS if stale; ensure selector matches pod labels |
| **Evidence** | `curl` output; `kubectl get svc,ep`; `nslookup <service>` |
| **Automated** | Yes — scripted curl; assert HTTP 200 and response time |
| **Manual** | Yes — exec into pod, run curl against service |
| **Negative Test (NET-003-NEG)** | |
| **Preconditions** | Same as positive; a NetworkPolicy in the pod's namespace blocks inbound traffic to the service port |
| **Test Command** | Apply a NetworkPolicy that denies inbound traffic to the service's selector/port; then run the pod-to-service curl |
| **Expected Output** | Connection timed out or refused; DNS resolves but no route to endpoint |
| **Failure Condition** | Traffic passes despite blocking policy — indicates policy selector does not match the service's pod labels |
| **Remediation** | Verify policy `selector` matches the service's pod labels; check `order`; confirm `namespace` scope is correct; ensure `k8s.opsnetwork.io/enforce` is not set to `false` |
| **Evidence** | NetworkPolicy YAML; `cilium monitor` or `kubectl get policy`; `curl` exit code |
| **Automated** | Yes — apply policy, rerun NET-003, assert failure |
| **Manual** | Yes — apply policy, test manually |

---

## 5.4 DNS Resolution

| Field | Details |
|---|---|
| **Test ID** | NET-004 |
| **Scope** | Cluster DNS resolution: internal services, external domains, split-horizon, ConfigMap/HostFile overrides |
| **Positive Test** | |
| **Preconditions** | CoreDNS running; `cluster.local` zone; no custom upstream DNS misconfiguration |
| **Test Command** | `nslookup <service>.<namespace>.svc.cluster.local`; `dig +short <service>` |
| **Expected Output** | A/AAAA record returns ClusterIP/ClusterIPv6; query time < 500ms; no SERVFAIL |
| **Failure Condition** | SERVFAIL; NXDOMAIN; long query time (>2s); unexpected IP returned |
| **Remediation** | Restart CoreDNS (`kubectl -n kube-system rollout restart deployment/coredns`); verify `kubectl get configmap coredns`; check for upstream DNS override in kubelet flags; ensure `/etc/resolv.conf` points to `10.96.0.10` (cluster DNS) |
| **Evidence** | `nslookup`/`dig` output; `kubectl get pods -n kube-system -l k8s-app=kube-dns` or `k8s-app=coredns` |
| **Automated** | Yes — scripted dig against each service type; assert exit code 0 and expected IP |
| **Manual** | Yes — `nslookup` from inside a pod and from a host |
| **Negative Test (NET-004-NEG)** | |
| **Preconditions** | Same as positive; a CoreDNS ConfigMap overrides `upstream` to a non-functional resolver; or a `dnsPolicy: None` with custom `nameservers` misconfigured |
| **Test Command** | Force `dnsPolicy: None` on a pod with bad nameserver; run `nslookup` inside that pod |
| **Expected Output** | Resolution fails; `SERVFAIL` or no answer; pod cannot resolve internal services |
| **Failure Condition** | Resolution unexpectedly succeeds despite bad ConfigMap — indicates fallback to host DNS |
| **Remediation** | Fix `nameservers` in the ConfigMap; ensure `dnsPolicy: ClusterFirst` is used unless custom is intentional; verify `/etc/resolv.conf` inside the pod |
| **Evidence** | CoreDNS ConfigMap; pod `/etc/resolv.conf`; `nslookup` output before/after fix |
| **Automated** | Yes — create pod with `dnsPolicy: None`, assert resolution fails |
| **Manual** | Yes — create pod, check resolv.conf, test nslookup |

---

## 5.5 Internal/External Service Connectivity

| Field | Details |
|---|---|
| **Test ID** | NET-005 |
| **Scope** | Internal service (ClusterIP) reachable from within cluster; external service (LoadBalancer/NodePort) reachable from within cluster |
| **Positive Test** | |
| **Preconditions** | Internal ClusterIP service; external LoadBalancer or NodePort service with valid ingress; no firewall blocks outbound 443/80 from cluster |
| **Test Command** | `kubectl run tester --rm -i --restart=Never --image=appropriate/curl --rm=true -- curl -sS http://<internal-svc>` then `curl -sS http://<external-lb-ip>` |
| **Expected Output** | Both curl commands succeed; internal returns expected payload; external returns 200 or expected payload |
| **Failure Condition** | Internal curl fails (no endpoints, wrong selector); external curl fails (LB not provisioned, no route to internet, firewall blocks 80/443) |
| **Remediation** | Check internal service endpoints and selectors; for external: verify LB controller status (`kubectl get svc -A`), check cloud provider LB, ensure route table allows outbound, check firewall outbound rules |
| **Evidence** | `curl` output; `kubectl get svc,ep,ingress`; cloud provider LB status |
| **Automated** | Yes — scripted dual curl; assert both exit codes 0 |
| **Manual** | Yes — exec into pod, run both curls |
| **Negative Test (NET-005-NEG)** | |
| **Preconditions** | Same as positive; an egress NetworkPolicy or firewall rule blocks outbound traffic to the external service's IP/port |
| **Test Command** | Apply a NetworkPolicy that denies egress to the external service's IP and port; then run the external curl from NET-005 positive |
| **Expected Output** | External curl fails (timeout or connection refused); internal curl still succeeds if its traffic is not covered by the policy |
| **Failure Condition** | External traffic passes despite blocking policy — indicates policy scope gap or missing rule |
| **Remediation** | Verify policy `egress` section targets the correct IP/port; check `not selector` vs `destination`; ensure policy `order` is set to enforce before broader rules; confirm no `allow-all` default is overriding |
| **Evidence** | NetworkPolicy YAML; `cilium monitor` or `tcpdump`; `curl` exit code |
| **Automated** | Yes — apply policy, rerun NET-005, assert external curl fails |
| **Manual** | Yes — apply policy, test manually; verify with `kubectl describe networkpolicy` |

---

## 5.6 Ingress Routing

| Field | Details |
|---|---|
| **Test ID** | NET-006 |
| **Scope** | Ingress controller (NGINX/Traefik/GCE/Azure) routing HTTP/HTTPS traffic to services |
| **Positive Test** | |
| **Preconditions** | Ingress resource defined with host/paths; Ingress controller pod Running; valid TLS certificate if TLS is configured |
| **Test Command** | `curl -k -s https://<ingress-host>/` (or `http` if no TLS) |
| **Expected Output** | HTTP 200 or expected payload; TLS handshake succeeds (if TLS configured) |
| **Failure Condition** | `curl: (6) Could not resolve host`; `curl: (35) SSL connect error`; HTTP 404 or 502 from backend |
| **Remediation** | Check Ingress resource YAML for correct host/path; verify Ingress controller pods are Ready; check controller logs for config errors; ensure DNS for the host resolves to the Ingress IP/LoadBalancer |
| **Evidence** | `curl` output; `kubectl get ingress`; Ingress controller logs (`kubectl logs -n ingress-nginx <pod>`) |
| **Automated** | Yes — scripted curl against ingress host; assert HTTP 200 |
| **Manual** | Yes — `curl` from a pod or from a bastion host |
| **Negative Test (NET-006-NEG)** | |
| **Preconditions** | Same as positive; an Ingress NetworkPolicy or NetworkPolicy that blocks inbound traffic to the Ingress controller's namespace/ports |
| **Test Command** | Apply a NetworkPolicy that denies inbound traffic to the Ingress controller namespace on port 80/443; then run the ingress curl from NET-006 positive |
| **Expected Output** | curl fails; TLS handshake or TCP connection refused |
| **Failure Condition** | Traffic passes despite blocking policy — indicates policy selector does not match Ingress controller pods, or `allow-all` default exists |
| **Remediation** | Verify policy `selector` matches Ingress controller pod labels (e.g., `app.kubernetes.io/name: ingress-nginx`); check `order`; ensure no `k8s.opsnetwork.io/enforce: "false"` annotation; confirm policy is in the same namespace as the Ingress controller |
| **Evidence** | NetworkPolicy YAML; `curl` output; `kubectl get networkpolicy`, `kubectl get pods -n ingress-nginx` |
| **Automated** | Yes — apply policy, rerun NET-006, assert failure |
| **Manual** | Yes — apply policy, test manually |

---

## 5.7 LB/VIP Failover

| Field | Details |
|---|---|
| **Test ID** | NET-007 |
| **Scope** | LoadBalancer VIP failover: secondary node takes over when primary becomes unavailable |
| **Positive Test** | |
| **Preconditions** | Cloud provider LoadBalancer service; two worker nodes capable of LB provisioning; health checks configured |
| **Test Command** | `kubectl get svc <lb-service> -o jsonpath='{.status.loadBalancer.ingress}'` — note current IP; then `kubectl drain <node-to-simulate-failover> --ignore-daemonsets --delete-empty-data`; re-check the LB ingress IP changes or remains stable |
| **Expected Output** | LB ingress IP either remaps to the remaining node's IP or stays stable depending on cloud provider; no service disruption (curl still succeeds) |
| **Failure Condition** | LB IP becomes unreachable; service drops to `Pending`; curl fails after drain |
| **Remediation** | Check cloud provider LB limits; ensure `cluster-name` or `node-labels` selector allows failover; verify health check configuration; consider increasing `spec.externalTrafficPolicy` to `Local` if session affinity is needed |
| **Evidence** | `kubectl get svc` before/after drain; cloud provider console; `curl` output before/after |
| **Automated** | Yes — scripted drain + re-query LB IP + rerun curl; assert curl still succeeds or expected IP change |
| **Manual** | Yes — drain a node, observe LB, test curl |
| **Negative Test (NET-007-NEG)** | |
| **Preconditions** | Same as positive; a NetworkPolicy or security group blocks failover traffic or VIP assignment |
| **Test Command** | Apply a security group / NetworkPolicy that blocks traffic to the LB VIP; then drain a node and observe |
| **Expected Output** | LB VIP becomes unreachable or does not fail over; service remains on failing node |
| **Failure Condition** | Failover proceeds despite blocking policy — indicates policy scope too narrow or missing VIP rule |
| **Remediation** | Verify NetworkPolicy `egress/ingress` covers the LB VIP range or the cloud provider's security group rules; check that the policy `order` does not skip LB-related rules; confirm the cloud provider security group allows the LB health check ports |
| **Evidence** | NetworkPolicy/YAML; cloud security group config; `curl` before/after; `kubectl get svc` |
| **Automated** | Yes — apply policy, drain node, rerun curl, assert failure |
| **Manual** | Yes — apply policy, drain node, test manually |

---

## 5.8 Cilium NetworkPolicy Enforcement

| Field | Details |
|---|---|
| **Test ID** | NET-008 |
| **Scope** | Cilium NetworkPolicy enforcement: positive (allowed) and negative (blocked) rules |
| **Positive Test** | |
| **Preconditions** | Cilium installed; NetworkPolicy CRDs available; a permissive Policy allows traffic between labeled pods |
| **Test Command** | Apply a Cilium NetworkPolicy that `allow`s traffic from `source.ns: pod-A` to `dest.ns: pod-B` on port 80; then run `curl` from pod-A to pod-B |
| **Expected Output** | curl succeeds; `cilium policy status` shows "ALLOW" for the rule |
| **Failure Condition** | curl fails despite policy saying allow — indicates policy not applied or selector mismatch |
| **Remediation** | Verify `source`/`dest` labels exist on the pods; check `cilium networkpolicy` YAML for correct `from/to`; ensure `enable` is not set to `false`; check `cilium` pod logs for policy compilation errors |
| **Evidence** | CiliumNetworkPolicy YAML; `cilium policy status`; `curl` output |
| **Automated** | Yes — apply policy, run curl, assert exit code 0 and policy status "ALLOW" |
| **Manual** | Yes — apply policy, test curl, check `cilium policy status` |
| **Negative Test (NET-008-NEG)** | |
| **Preconditions** | Same as positive; a Cilium NetworkPolicy `den`ies traffic between the same pods/ports |
| **Test Command** | Apply a Cilium NetworkPolicy that `den`s traffic from `source.ns: pod-A` to `dest.ns: pod-B` on port 80; then run `curl` from pod-A to pod-B |
| **Expected Output** | curl fails; `cilium policy status` shows "DENY" for the rule; `cilium monitor` captures "policy drop" |
| **Failure Condition** | Traffic passes despite DENY policy — indicates policy order issue, missing `enable`, or `k8s.opsnetwork.io/enforce: "false"` |
| **Remediation** | Verify policy `order` number; confirm `from/to` selectors match pod labels; check for broader `allow` policy with lower `order` that may override; ensure `k8s.opsnetwork.io/enforce` is not set to `false` on the cluster |
| **Evidence** | CiliumNetworkPolicy YAML; `cilium policy status`; `cilium monitor`; `curl` exit code |
| **Automated** | Yes — apply policy, run curl, assert exit code 1 and policy status "DENY" |
| **Manual** | Yes — apply policy, test curl, check `cilium policy status` |

---

## 5.9 Cross-Namespace Communication

| Field | Details |
|---|---|
| **Test ID** | NET-009 |
| **Scope** | Pod in namespace A communicating with service in namespace B (same cluster, inter-namespace) |
| **Positive Test** | |
| **Preconditions** | Service defined in namespace B with cluster-scope ClusterIP; pod in namespace A has `cluster.local` DNS resolution; no namespace-scoped NetworkPolicy blocking cross-ns traffic |
| **Test Command** | `kubectl run tester --rm -i --restart=Never --image=appropriate/curl --rm=true -- curl -sS http://<service-name>.<namespace-b>.svc.cluster.local` |
| **Expected Output** | curl succeeds; DNS resolves to ClusterIP; payload returned |
| **Failure Condition** | curl fails; DNS returns NXDOMAIN or wrong IP; "Forbidden" or "403" from service |
| **Remediation** | Verify service is `clusterIP` (not `Namespace-scoped`); check for namespace-scoped NetworkPolicy blocking ingress from namespace A; ensure pod has permissions to reach cluster DNS; check `kubectl auth can-i` if RBAC is in place |
| **Evidence** | `curl` output; `kubectl get svc,ep -n <ns-b>`; `kubectl get networkpolicy -n <ns-b>` |
| **Automated** | Yes — scripted cross-ns curl; assert exit code 0 |
| **Manual** | Yes — exec into pod in ns A, curl ns B service |
| **Negative Test (NET-009-NEG)** | |
| **Preconditions** | Same as positive; a namespace-scoped NetworkPolicy in namespace B blocks inbound traffic from namespace A |
| **Test Command** | Apply a NetworkPolicy in namespace B that `den`s traffic from `source.namespace: ns-a`; then run the cross-ns curl from NET-009 positive |
| **Expected Output** | curl fails; DNS resolves but connection refused or filtered; `cilium monitor` shows "policy drop" from other-ns |
| **Failure Condition** | Traffic passes despite blocking policy — indicates policy `from` selector does not match the source namespace, or `namespace-wide` default allow exists |
| **Remediation** | Verify policy `from` `namespace` selector matches `ns-a`; check `order`; ensure no `k8s.opsnetwork.io/enforce: "false"`; confirm the policy is in the same namespace as the target service |
| **Evidence** | NetworkPolicy YAML; `cilium policy status`; `curl` exit code |
| **Automated** | Yes — apply policy, rerun NET-009, assert failure |
| **Manual** | Yes — apply policy, test manually |

---

## 5.10 K8s API Access

| Field | Details |
|---|---|
| **Test ID** | NET-010 |
| **Scope** | K8s API server reachability from within and outside the cluster |
| **Positive Test** | |
| **Preconditions** | API server is Running; RBAC allows the test service account; `kubectl` or `curl` against `https://<kube-apiserver>` works |
| **Test Command** | `kubectl get nodes`; or `curl -sS https://<kube-apiserver-ip>:6443` (use certs if required) |
| **Expected Output** | `kubectl get nodes` returns list of nodes; curl returns API responses (or 401 with valid cert) |
| **Failure Condition** | `kubectl get nodes` errors out (e.g., `net/http: TLS handshake timeout`); curl fails with connection refused or SSL error |
| **Remediation** | Check API server health (`kubectl get componentstatuses`); verify certs are mounted and valid; check kube-apiserver logs; ensure etcd is Running; confirm the test pod/service account has `get`/`list` permissions |
| **Evidence** | `kubectl get nodes` output; `curl` output; `kubectl get componentstatuses` |
| **Automated** | Yes — scripted `kubectl get nodes` or `curl` against API endpoint; assert exit code 0 |
| **Manual** | Yes — `kubectl get nodes`, `curl` against API |
| **Negative Test (NET-010-NEG)** | |
| **Preconditions** | Same as positive; a NetworkPolicy or RBAC rule blocks API server access from the test pod's namespace/service account |
| **Test Command** | Restrict the test pod's service account with a `Role` that removes `get`/`list` on `nodes`, `pods`; or apply a NetworkPolicy that blocks inbound to the API server's secure port |
| **Expected Output** | `kubectl get nodes` fails with `Forbidden`; curl against API returns error or timeout |
| **Failure Condition** | Access still works despite restrictions — indicates RBAC gap or NetworkPolicy not enforcing on the API server port |
| **Remediation** | Verify `Role`/`ClusterRole` rules are correct; check `aggregator` layer if custom API; ensure NetworkPolicy covers the API server's port(s); confirm `k8s.opsnetwork.io/enforce` is not `false` |
| **Evidence** | Role/YAML; `kubectl auth can-i` output; `curl`/error; `kubectl get networkpolicy` |
| **Automated** | Yes — scripted `kubectl get nodes` with restricted SA; assert `Forbidden` error |
| **Manual** | Yes — restrict SA, test `kubectl`, observe result |

---

## 5.11 Ceph Public + Cluster Network Paths

| Field | Details |
|---|---|
| **Test ID** | NET-011 |
| **Scope** | Ceph RGW (public) and Ceph Cluster (mon/data) network paths from cluster pods |
| **Positive Test** | |
| **Preconditions** | Ceph cluster deployed; Ceph mon/services reachable via cluster network; RGW endpoint available; RBD/CephFS CSIs deployed |
| **Test Command** | `rados -p <pool> ls` (or `rbd list`); `curl -sS http://<rgw-endpoint>/` (public endpoint); or from a pod: `rbd info <pool>/<image>` |
| **Expected Output** | Ceph commands return expected pool/image info; RGW curl returns XML/JSON response or 200 OK |
| **Failure Condition** | `rados`/`rbd` commands error out ("object store not found"); RGW curl fails (timeout, 503, DNS failure) |
| **Remediation** | Check Ceph mon services (`kubectl get pods -n ceph`); verify Ceph CRDs and endpoints; check RGW service and ingress; ensure Ceph mon/rgw are in `Ready` state; confirm network connectivity between cluster nodes and Ceph IPs |
| **Evidence** | `rados`/`rbd` output; `curl` output; `kubectl get cephcluster`, `kubectl get cephobjectstore` |
| **Automated** | Yes — scripted `rados ls` and `curl` against RGW; assert expected output |
| **Manual** | Yes — run `rados`, `curl` from a host or pod; verify Ceph dashboard |
| **Negative Test (NET-011-NEG)** | |
| **Preconditions** | Same as positive; a NetworkPolicy or security group blocks Ceph cluster traffic (mon port 3300/6789, RGW port 80/443) |
| **Test Command** | Apply a NetworkPolicy that `den`s traffic to the Ceph mon/service IPs/ports; then run the Ceph commands from NET-011 positive |
| **Expected Output** | `rados` commands fail; RGW curl times out or returns 503/connection refused |
| **Failure Condition** | Traffic passes despite blocking policy — indicates policy scope too narrow, or Ceph traffic is over a different interface/port not covered |
| **Remediation** | Verify policy `to` `ports` match Ceph mon/rgw ports (`3300`, `6789`, `80`, `443`); check `from` selector matches the pod initiating traffic; ensure the policy `order` enforces before any `allow-all`; confirm no `k8s.opsnetwork.io/enforce: "false"` |
| **Evidence** | NetworkPolicy YAML; `rados`/`rbd`/`curl` output before/after; `kubectl get networkpolicy` |
| **Automated** | Yes — apply policy, rerun NET-011, assert failure |
| **Manual** | Yes — apply policy, test manually |

---

## 5.12 Monitoring Scrape Connectivity

| Field | Details |
|---|---|
| **Test ID** | NET-012 |
| **Scope** | Monitoring stack (Prometheus/Thanos) can scrape metrics from target pods/instances; reverse connectivity (pod → Prometheus) |
| **Positive Test** | |
| **Preconditions** | Prometheus deployed; target pods have `prometheus.io/scrape` annotations or are in a `Monitor` CR; port exposure (e.g., `:9090`) |
| **Test Command** | `curl -sS http://<prometheus-node-port-or-LB>/api/v1/query?query=up`; or from Prometheus UI: target `health="up"` |
| **Expected Output** | `up{job="..."} 1` or other metric series returned; Prometheus shows all expected targets as `up` |
| **Failure Condition** | curl returns error or empty result; Prometheus target `health="down"`; "query was disabled by your rate limit" |
| **Remediation** | Check Prometheus `scrape_configs`; verify target pod annotations; ensure the metrics port is open (`kubectl port-forward`); check firewalls allowing 9090/443 from Prometheus host; verify service discovery is finding the targets |
| **Evidence** | `curl` output; Prometheus UI target list; `kubectl get service prometheus` |
| **Automated** | Yes — scripted `curl` against Prometheus; assert expected metric in output |
| **Manual** | Yes — `curl` against Prometheus, check UI |
| **Negative Test (NET-012-NEG)** | |
| **Preconditions** | Same as positive; a NetworkPolicy blocks exporter/scrape traffic from target pods to Prometheus |
| **Test Command** | Apply a NetworkPolicy that `den`s egress from the target pod's namespace on port 9090 (or the metrics port) to the Prometheus service IP; then check scrape status |
| **Expected Output** | Prometheus target goes `health="down"`; `curl` against Prometheus returns error or empty; scrape fails |
| **Failure Condition** | Target stays `health="up"` despite blocking policy — indicates policy does not cover the metrics port, or `allow-all` default overrides |
| **Remediation** | Verify policy `egress` `ports` include the metrics port (9090, 443); check `from` selector matches the target pod labels; ensure `order` does not skip the scrape rule; confirm `k8s.opsnetwork.io/enforce` is not `false` |
| **Evidence** | NetworkPolicy YAML; Prometheus UI; `curl` output; `kubectl get networkpolicy` |
| **Automated** | Yes — apply policy, rerun NET-012, assert target goes down |
| **Manual** | Yes — apply policy, check Prometheus UI, test manually |

---

## 5.13 Registry/Repository Access

| Field | Details |
|---|---|
| **Test ID** | NET-013 |
| **Scope** | Container image registry access from within the cluster (private registry, Docker Hub, GHCR, etc.) |
| **Positive Test** | |
| **Preconditions** | Registry is reachable; cluster has pull secrets if private; `imagePullPolicy: IfNotPresent` or `Always` |
| **Test Command** | `kubectl run tester --rm -i --restart=Never --image=docker.io/library/nginx:latest --rm=true`; or `crictl pull <image>` |
| **Expected Output** | Pod starts successfully; image is pulled; `kubectl describe pod tester` shows `Successfully pulled image` |
| **Failure Condition** | `ImagePullBackOff`; `rpc: error: code = NotFound; desc = unable to pull manifest`; timeout reaching registry |
| **Remediation** | Check pull secret (`kubectl get secret`); verify registry URL and connectivity (`nc <registry> 443`); ensure `NO_PROXY`/`proxy` env vars are correct; check if registry requires token authentication |
| **Evidence** | `kubectl describe pod` events; `crictl pull` output; registry access logs |
| **Automated** | Yes — scripted `kubectl run` with image pull; assert pod phase is `Running` |
| **Manual** | Yes — `crictl pull`, `docker pull` from a host |
| **Negative Test (NET-013-NEG)** | |
| **Preconditions** | Same as positive; a NetworkPolicy or firewall blocks outbound traffic to the registry IP/port |
| **Test Command** | Apply a NetworkPolicy that `den`s egress to the registry IP and port (typically 443); then run the image pull from NET-013 positive |
| **Expected Output** | Image pull fails; pod stays in `ImagePullBackOff`; `crictl pull` returns error |
| **Failure Condition** | Pull succeeds despite blocking policy — indicates policy does not cover the registry's IP range or port, or the cluster uses a local cache/mirror that bypasses the policy |
| **Remediation** | Verify policy `egress` `dest` matches the registry IP/CIDR; check `ports` include 443; ensure `from` selector matches the pulling pod's labels; confirm no `k8s.opsnetwork.io/enforce: "false"`; check `ImagePullSecrets` on the pod |
| **Evidence** | NetworkPolicy YAML; `kubectl describe pod` events; `crictl pull` output |
| **Automated** | Yes — apply policy, rerun NET-013, assert ImagePullBackOff |
| **Manual** | Yes — apply policy, test image pull manually |

---

## 5.14 OIDC/Identity Endpoints

| Field | Details |
|---|---|
| **Test ID** | NET-014 |
| **Scope** | OIDC identity provider (Keycloak, OIDC issuer) reachability from within the cluster; token issuance and validation |
| **Positive Test** | |
| **Preconditions** | OIDC issuer deployed (e.g., Keycloak); OIDC client config in platform; `kubectl` or `curl` can reach the issuer's `.well-known/openid-configuration` endpoint |
| **Test Command** | `curl -sS https://<oidc-issuer>/.well-known/openid-configuration`; or `kubectl exec` into a pod with `oauth2l` to fetch a token |
| **Expected Output** | JSON `.well-known` config returned; token fetched successfully; `kubectl auth can-i` works against RBAC-protected resources |
| **Failure Condition** | curl returns error (DNS failure, connection refused, TLS error); token request fails; `kubectl auth can-i` returns `Forbidden` |
| **Remediation** | Check OIDC issuer service/pod status; verify service type and LoadBalancer/NodePort; ensure TLS certs are valid and trusted; check `kubectl get oauthclient` or Keycloak logs; confirm network connectivity to issuer host |
| **Evidence** | `curl` output; Keycloak/OIDC logs; `kubectl get pods,services` for the OIDC component |
| **Automated** | Yes — scripted `curl` against OIDC well-known; assert JSON response contains `issuer`, `authorization_endpoint`, `token_endpoint` |
| **Manual** | Yes — `curl` against OIDC endpoint; use `oauth2l` or Keycloak admin UI to verify token flow |
| **Negative Test (NET-014-NEG)** | |
| **Preconditions** | Same as positive; a NetworkPolicy or firewall blocks outbound traffic to the OIDC issuer host/port |
| **Test Command** | Apply a NetworkPolicy that `den`s egress from the client pod's namespace to the OIDC issuer host on port 443; then run the OIDC curl/test from NET-014 positive |
| **Expected Output** | curl fails; token request fails; `kubectl auth can-i` returns `Forbidden` or times out |
| **Failure Condition** | Access still works despite blocking policy — indicates policy does not cover the issuer host, or the cluster uses a local proxy/mirror |
| **Remediation** | Verify policy `egress` `host` matches the OIDC issuer exact host; check `ports` include 443; ensure `from` selector matches the client pod labels; confirm no `k8s.opsnetwork.io/enforce: "false"` |
| **Evidence** | NetworkPolicy YAML; `curl` output before/after; `kubectl get networkpolicy` |
| **Automated** | Yes — apply policy, rerun NET-014, assert failure |
| **Manual** | Yes — apply policy, test manually |

---

## 5.15 MTU Discovery and Routing

| Field | Details |
|---|---|
| **Test ID** | NET-015 |
| **Scope** | MTU consistency across cluster network paths; fragmentation behavior; routing consistency |
| **Positive Test** | |
| **Preconditions** | All nodes use the same MTU (default 1450 for many CNIs, or configured); no oversized packets in test path |
| **Test Command** | `kubectl exec -it <pod> -- ip path-mtu 1472` (or `ping -M do -s <size> <dest-ip>` from within a pod); verify `ip mtu` on interfaces |
| **Expected Output** | MTU reported consistently; `ping` with appropriate size succeeds; no "frag needed" ICMP messages |
| **Failure Condition** | ICMP "frag needed, mtu xxx" returned; packets dropped; inconsistent MTU sizes across nodes |
| **Remediation** | Adjust CNI MTU setting; ensure jumbo frame settings are consistent; check for VPN or tunnel interfaces that change MTU; avoid `path-mtu-discovery` disabled on nodes |
| **Evidence** | `ip path-mtu` output; `ping -M do -s` results; `ifconfig` / `ip addr` MTU values |
| **Automated** | Yes — scripted MTU probe from source pod to destination; assert no fragmentation ICMP |
| **Manual** | Yes — `ip path-mtu`, `ping -M do -s` from pod and from host |
| **Negative Test (NET-015-NEG)** | |
| **Preconditions** | Same as positive; a misconfigured MTU or a tunnel that drops packets > certain size; or a NetworkPolicy that indirectly affects path MTU (unlikely but tested for completeness) |
| **Test Command** | Force a smaller MTU on a pod's interface; or send oversized packets and observe drops; or apply a policy that breaks return-path MTU discovery |
| **Expected Output** | Packets fragmented or dropped; `ping` returns "frag needed"; application reports timeouts or truncated data |
| **Failure Condition** | Oversized packets pass through despite MTU mismatch — indicates path MTU not being discovered or adjusted |
| **Remediation** | Align MTU across all nodes in the path; check for GRE/IPsec tunnels that impose additional headers; ensure CNI config MTU matches the deployment; adjust `path-mtu-discovery` if disabled |
| **Evidence** | `ip path-mtu`; `ping -M do -s`; `tcpdump` capture showing ICMP frag needed or packet loss |
| **Automated** | Yes — scripted MTU probe; assert expected ICMP or no-fragment behavior |
| **Manual** | Yes — `ip path-mtu`, `ping -M do -s` from multiple points; `tcpdump` analysis |

---

## 5.16 Time Sync Dependencies

| Field | Details |
|---|---|
| **Test ID** | NET-016 |
| **Scope** | NTP/Chrony time sync across cluster nodes and pods; clock skew impact on certs, logging, and distributed tracing |
| **Positive Test** | |
| **Preconditions** | NTP service running on nodes; `chronyd` or `ntpd` configured; cluster pods inherit host time; no firewall blocks UDP 123 |
| **Test Command** | `date` on a node; `kubectl exec <pod> -- date`; compare outputs; verify `chronyc tracking` |
| **Expected Output** | Node and pod clocks differ by < 1 second (typically < 0.01s); `chronyc tracking` shows "Internet time constant" or stable offset |
| **Failure Condition** | Clock offset > 5 seconds; `chronyc` reports "ERROR"; NTP packets dropped; pods' clocks drift significantly from host |
| **Remediation** | Open UDP 123 in both directions between nodes and any restricted network zones; check `chronyd` config; ensure firewalls allow inbound/outbound NTP; use a redundant NTP source; verify `rtc` hardware clock is functional |
| **Evidence** | `date` output (node vs pod); `chronyc tracking`; `kubectl exec` into pod and run `date`; NTP firewall rule check |
| **Automated** | Yes — scripted `date` comparison; assert offset < 1s |
| **Manual** | Yes — `date` on node, `kubectl exec` into pod, `chronyc tracking` |
| **Negative Test (NET-016-NEG)** | |
| **Preconditions** | Same as positive; a firewall or NetworkPolicy blocks UDP 123 NTP traffic between nodes and pods |
| **Test Command** | Apply a NetworkPolicy that `den`s UDP traffic on port 123; or apply a host-level firewall rule blocking NTP; then compare node and pod time |
| **Expected Output** | Pod clock drifts relative to node; `chronyc` reports inability to reach NTP server; time skew grows |
| **Failure Condition** | Time sync still works despite blocking policy — indicates policy does not cover UDP 123, or the host NTP client falls back to a different source |
| **Remediation** | Verify policy `egress/ingress` `ports` include `123/udp`; check `from`/`to` selectors match the NTP traffic path; ensure `order` enforces the NTP block; confirm `k8s.opsnetwork.io/enforce` is not `false`; open UDP 123 if time sync is critical |
| **Evidence** | NetworkPolicy YAML; `chronyc tracking` before/after; `curl`/`nc -u` NTP test; firewall logs |
| **Automated** | Yes — apply policy, rerun NET-016, assert clock offset grows beyond threshold |
| **Manual** | Yes — apply policy, check time drift manually; `chronyc` logs |

---

## 5.17 Summary Table

| Test ID | Test Name | Positive | Negative |
|---|---|---|---|
| NET-001 | Node-to-Node Communication | ✅ | ✅ |
| NET-002 | Pod-to-Pod Across Workers | ✅ | ✅ |
| NET-003 | Pod-to-Service Communication | ✅ | ✅ |
| NET-004 | DNS Resolution | ✅ | ✅ |
| NET-005 | Internal/External Service Connectivity | ✅ | ✅ |
| NET-006 | Ingress Routing | ✅ | ✅ |
| NET-007 | LB/VIP Failover | ✅ | ✅ |
| NET-008 | Cilium NetworkPolicy Enforcement | ✅ | ✅ |
| NET-009 | Cross-Namespace Communication | ✅ | ✅ |
| NET-010 | K8s API Access | ✅ | ✅ |
| NET-011 | Ceph Public + Cluster Network Paths | ✅ | ✅ |
| NET-012 | Monitoring Scrape Connectivity | ✅ | ✅ |
| NET-013 | Registry/Repository Access | ✅ | ✅ |
| NET-014 | OIDC/Identity Endpoints | ✅ | ✅ |
| NET-015 | MTU Discovery and Routing | ✅ | ✅ |
| NET-016 | Time Sync Dependencies | ✅ | ✅ |

**Total**: 17 test suites (34 tests — positive + negative pairs)

---

## Design Notes

- **Every test includes**: preconditions, test command, expected output, failure condition, remediation, evidence, and both automated and manual execution paths.
- **Negative tests** always verify that prohibited traffic is *actually blocked*, not just that a policy resource exists. Each negative test applies the policy, reruns the corresponding positive test, and asserts the expected failure.
- **No broad network access** is recommended merely to make tests pass. If a negative test consistently fails, the remediation path focuses on tightening policy selectors, adjusting policy order, or confirming the intended enforcement point — never on opening rules.
- **All tests are designed against ephemeral/lab clusters** (kind, k3s, or a dedicated test cluster). They do not deploy against production or shared clusters.
- **Illustrative example values** (CIDRs, hostnames, port numbers) are clearly marked as placeholders; operators must substitute site-specific values.
- **Covered dependencies**: MTU (NET-015), routing (NET-001, NET-002, NET-011), DNS (NET-004), firewall/NetworkPolicy (NET-008, NET-012, NET-014), time sync (NET-016).
- **No credentials or secrets** are embedded. Registry/pull secret references use generic names; operators supply their own.
- **No Git operations** are performed in the creation of this document — it is a static design document.

---

*This document is part of the SRE network-integration-testing workstream for Task 004-P11.7. All example values are illustrative/placeholders. No live or shared clusters are used in the design of these tests. Static YAML/schema checks are NOT proof of runtime functionality.*