# Fleet vs Argo CD Decision Matrix



## Use Cases



| Situation | Recommended Tool | Rationale |

|---|---|---|

| **Cluster registration and lifecycle** (provisioning, deprovisioning, labeling, tainting) | **Fleet** | Fleet manages the Rancher cluster lifecycle: registration tokens, kubeconfig distribution, and cluster-level configuration. Applications are deployed afterward via Argo CD. |

| **Baseline add-on deployment** (monitoring, logging, ingress, policy, cert-manager) | **Fleet** | Fleet `GitRepo` resources deploy cluster-scoped add-ons to every managed cluster consistently. |

| **Application workload deployment** (team services, Helm charts, K8s manifests) | **Argo CD** | Argo CD owns application namespaces and deployment objects. ApplicationSets drive multi-environment spreads. |

| **Multi-tenant fleet of clusters** (10+ clusters, per-team isolation) | **Fleet + Argo CD** (combined) | Fleet handles cluster-level concerns; Argo CD handles per-application GitOps within each cluster. See the ownership table in `automation/gitlab-ci/gitlab-ansible-design.md` §7.4. |

| **Canary / blue-green deployments** | **Argo CD** | Argo CD application sync policies support automated canary, blue-green, and rolling strategies with health-based promotion. |

| **Application-level rollback** | **Argo CD** | `argocd app rollback` operates against the Application resource history. |

| **GitOps for platform-level resources** (ClusterRoleBindings, CRDs, namespace templates) | **Fleet** (or Argo CD via app-of-apps) | Fleet can push baseline CRDs; the app-of-apps pattern in `management-cluster/argocd/argocd.md` §G uses Argo CD for platform bootstrap. |

| **Migration from one management plane to another** | **Fleet + Argo CD** (coordinated) | See migration criteria below. |



## Ownership Boundaries



| Resource Type | Owner | Tool | Notes |

|---|---|---|---|

| Cluster registration token | **Fleet** | Rancher | Short-lived; rotates automatically. |

| kubeconfig distribution | **Fleet** | Rancher | Embeds Rancher server URL and CA. |

| Baseline add-ons (monitoring, logging, ingress, policy) | **Fleet** | Fleet GitRepo | Deployed to `monitoring`, `logging`, `ingress-nginx`, `gatekeeper-system`, `cert-manager` namespaces. |

| Application deployments | **Argo CD** | Argo CD Application | Per-team `AppProject` with restricted destinations. |

| Namespace creation | **Fleet** | Fleet | Baseline namespaces created by add-ons. |

| Application namespace resources | **Argo CD** | Argo CD Application | All workload objects (Deployments, Services, etc.). |

| RBAC for applications | **Argo CD** | Argo CD Application + AppProject | Project-scoped policies via Keycloak group mapping. |

| Network policies (baseline) | **Fleet** | Fleet GitRepo | Applied to infrastructure namespaces. |

| Pod Security Standards (baseline) | **Fleet** | Fleet GitRepo | Applied via Gatekeeper/OPA constraints. |

| Application-level NetworkPolicies | **Argo CD** | Argo CD Application | Per-workload policies. |

| **Never** deploy an application workload via Fleet. **Never** deploy baseline add-ons via Argo CD. | — | — | Ownership inversion causes drift and merge conflicts. |



**Normative reference**: the ownership table in `automation/gitlab-ci/gitlab-ansible-design.md` §7.4 is authoritative.



## Migration Criteria



Migrate from Argo CD to Fleet (or vice versa) when the following conditions are met:



| Direction | Trigger | Action |

|---|---|---|

| **Argo CD → Fleet** | Workload deployment logic needs to be cluster-registration-aware, or you want to co-locate application manifests with baseline add-ons in a single Git repo. | 1. Convert Application/ApplicationSet resources to Fleet `GitRepo`/`Application` CRs. 2. Remove Argo CD Application resources for the same workloads. 3. Update `AppProject` destinations to align with Fleet-added namespaces. 4. Verify no resource is owned by both tools per the ownership table. |

| **Fleet → Argo CD** | You need advanced deployment strategies (canary, blue-green) or per-application rollback that Fleet does not natively support. | 1. Migrate baseline add-on GitRepos to Argo CD app-of-apps or Helm releases. 2. Convert application workloads to Argo CD Applications. 3. Remove Fleet `GitRepo` resources for application paths. 4. Re-register clusters via Argo CD repo connections if Fleet is decommissioned. |

| **Fleet → Argo CD** (management plane switch) | Replacing Rancher with an alternative management plane (Headlamp + Argo CD, KubeSphere, or no UI). | 1. Follow migration steps in `management-cluster/alternatives.md` §Migration between options. 2. Register clusters with the new plane. 3. Keep Argo CD Application resources pointing at the new cluster endpoints. 4. Remove Fleet resources only after every user has a kubeconfig path that does not go through the old plane. |

| **Argo CD → Fleet** (consolidation) | Fleet already manages cluster registration and baseline add-ons, and you want to unify under a single controller. | 1. Import existing Argo CD Applications into Fleet as Application CRs (if Fleet supports it) or recreate them via Git. 2. Remove Argo CD Application resources. 3. Update any ApplicationSet generators to Fleet-compatible formats. 4. Validate that `check_links.py` reports 0 broken links across the repo. |



## Cross-References



- `management-cluster/argocd/argocd.md` — Argo CD detailed configuration, application model, and operations

- `management-cluster/rancher/fleet-integration.md` — Fleet architecture, cluster registration, and baseline add-on deployment

- `automation/gitlab-ci/gitlab-ansible-design.md` §7.4 — Normative ownership table (conflicts are resolved per this table)

- `management-cluster/alternatives.md` — Migration between management planes (Rancher → Headlamp/Argo CD paths)

- `decisions/ADR-0014-gitops-strategy-and-division-of-labour-with-ansible.md` — GitOps strategy context for the division of labour between Fleet and Argo CD
