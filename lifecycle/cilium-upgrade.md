# Section 6: CNI and Cilium Upgrade

*Illustrative only — not production-committed configurations. No live cluster is upgraded from this document. All examples are version-dependent and labeled as such.*

## 6.1 Cilium/Kubernetes compatibility

Cilium version must be compatible with the target Kubernetes version (see `lifecycle/version-compatibility-matrix.conf`). Cilium upgrades can temporarily affect pod connectivity; plan upgrade windows accordingly.

| Component | Dependency | Compatibility rule |
|---|---|---|
| Cilium agent | Kubernetes API | Cilium version must support target K8s API |
| Cilium operator | Cilium agent | Upgrade operator in lockstep with agent |
| Hubble | Cilium | Hubble version must match Cilium release |
| kube-proxy | Cilium (if replaced) | Cilium can replace kube-proxy in eBPF mode |
| IPAM/IPPool | Cilium | IPPool CIDR must not conflict with cluster CIDR |

## 6.2 Cilium upgrade paths

Supported upgrade is one Cilium minor version at a time; version-skipping is not supported. Review the Cilium upgrade notes for breaking changes (CRD changes, Helm value changes, API deprecations).

Before upgrading:

1. `cilium status` — confirm agent and operator healthy.
2. `cilium connectivity test` — record baseline connectivity.
3. Backup Cilium CRDs and policies (`cilium policy export` or `kubectl get ciliumnetworkpolicy`).
4. Confirm Hubble is enabled and reachable (if used for visibility).

## 6.3 CRD and API compatibility

Cilium CRDs (CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy, CiliumEndpoint, CiliumIdentity, CiliumIPPool, CiliumLoadBalancerIPPool) may change between releases. Conversion webhooks handle stored data migration, but:

- Review CRD schema changes in Cilium release notes.
- Do not delete Cilium CRDs as an upgrade procedure.
- Verify `kubectl get crd | grep cilium.io` after upgrade.

## 6.4 Agent and operator rollout

Upgrade Cilium via Helm (values labeled as placeholders):

```bash
# Illustrative — replace <version> with pinned value from version-compatibility-matrix.md
helm upgrade cilium cilium/cilium --version <version> \
  --set operator.replicas=2 \
  --set agent.enabled=true \
  --set hubble.enabled=true \
  --set loadBalancer.mode=disabled
```

Rollout strategy: upgrade agent DaemonSet first, then operator Deployment. Confirm each rollout before proceeding:

```bash
kubectl rollout status daemonset/cilium-agent -n kube-system
kubectl rollout status deployment/cilium-operator -n kube-system
```

## 6.5 kube-proxy replacement considerations

Cilium can replace kube-proxy in eBPF mode (`--set kubeProxyReplacement=strict`). Enabling this during an upgrade changes service traffic handling:

- Test in a staging cluster first.
- Verify `iptables`/`ipvs` rules are cleanly replaced by eBPF.
- Have a rollback plan to re-enable kube-proxy if eBPF mode causes regressions.

## 6.6 IPAM and IPPool dependencies

Cilium IPAM allocates pod IPs from IPPools. Before upgrading:

- Confirm IPPool CIDRs do not overlap with service CIDR or node CIDR.
- Verify IP allocation is healthy: `cilium ipam list`.
- Do not change IPPool ranges during the upgrade window.

## 6.7 Routing and encapsulation behavior

Cilium supports VXLAN, Geneve, and native routing. Encapsulation mode changes require node-level configuration and may temporarily disrupt cross-node traffic. Do not change encapsulation mode during a Kubernetes upgrade window; do them as separate, validated changes.

## 6.8 NetworkPolicy compatibility

CiliumNetworkPolicy resources use Cilium-specific CRDs. Verify existing policies remain valid after upgrade:

```bash
kubectl get ciliumnetworkpolicy -A
```

Test that policy enforcement still allows required traffic and denies unintended traffic after upgrade.

## 6.9 Cluster connectivity validation

After Cilium upgrade, validate:

```bash
# Illustrative — connectivity test between two test pods
kubectl exec client-pod -- curl -s -o /dev/null -w "%{http_code}" http://server-pod:8080
# Expected: 200

# DNS resolution from a pod
kubectl exec client-pod -- nslookup kubernetes.default
# Expected: cluster IP resolved

# External connectivity (if allowed by egress policy)
kubectl exec client-pod -- curl -sI https://harbor.internal/
# Expected: 200/301 (internal registry reachable)
```

Run `cilium connectivity test` after upgrade to validate pod-to-pod, pod-to-service, DNS, external, and cross-worker traffic.

## 6.10 Hubble visibility

If Hubble is used, confirm it is healthy after upgrade:

```bash
cilium hubble status
cilium hubble observe --since 1m
```

## 6.11 Rollback limitations

Cilium rollback is not a simple Helm downgrade:

- CRD conversion webhooks may not support downgrading stored policy resources.
- eBPF programs loaded by the new agent may not be cleanly unloaded by an older agent.
- Rollback to a previous Cilium minor version requires specialist review; test in staging first.

Forward-fix (upgrade to a newer patch release) is preferred over rollback.

## 6.12 Upgrades that temporarily affect connectivity

The following can cause brief connectivity interruptions; schedule in maintenance windows:

- Cilium agent DaemonSet rollout (eBPF program reload on each node).
- kube-proxy replacement mode change.
- Encapsulation mode change.
- IPPool CIDR changes.

Detect regressions via `cilium connectivity test`, Hubble flow drops, and application health checks.

---

*SND 004-P11.6 — CNI and Cilium Upgrade (illustrative)*
