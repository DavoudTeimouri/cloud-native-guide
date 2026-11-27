# Reference architecture diagram

```mermaid
graph TD
    subgraph External["External / DMZ"]
        LB[(External LB VIP)]
    end

    subgraph Mgmt["Management Cluster"]
        subgraph CP["Control Plane (3, stacked etcd)"]
            CP1[etcd + API]
            CP2[etcd + API]
            CP3[etcd + API]
        end
        subgraph MW["Infra Workers"]
            RAN[Rancher]
            ARGO[Argo CD]
            KC[Keycloak]
            VAULT[Vault]
            PROM[Prometheus/Grafana]
        end
    end

    subgraph App["Application Cluster(s)"]
        subgraph ACP["Control Plane (3, stacked etcd)"]
            ACP1[etcd + API]
            ACP2[etcd + API]
            ACP3[etcd + API]
        end
        subgraph AW["Workers"]
            GEN[General workers]
            GPU[GPU workers]
            STO[Storage-facing workers]
        end
    end

    subgraph Storage["Storage"]
        CEPH[(Ceph MON/MGR/OSD/RGW)]
    end

    subgraph Repos["Repositories / Registries"]
        HAR[Harbor]
        NEX[Nexus]
        GIT[GitLab]
    end

    LB --> CP1
    LB --> RAN
    CP1 --> CEPH
    RAN --> ARGO
    ARGO --> AW
    VAULT --> AW
    HAR --> AW
    NEX --> AW
    GIT --> ARGO
```

## Purpose
Reference architecture showing layers: external LB, management cluster (control plane + infra workers), application clusters (control plane + workers), storage, and repositories/registries.

## Related
- [Overview (1.1 Architecture)](../../01-overview-and-architecture/1.1-project-introduction-and-goals.md)
- [Shared ADRs (ADR-0002, ADR-0006, ADR-0007, ADR-0010)](../../shared/decision-records/index.md)
