# Section 7 — Kubernetes Network Security Policies

*Illustrative only — not production-committed configurations. Marked as such where indicated. No policies are applied to a live cluster from this document.*

---

## 7.1 Default-Deny Baseline

The baseline posture for all namespaces is **default-deny**: if no NetworkPolicy exists that permits traffic, all inbound and outbound connections are blocked. This replaces the Kubernetes default of "allow all" when any NetworkPolicy is present in a namespace.

**Important**: A namespace with zero NetworkPolicy objects still permits unrestricted traffic. The default-deny posture only takes effect once at least one NetworkPolicy is applied.

### Verification

```bash
# Confirm no policies allow unrestricted access
kubectl get networkpolicy --all-namespaces

# Verify a namespace with policies has default-deny behavior
kubectl get networkpolicy -n <namespace>
```

---

## 7.2 Namespace Isolation

NetworkPolicies scope their rules to a single namespace. A policy in `ns-a` can only affect traffic entering or leaving pods in `ns-a`. Cross-namespace isolation requires policies in both namespaces.

### Example — Isolate a Payment Namespace

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-except-mesh
  namespace: payment
spec:
  podSelector: {}              # select all pods in this namespace
  policyTypes:
    - Ingress
    - Egress

  # Ingress: only allow from the mesh gateway namespace
  ingress:
    - from:
        - podSelector:
            matchLabels:
              k8s-app: cilium
              kube-app: mesh-gateway
      ports:
        - protocol: TCP
          port: 443

  # Egress: only allow to the mesh gateway and monitoring
  egress:
    - to:
        - podSelector:
            matchLabels:
              k8s-app: cilium
              kube-app: mesh-gateway
      - to:
          - namespaceSelector:
              matchLabels:
                kubernetes.io/metadata.name: monitoring
            podSelector:
              matchLabels:
                k8s-app: prometheus
    - to:
        - namespaceSelector:
            matchLabels:
                kubernetes.io/metadata.name: monitoring
            podSelector:
              matchLabels:
                k8s-app: grafana
    ports:
      - protocol: TCP
        port: 443
```

**Policy ordering**: When multiple NetworkPolicies exist in the same namespace, they are **additive**. A pod must match the selector of at least one Ingress/Egress rule *and* not be denied by any rule. Order of creation does not matter; the effective rule set is the union of all policies.

---

## 7.3 DNS Allowances

Cluster DNS resolution must always be permitted. Use the `kube-system` namespace DNS pod labels matching your CNI.

### Example — Allow DNS Egress for All Pods

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: production
spec:
  podSelector: {}                              # apply to all pods in namespace
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns                  # or coredns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

**Dependency**: This policy assumes the cluster DNS deployment runs in `kube-system` with the `k8s-app: kube-dns` (or `coredns`) label. Verify with `kubectl get pods -n kube-system -l k8s-app`.

---

## 7.4 Application-to-Application Communication

Explicit allow rules between tiers. Both the sender's egress and the receiver's ingress must permit the connection.

### Example — Frontend → Backend API on Port 8080

```yaml
# Sender: frontend allows egress to backend API
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend-api
      ports:
        - protocol: TCP
          port: 8080

# Receiver: backend API allows ingress from frontend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend-api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

**Validation**:

```bash
# Verify allowed flow
kubectl exec -n production $(kubectl get pod -l app=frontend -o name) -- curl -s -o /dev/null -w "%{http_code}" http://<backend-api-service>:8080/healthz

# Verify blocked flow (should timeout or return error)
kubectl exec -n production $(kubectl get pod -l app=frontend -o name) -- curl -s -o /dev/null -w "%{http_code}" http://<database-service>:5432
```

---

## 7.5 Kubernetes API Access

Restrict access to the Kubernetes API server from within the cluster. This prevents compromised pods from contacting the API server.

### Example — Limit API Server Access to Trusted System Pods

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: limit-apiserver-access
  namespace: kube-system
spec:
  podSelector: {}                              # select all kube-system pods
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              k8s-app: kube-dns
              kubernetes.io/cluster-service: "true"
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
            podSelector:
              matchLabels:
                k6s-app: api-server  # not a standard label; use node selector instead
      ports:
        - protocol: TCP
          port: 443
```

**Note**: The API server endpoint is typically `https://<control-plane>:6443`. Many CNI plugins and system pods need access; restrict using node selectors or service accounts with limited RBAC rather than NetworkPolicy alone when possible.

**Verification**:

```bash
# Attempt API call from a workload pod
kubectl exec -n production $(kubectl get pod -l app=frontend -o name) -- curl -k https://<api-server>:6443/api/v1/namespaces/production/pods

# Should be denied if policy is enforced
```

---

## 7.6 Monitoring and Observability Traffic

Monitoring stack components (Prometheus, Alertmanager, Grafana) require specific allowances. Define policies per namespace.

### Example — Monitoring Scrape Egress

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring-scrape
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: kube-state-metrics
        - podSelector:
            matchLabels:
              app: node-exporter
      ports:
        - protocol: TCP
          port: 9100
        - protocol: TCP
          port: 9090
```

### Example — Allow Ingress from Prometheus to All Workloads

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-ingress
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              k8s-app: node-exporter
      ports:
        - protocol: TCP
          port: 9100
```

---

## 7.7 Storage and Ceph Traffic Considerations

Ceph (via Rook) and other storage systems have specific port requirements. Policies must allow the cluster-internal traffic that storage daemons need.

### Example — Ceph Cluster Traffic (Rook-Ceph)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ceph-cluster
  namespace: rook-ceph
spec:
  podSelector: {}                              # all rook ceph pods
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: mon
      ports:
        - protocol: TCP
          port: 6789    # MON
        - protocol: TCP
          port: 6800    # OSD
    - from:
        - podSelector:
            matchLabels:
              app: osd
      ports:
        - protocol: TCP
          port: 6800-7568    # OSD data
    - from:
        - podSelector:
            matchLabels:
              app: mds
      ports:
        - protocol: TCP
          port: 6800    # MDS
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: mon
      ports:
        - protocol: TCP
          port: 6789
        - protocol: TCP
          port: 6800
    - to:
        - podSelector:
            matchLabels:
              app: osd
      ports:
        - protocol: TCP
          port: 6800-7568
```

**Dependencies**: This policy assumes Rook-Ceph pods are labeled `app: mon`, `app: osd`, `app: mds`. Verify with `kubectl get pods -n rook-ceph -o jsonpath='{.items[*].metadata.labels.app}'`.

### Example — Ceph RGW (S3 API) Restricted

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ceph-rgw
  namespace: rook-ceph
spec:
  podSelector:
    matchLabels:
      app: rgw
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: client
      ports:
        - protocol: TCP
          port: 7480    # RGW S3 API
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: mon
      ports:
        - protocol: TCP
          port: 6789
```

---

## 7.8 Ingress and Egress Gateways

Gateway policies control traffic entering (IngressGateway) and leaving (EgressGateway) the cluster. These are typically deployed by the service mesh or ingress controller.

### Example — Ingress Gateway Allowlist

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ingress-gateway-allowlist
  namespace: ingress-gateway
spec:
  podSelector: {}                              # ingress gateway pods
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: production
          podSelector:
            matchLabels:
              app: frontend
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: staging
          podSelector:
            matchLabels:
              app: frontend
    ports:
      - protocol: TCP
        port: 443
      - protocol: TCP
        port: 80
```

### Example — Egress Gateway Allowlist

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: egress-gateway-allowlist
  namespace: egress-gateway
spec:
  podSelector: {}                              # egress gateway pods
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: production
      ports:
        - protocol: TCP
          port: 443
```

---

## 7.9 Cilium NetworkPolicy vs Standard Kubernetes NetworkPolicy

| Aspect | Kubernetes NetworkPolicy | Cilium NetworkPolicy |
|--------|-------------------------|-----------------------|
| **API version** | `networking.k8s.io/v1` | `cilium.io/v2` |
| **L7 filtering** | Not supported (layer 3/4 only) | Supported: HTTP methods, paths, headers |
| **Identity tracking** | Pod selectors only | Labels + identity; tracks across migrations |
| **Enforcement** | Depends on CNI plugin; not all plugins fully implement the API | BPF-based in-kernel enforcement; always present when Cilium is the CNI |
| **Additive behavior** | Policies are additive within a namespace; default-allow becomes default-deny once any policy exists | Same additive behavior, but Cilium merges native + Cilium policies into a single BPF rule set |
| **Service mesh integration** | None built-in | Integrates with mTLS/service mesh; can enforce identity-based rules |
| **Visibility** | Limited to `kubectl describe` | Hubble observability: live traffic flow graphs, drop counters |
| **Compatibility mode** | N/A | Can operate in native-k8s NetworkPolicy mode, but full features require Cilium CRDs |
| **Namespace scope** | Single namespace per policy | Can reference `fromEndpointSelector` across namespaces with `namespace-wide` scope |

### Cilium Policy Example — L7 HTTP Path Filtering

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-http-path
  namespace: production
spec:
  egress:
    - toports:
        - ports: ["443"]
          http:
            methods: ["GET", "HEAD"]
            paths: ["/api/*"]
  ingress:
    - fromEndpointSelector:
        matchLabels:
          app: ingress
    - toports:
        - ports: ["8080"]
          into:
            ports: ["8080"]
```

**Key difference**: The Cilium policy above filters by HTTP method and path, which a standard Kubernetes NetworkPolicy cannot express (it only allows TCP port 8080). If Cilium is the cluster CNI, Cilium policies are the effective enforcement layer for both native and Cilium rule sets.

### Policy Ordering & Additive Behavior (Cilium)

When both native Kubernetes NetworkPolicies and Cilium NetworkPolicies exist:

1. Cilium merges all rule sets into a single BPF program
2. The merged rules are **additive** — a packet must match at least one allow rule and must not be denied by any deny rule
3. Cilium processes native Kubernetes NetworkPolicy rules first, then overlays its own rules
4. If a native NetworkPolicy has `policyTypes: [Ingress]`, Cilium generates the equivalent BPF rule; if both specify conflicting ports, the more specific rule takes precedence in the BPF program

**Verification — compare enforced behavior**:

```bash
# Native K8s NP only
kubectl apply -f native-np.yaml
cilium policy list --type=ingress

# Cilium NP only (in a Cilium cluster)
kubectl apply -f cilium-np.yaml
cilium policy list

# Both present — verify merged view
kubectl apply -f native-np.yaml
kubectl apply -f cilium-np.yaml
cilium policy list --type=ingress --all-namespaces
```

---

## 7.10 Validation Checklist

- [ ] Default-deny baseline confirmed: namespace with at least one NetworkPolicy blocks all traffic not explicitly allowed
- [ ] DNS egress allowed: `kube-dns/CoreDNS` UDP+TCP 53 to `kube-system` namespace
- [ ] Kubernetes API server access restricted from workload namespaces
- [ ] Monitoring traffic allowances defined (Prometheus scrape, Alertmanager)
- [ ] Storage traffic (Ceph/Rook) policies allow MON/OSD/MDS communication
- [ ] Ingress gateway allows only expected namespace traffic
- [ ] Egress gateway allows only expected destination namespaces
- [ ] Cilium vs native NP differences documented for the cluster's CNI
- [ ] Application-to-application egress + ingress pairs verified (both directions must allow)
- [ ] No plaintext credentials in policy YAML (all placeholders labeled)
- [ ] Version-dependent examples labeled: `apiVersion: networking.k8s.io/v1` for K8s ≤1.29; `cilium.io/v2` for Cilium ≥1.13

---

*End of Section 7*