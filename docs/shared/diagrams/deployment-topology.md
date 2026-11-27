# Deployment topology diagram

```mermaid
graph TD
    subgraph CP["Control Plane (3 nodes)"]
    c1[k8s-cp-1]
    c2[k8s-cp-2]
    c3[k8s-cp-3]
    end
    subgraph ETCD["etcd (stacked)"]
    e1[etcd]
    e2[etcd]
    e3[etcd]
    end
    subgraph WK["Workers (3+)"]
    w1[k8s-w-1]
    w2[k8s-w-2]
    w3[k8s-w-3]
    end
    subgraph GPU["GPU workers"]
    g1[k8s-gpu-1]
    end

    c1 --- c2 --- c3
    e1 --- e2 --- e3
    c1 --> w1
    c2 --> w2
    c3 --> w3
    w1 --> g1
```

## Purpose
Deployment topology showing 3-node control plane with stacked etcd, workers, and optional GPU workers.

## Related
- [Overview (1.1 Architecture)](../../01-overview-and-architecture/1.1-project-introduction-and-goals.md)
- [Kubernetes (6.1 Architecture)](../../06-kubernetes-infrastructure/6.1-kubernetes-architecture.md)
