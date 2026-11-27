# Calico CNI Deployment Guide

Calico is an alternative CNI to Cilium. Use Calico when you need BGP routing,
network policy enforcement without eBPF, or compatibility with kernels that
cannot run Cilium's eBPF datapath.

## Prerequisites

- Kubernetes cluster is deployed with `kube_network_plugin: calico` in Kubespray
  group vars, OR the cluster is running with no CNI yet.
- `kubectl` is configured to target the cluster.
- Nodes have IP forwarding enabled (`net.ipv4.ip_forward = 1`).
- Bridge netfilter is enabled (`net.bridge.bridge-nf-call-iptables = 1`).

## Step 1 — Install Calico via Operator

```bash
kubectl create namespace tigera-operator

kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml
```

Wait for the operator:

```bash
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=300s
```

## Step 2 — Create Installation Custom Resource

```yaml
# calico-installation.yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: calico
spec:
  calicoNetwork:
    ipPools:
      - blockSize: 24
        cidr: 10.30.0.0/16
        encapsulation: VXLAN
        natOutgoing: Enabled
        nodeSelector: all()
  variant: Calico
```

```bash
kubectl apply -f calico-installation.yaml
```

## Step 3 — Create API CRD

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/custom-resources.yaml
```

## Step 4 — Wait for Calico to Be Ready

```bash
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl -n calico-system rollout status deployment/calico-kube-controllers --timeout=300s
```

## Step 5 — Verify CNI Health

```bash
# All Calico pods running
kubectl -n calico-system get pods

# Calico node status
kubectl -n calico-system get daemonset calico-node

# Verify IP pools
calicoctl ipam pool show --show-ip 2>/dev/null || \
  kubectl -n calico-system exec -it deployment/calico-kube-controllers -- calicoctl ipam pool show

# Pod-to-pod connectivity
kubectl run --rm -i --tty --image=busybox connectivity-test -- \
  ping -c 3 10.30.1.100  # replace with another pod IP
```

## Step 6 — Configure Network Policy (Optional)

Calico network policies are applied via `NetworkPolicy` resources:

```yaml
# allow-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: default
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

```bash
kubectl apply -f allow-dns.yaml
```

## Rollback

```bash
kubectl delete -f calico-installation.yaml
kubectl delete -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/custom-resources.yaml
kubectl delete -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml
kubectl delete namespace calico-system tigera-operator
```

> **Note:** Calico and Cilium cannot run simultaneously. If switching from Cilium,
> uninstall Cilium first and drain/rejoin nodes to clear CNI state.
