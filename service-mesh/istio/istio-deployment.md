# Istio Service Mesh Deployment

## Overview

Istio provides service-to-service authentication, authorization, traffic management, and observability. This document covers the deployment of Istio in ambient mode (preferred) and sidecar mode (when required).

## Prerequisites

- Kubernetes cluster v1.31+
- Cilium CNI with eBPF enabled
- MetalLB or external load balancer for ingress gateway
- cert-manager for TLS certificate management
- Internal Harbor registry with Istio images mirrored

## Version Matrix

| Istio Version | Kubernetes | Supported Until |
|---|---|---|
| 1.24.x | 1.31 - 1.34 | Per upstream support |
| 1.23.x | 1.30 - 1.33 | Per upstream support |

Refer to `compatibility/version-matrix.md` for the pinned version.

## Deployment Modes

### Ambient Mode (Default, Recommended)

Ambient mode uses a per-node ztunnel for mTLS and optional L7 waypoint proxies. No sidecar injection per pod.

```bash
# Install Istio ambient
istioctl install --set profile=ambient -y

# Verify
istioctl verify-install
kubectl get pods -n istio-system
```

**Components**:
- `istiod` - Control plane (1-3 replicas)
- `ztunnel` - Per-node daemon for mTLS (DaemonSet)
- `istio-ingressgateway` - External ingress (Deployment, L4/L7)
- `istio-egressgateway` - Optional egress gateway

**Advantages**:
- Lower per-pod resource overhead
- No application restart required for mesh join
- ztunnel failure affects only node-local pods

**Trade-offs**:
- L7 authorization requires waypoint proxies
- A ztunnel fault affects every pod on the node

### Sidecar Mode (When Required)

Sidecar mode injects an Envoy proxy into each pod.

```bash
# Install Istio sidecar
istioctl install --set profile=default -y

# Enable sidecar injection for namespace
kubectl label namespace <namespace> istio-injection=enabled

# Restart pods to inject sidecar
kubectl rollout restart deployment -n <namespace>
```

**Use when**:
- Per-pod L7 policies required without waypoint
- Legacy workload compatibility
- Explicit Envoy configuration needed

## Configuration

### Control Plane

```yaml
# istio-operator.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-control-plane
  namespace: istio-system
spec:
  profile: ambient
  values:
    pilot:
      traceSampling: 1.0
    global:
      meshID: cloud-native-stack
      multiCluster:
        clusterName: management
      defaultNodeSelector:
        kubernetes.io/os: linux
      logging:
        level: "default:info"
      tracer:
        zipkin:
          address: jaeger-collector.observability:9411
    cni:
      enabled: false  # Cilium handles CNI
    ztunnel:
      enabled: true
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: 500m
          memory: 512Mi
```

### Ingress Gateway

```yaml
# ingress-gateway.yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: external-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: ISTIO_MUTUAL
    hosts:
    - "*.internal.example.com"
```

### Waypoint Proxy (Ambient L7)

```yaml
# waypoint.yaml
apiVersion: networking.istio.io/v1beta1
kind: Waypoint
metadata:
  name: apps-waypoint
  namespace: apps
spec:
  replicas: 2
```

```yaml
# L7 AuthorizationPolicy
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: apps-read-only
  namespace: apps
spec:
  selector:
    matchLabels:
      app: api-server
  rules:
  - when:
    - key: request.auth.claims[groups]
      values: ["apps-readers"]
    to:
    - operation:
        methods: ["GET"]
```

## Certificate Management

Istio uses cert-manager for external TLS:

```yaml
# cert-manager ClusterIssuer for Istio
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: vault-issuer
spec:
  vault:
    path: pki_int/sign/istio
    server: https://vault.internal:8200
    auth:
      kubernetes:
        role: cert-manager
```

Gateway TLS:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: external-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: istio-ingressgateway-certs
    hosts:
    - "*.internal.example.com"
```

## mTLS Configuration

### Ambient Mode

```yaml
# PeerAuthentication for ambient
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

### Sidecar Mode

```yaml
# PeerAuthentication for sidecar
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

## Offline Installation

All Istio images must be mirrored to internal Harbor:

```bash
# Images to mirror (for Istio 1.24.0)
docker pull docker.io/istio/pilot:1.24.0
docker pull docker.io/istio/proxyv2:1.24.0
docker pull docker.io/istio/install-cni:1.24.0
docker pull docker.io/istio/ztunnel:1.24.0

# Tag and push to internal Harbor
docker tag docker.io/istio/pilot:1.24.0 harbor.internal/istio/pilot:1.24.0
docker push harbor.internal/istio/pilot:1.24.0
# ... repeat for all images
```

Offline install:

```bash
istioctl install \
  --set hub=harbor.internal/istio \
  --set tag=1.24.0 \
  --set profile=ambient \
  -y
```

## Validation

```bash
# Check control plane
istioctl verify-install
istioctl proxy-status

# Check ztunnel (ambient)
kubectl get pods -n istio-system -l app=ztunnel

# Check mTLS
istioctl authn tls-check <pod>.<namespace>

# Check sidecar injection (if enabled)
kubectl get pods -n <namespace> -o jsonpath='{.items[*].spec.containers[*].name}' | grep istio-proxy

# Check waypoints (ambient L7)
kubectl get waypoints -A
kubectl get pods -n <namespace> -l istio.io/waypoint-for
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| ztunnel pods CrashLoopBackOff | CNI conflict with Cilium | Ensure `cni.enabled: false` in IstioOperator |
| Ingress gateway no external IP | MetalLB not configured | Verify IPAddressPool and L2Advertisement |
| mTLS not working | PeerAuthentication missing | Apply STRICT mode PeerAuthentication |
| Waypoint not receiving traffic | Missing AuthorizationPolicy | Create AuthorizationPolicy targeting waypoint |
| High latency | Too many waypoints | Consolidate waypoints per namespace |

## Upgrade Procedure

1. Review Istio release notes for breaking changes
2. Mirror new images to internal Harbor
3. Test in staging cluster
4. Canary upgrade: `istioctl upgrade --set revision=1-24-1`
5. Verify with `istioctl verify-install`
6. Switch traffic to new revision
7. Remove old revision

## References

- [Istio Official Documentation](https://istio.io/latest/docs/)
- [Ambient Mode Deep Dive](https://istio.io/latest/docs/ambient/)
- [Service Mesh Evaluation](../evaluation.md)
- [Architecture Decision: Service Mesh](../../decisions/ADR-0009-service-mesh-adoption.md)

---

*Status: DRAFT | Owner: Platform Team | Last reviewed: 2026-11-24*