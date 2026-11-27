# Traffic flow diagram

```mermaid
graph LR
    User[User / Client]
    LB[(External LB VIP)]
    Ingress[Ingress Controller]
    SVC[Service]
    Pod[Pod]
    CEPH[(Ceph)]

    User -->|HTTPS| LB
    LB -->|L4| Ingress
    Ingress -->|L7| SVC
    SVC --> Pod
    Pod --> CEPH
```

## Purpose
Traffic flow from external user through load balancer and ingress to a pod and storage.

## Related
- [05 · Load Balancers (5.1 Architecture)](../../05-load-balancers/5.1-architecture.md)
- [Shared network matrix](../../shared/network-matrix/index.md)
