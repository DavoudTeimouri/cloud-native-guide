# NetworkPolicy Examples

## A. Purpose and scope

Example Kubernetes NetworkPolicy resources for the platform. Cilium is the CNI and supports standard NetworkPolicy plus Cilium-specific extensions.

## B. Default deny-all

Apply to every namespace as a baseline:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: <namespace>
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

## C. Allow DNS

All pods need DNS resolution:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: <namespace>
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

## D. Allow ingress from specific namespace

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-frontend
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
      podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

## E. Cilium-specific: L7 policy

Cilium supports L7 (HTTP) policy beyond standard NetworkPolicy:

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
  namespace: backend
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEntities:
    - cluster
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/healthz"
```

## F. Verification

```bash
# Check NetworkPolicy exists
kubectl get networkpolicy -n <namespace>

# Test connectivity is blocked
kubectl run test --rm -i --tty --image=registry.internal/tools/curl:1.0 -- curl -v http://backend:8080

# Test connectivity is allowed
kubectl run test --rm -i --tty --image=registry.internal/tools/curl:1.0 -- curl -v http://backend:8080/healthz

# Check Cilium policy enforcement
cilium policy list
```

## G. Cross-references

- `kubernetes/networking/cilium.md` — Cilium CNI
- `decisions/ADR-0006-cni-selection.md` — CNI selection rationale
- `network-matrix/network-communication-matrix.md` — Traffic flow matrix
