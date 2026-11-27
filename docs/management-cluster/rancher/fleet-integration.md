# Fleet Integration

## A. Purpose and scope

Document Fleet integration with Rancher: cluster registration, baseline add-ons through Git, GitOps workflow, and Fleet vs Argo CD ownership boundaries.

Cross-references `management-cluster/rancher/rancher.md` §Fleet, `management-cluster/argocd/argocd.md`, `automation/gitlab-ci/gitlab-ansible-design.md`.

## B. Fleet vs Argo CD ownership

Rancher manages the lifecycle of application clusters. Fleet and Argo CD have complementary but distinct roles:

| Component | Responsibility | Owns |
|-----------|--------------|------|
| Fleet | Cluster registration, baseline add-ons, cluster-level configuration | Rancher cluster resources, namespace resources, baseline add-ons |
| Argo CD | Application workloads, application-level GitOps | Application namespaces, application deployments |

**Rule: Fleet and Argo CD must never both own the same object.** The ownership table in `automation/gitlab-ci/gitlab-ansible-design.md` is normative.

## C. Fleet architecture

```
Rancher Server (management cluster)
  ├── Fleet Controller
  │     ├── GitRepo resources (cluster registration)
  │     ├── ClusterRegistration resources
  │     └── Baseline add-on bundles
  └── Kubernetes API
        ├── Managed clusters (registered via Fleet)
        └── Baseline add-ons (deployed to each cluster)
```

Fleet runs in the management cluster (cattle-fleet-system namespace) and manages:
- Cluster registration tokens and kubeconfigs
- Baseline add-ons (monitoring, logging, ingress, policy)
- Cluster-level configuration (labels, taints, annotations)

## D. Cluster registration

### 1. Generate registration token

In Rancher UI: Cluster Management → Add Cluster → Custom → Generate registration command.

The registration command includes:
- Server URL (Rancher API endpoint)
- Token (short-lived, rotates automatically)
- CA certificate (Rancher server TLS)

### 2. Register cluster via Fleet

Create a Fleet `ClusterRegistration` resource:

```yaml
apiVersion: fleet.cattle.io/v1alpha1
kind: ClusterRegistration
metadata:
  name: <cluster-name>
  namespace: fleet-default
spec:
  base64ca: <base64-encoded-CA>
  serverUrl: https://<rancher-url>
  labels:
    environment: production
    tier: application
```

### 3. Verify registration

```bash
kubectl -n fleet-local get clusters
kubectl -n fleet-local get clusterregistrations
kubectl get nodes  # On the managed cluster
```

## E. Baseline add-ons

Baseline add-ons are deployed to every managed cluster via Fleet `GitRepo` resources:

| Add-on | Purpose | Fleet target |
|--------|---------|-------------|
| Monitoring (Prometheus/Grafana) | Cluster observability | monitoring namespace |
| Logging (Fluent Bit/Loki) | Log aggregation | logging namespace |
| Ingress (NGINX) | External traffic entry | ingress-nginx namespace |
| Policy (Kyverno/OPA Gatekeeper) | Security policy enforcement | gatekeeper-system namespace |
| Cert-manager | Certificate management | cert-manager namespace |

Each add-on is a separate Fleet `GitRepo` pointing to a directory in the GitLab repository:

```yaml
apiVersion: fleet.cattle.io/v1alpha1
kind: GitRepo
metadata:
  name: baseline-monitoring
  namespace: fleet-default
spec:
  repo: git@gitlab.internal:platform/baseline-addons.git
  branch: main
  paths:
    - monitoring/
  targetNamespace: monitoring
```

## F. GitOps workflow

1. **Provision cluster**: Terraform creates VMs, Ansible configures OS
2. **Register cluster**: Fleet ClusterRegistration resource
3. **Deploy baseline add-ons**: Fleet GitRepo resources deploy monitoring, logging, ingress, policy
4. **Deploy applications**: Argo CD syncs application workloads from GitLab
5. **Monitor and reconcile**: Fleet and Argo CD continuously reconcile drift

## G. Ownership boundaries

| Resource type | Owner | Tool |
|--------------|-------|------|
| Cluster registration token | Fleet | Rancher |
| kubeconfig distribution | Fleet | Rancher |
| Baseline add-ons (monitoring, logging, ingress, policy) | Fleet | Fleet GitRepo |
| Application deployments | Argo CD | Argo CD Application |
| Namespace creation | Fleet | Fleet (baseline namespaces) |
| Application namespace resources | Argo CD | Argo CD Application |
| RBAC for applications | Argo CD | Argo CD Application |
| Network policies | Fleet (baseline) | Fleet GitRepo |
| Pod Security Standards | Fleet (baseline) | Fleet GitRepo |

**Never** deploy an application workload via Fleet. **Never** deploy baseline add-ons via Argo CD.

## H. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Cluster not showing in Rancher | Registration token expired | Generate new token, re-register |
| Baseline add-ons not deploying | Fleet GitRepo sync error | Check `fleet get gitrepo` status |
| Application drift not detected | Argo CD not syncing | Check `argocd app sync` status |
| Fleet and Argo CD conflict | Both owning same object | Remove one owner per ownership table |

## I. Cross-references

- `management-cluster/rancher/rancher.md` — Rancher deployment, Fleet context
- `management-cluster/argocd/argocd.md` — Argo CD deployment
- `automation/gitlab-ci/gitlab-ansible-design.md` — Fleet vs Argo CD ownership table (normative)
