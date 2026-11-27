# Kubernetes Networking: CNI, DNS, Ingress, and Load Balancing

## CNI Plugin Options

| Plugin | Description | Key Features | Typical Use-Case |
|---|---|---|---|
| **Calico** | Widely adopted CNI using BPF fast-path. | - Scales to thousands of nodes<br>- Supports IPv4/IPv6<br>- NetworkPolicy CRDs<br>- Can run on bare metal, cloud, on-prem | General-purpose clusters, multi-cloud, where simple networking is needed |
| **Cilium** | CNI based on eBPF for observability and security. | - L7 traffic awareness<br>- Transparent encryption<br>- Kubernetes-native NetworkPolicy enhanced<br>- Integration with Hubble for visibility | Performance-sensitive workloads, need L7 observability, zero-trust networking |
| **Flannel** | Simple overlay CNI using VXLAN. | - Minimal configuration<br>- Supports etcd-backed subnet allocation<br>- Works on all CNI-compatible runtimes | Small clusters, labs, or environments where eBPF/BPF is not available |

## DNS Configuration

Kubernetes DNS is provided by **CoreDNS** by default. CoreDNS runs as a Deployment in the `kube-system` namespace and resolves:

- **Service DNS**: `my-service.my-namespace.svc.cluster.local`
- **Pod DNS**: `my-pod.my-namespace.pod.local`
- **External DNS**: Forwards external names via upstream resolvers

### Customizing CoreDNS

- Add plugins in `Corefile` ConfigMap (`kubectl -n kube-system get configmap coredns -o yaml`)
- Enable forwarder for external zones
- Configure cache TTLs, health probes, and query logging

> **SRE tip**: Monitor CoreDNS query latency and error rate as part of the cluster **Latency** SLO. A spike in DNS errors can masquerade as application latency.

## Ingress Controllers

An Ingress resource exposes HTTP/HTTPS routes from outside the cluster to services. The Ingress **controller** satisfies the request.

| Controller | Description | Key Features |
|---|---|---|
| **NGINX** | The de facto standard Ingress controller. | - Mature, wide ecosystem<br>- Supports TLS, rewrite, redirect<br>- Can run as DaemonSet or Deployment |
| **GCE** / **ALB** / **NLB** | Cloud-provider-specific controllers. | - Native integration with cloud load balancers<br>- ExternalIP handling<br>- Native support for cloud IAM |
| **Traefik** | Modern Ingress controller with dynamic config. | - Single binary, automatic cert retrieval via Let's Encrypt<br>- Middleware chaining<br>- Good for dynamic environments |

### Minimal Ingress Example

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: http-service
            port:
              number: 80
```

## Load Balancer Integration

### Service Type `LoadBalancer`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
```

- On **cloud providers**, an external IP (or hostname) is provisioned automatically.
- On **on-premises**, use **MetalLB** to assign an IP from a configured range.

### MetalLB (bare-metal load balancer)

MetalLB implements the Kubernetes `LoadBalancer` and `IPAddress` APIs using ARP announcements (Layer 2) or BGP (Layer 3).

```yaml
# ConfigMap example for MetalLB IP address pool
apiVersion: v1
kind: ConfigMap
metadata:
  namespace: metallb-system
  name: config
data:
  config: |
    address-pools:
    - name: default
      protocol: layer2
      addresses: ["192.168.100.240/28"]
```

## Network Policy Design

NetworkPolicies restrict traffic flow between pods. They are **opt-in**: if no NetworkPolicy exists, all traffic is allowed.

### Common Patterns

| Pattern | Example |
|---|---|
| **Allow only specific ingress** | ```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
spec:
  podSelector:
    matchLabels:
      app: web
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
``` |
| **Allow egress to external DNS** | ```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
spec:
  podSelector:
    matchLabels:
      app: web
  egress:
  - to:
    - ipBlock:
        ip: 8.8.8.8/32
``` |
| **Deny all ingress by default** | Create a catch-all policy `deny-all` with `spec.ingress: []` in namespaces where you want to lock down traffic. |

### Design Checklist

- [ ] Define a `default-deny` NetworkPolicy in namespaces that require strict isolation.
- [ ] Allow necessary ingress from trusted labels or namespaces.
- [ ] Allow egress for container images, package managers, and external APIs.
- [ ] Test policies with `kubectl describe networkpolicy <name>` and `kubectl get networkpolicy --all-namespaces`.
- [ ] Audit with `kubectl get networkpolicy --all-namespaces -o yaml` to ensure no accidental `allow-all`.
- [ ] Align policies with the **Error Budget** SLO: overly restrictive policies can increase failure rates during deployments.

## References

- [Calico Networking](https://docs.tigera.io/calico/latest/getting-started/kubernetes/setup/)
- [Cilium Documentation](https://docs.cilium.io/en/stable/)
- [CoreDNS Config](https://coredns.io/2019/11/18/corefile/)
- [Ingress Controllers Comparison](https://kubernetes.io/docs/concepts/services-ingress/controllers/)
- [MetalLB Quickstart](https://metallb.universe.tf/quick-start/)

---
*Generated for the cloud-native-guide repository. See also: `kubernetes/networking/cilium.md`, `kubernetes/networking/metallb.md`, `kubernetes/networking/ingress-tls-configuration.md`.*
