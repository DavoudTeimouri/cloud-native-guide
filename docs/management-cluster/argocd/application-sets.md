# Argo CD ApplicationSets

## A. Purpose and scope

ApplicationSets enable scalable, dynamic application creation in Argo CD. Instead of managing individual Application manifests, a single ApplicationSet definition generates multiple Applications based on defined generators and templates. This document covers the core patterns for building, managing, and onboarding applications using ApplicationSets.

Cross-references: `management-cluster/argocd/argocd.md`, `management-cluster/argocd/application-sync.md`, `management-cluster/argocd/drift-detection.md`.

## B. ApplicationSet generators

ApplicationSets support multiple generator types to produce the list of target Applications. Choosing the right generator depends on the fleet structure and update cadence.

### 1. list generator

Static, declarative element list. Best for small, stable fleets that change infrequently.

```yaml
generators:
  - list:
      elements:
        - service: payments
          tier: gold
        - service: ledger
          tier: gold
        - service: notify
          tier: silver
```

### 2. git generator

Watches a Git repository for a directory structure. Each subdirectory under the configured path becomes an Application. Ideal for directory-of-services layouts where each service has its own k8s manifests folder.

```yaml
generators:
  - git:
      repoURL: https://gitlab.internal/apps/payments
      revision: main
      directories:
        - path: k8s/*
```

### 3. cluster generator

Targets applications deployed to specific clusters. Useful when the same Application configuration must be rendered across multiple Kubernetes clusters.

```yaml
generators:
  - cluster:
      name: cluster-1
      server: https://kubernetes.default.svc
```

### 4. matrix generator

Cartesian product of element lists. Each combination of elements produces one Application. Useful for combining multiple dimensions (e.g., services × tiers × regions).

```yaml
generators:
  - matrix:
      elements:
        - service: payments
        - service: ledger
        - tier: gold
        - tier: silver
```

### 5. random generatör

Produces a random set of Applications. Each Application receives a random `generatorName` and `generatorKind` in its metadata. Useful for canary or A/B testing fleets.

```yaml
generators:
  - random:
      count: 5
```

### 6. fillgenerator generator

Fills a range of sequential numbers or strings. Commonly used with `template` to generate Applications with indexed names.

```yaml
generators:
  - fillgenerator:
      start: 1
      end: 10
      step: 1
```

## C. Template application spec

The `template` field defines the spec for each generated Application. Only the fields that differ between Applications need to be included; shared configuration is typically set at the AppProject level.

```yaml
template:
  metadata:
    name: '{{service}}'
    labels:
      app: '{{service}}'
      tier: '{{tier}}'
  spec:
    project: team-payments
    source:
      repoURL: https://gitlab.internal/apps/payments
      targetRevision: main
      path: 'k8s/{{service}}'
    destination:
      server: https://kubernetes.default.svc
      namespace: '{{service}}'
    syncPolicy:
      automated:
        prune: true
        selfHeal: true
      syncOptions:
        - CreateNamespace=true
```

**Key template functions**: `{{variable}}` references are resolved from generator `elements`. Unknown variables resolve to empty strings; guard templates against missing values using Go template `default` function or conditional logic.

## D. Target revision management

The `targetRevision` field controls which git ref the generated Applications track. This is critical for fleet-wide version alignment and rollback strategies.

| Value | Behavior |
|---|---|
| `main` | Tracks the default branch; Applications update when the branch tip advances. |
| A specific branch name (e.g., `release-1.8`) | All generated Applications track that branch; updates require a branch push. |
| `$patch` | Updates to the patch version of the current `main` commit; useful for hotfix pipelines. |
| `$auto` | Auto-detects the default branch and tracks it; the most common default. |

**Best practice**: Pin `targetRevision: main` for continuous deployment pipelines. Use a named branch (e.g., `release-1.8`) for release trains. Avoid `$patch` unless the CI pipeline explicitly manages patch bumps.

## E. Sync policies

ApplicationSets inherit sync policy behavior, but per-Application sync policies can override the generator-level defaults. The `syncPolicy` in the template applies to every generated Application.

```yaml
template:
  spec:
    syncPolicy:
      automated:
        prune: true
        selfHeal: true
      syncOptions:
        - CreateNamespace=true
      retry:
        limit: 5
        backoff: {duration: 15s, factor: 2, maxDuration: 5m}
```

**Sync policy fields**:
- `automated.prune`: Delete resources no longer present in Git.
- `automated.selfHeal`: Auto-sync when the Application detects drift.
- `automated.syncOptions`: Additional options such as `CreateNamespace` or `ServerSideApply`.
- `retry.limit`: Maximum sync retry attempts.
- `retry.backoff`: Exponential backoff configuration.
- `syncOptions`: One-time sync options passed to the Argo CD sync API.

**Per-application override**: To change sync behavior for a specific generated Application, edit that Application's spec directly via `argocd app set` or by modifying the generated Application manifest in Git.

## F. ApplicationSet-based application onboarding

Onboarding new applications via ApplicationSets reduces the manual workload of creating individual Application manifests. The onboarding pattern depends on the generator type.

### 1. Git-based onboarding (git generator)

1. Add a new subdirectory under the watched path (e.g., `k8s/new-service/`).
2. Ensure the directory contains valid k8s manifests or a Helm chart.
3. Argo CD automatically creates an Application for the new directory on the next sync.
4. The Application name is derived from the directory name; customize using the `name` template field if needed.

### 2. List-based onboarding (list generator)

1. Edit the ApplicationSet's `spec.generators[0].list.elements` array to add a new element.
2. Commit the change to the ApplicationSet manifest.
3. Argo CD reconciles and creates the new Application on the next sync.
4. The Application name follows the `template.metadata.name` pattern (e.g., `new-service`).

### 3. Cluster generator onboarding

1. Ensure the target cluster is reachable from the Argo CD repo-server.
2. Add a new `cluster` generator entry with the cluster name and server URL.
3. Generated Applications receive the cluster's context; override `destination.server` in the template if needed.

### 4. Matrix generator onboarding

1. Add new elements to any of the matrix dimension lists.
2. The Cartesian product expands automatically; no need to re-list combinations.
3. Verify the generated Application count matches `matrix.size` in the Argo CD UI.

### 5. Verifying onboarding

```bash
# List all applications generated by an ApplicationSet
argocd app list -l argocd.argoproj.io/application-set-name=microservices

# Describe a specific generated application
argocd app get payments-api -n argocd

# View the generated Application manifest
argocd app view payments-api --output yaml
```

**Onboarding checklist**:
- [ ] Generator configuration is correct for the target fleet structure.
- [ ] Template spec includes all required fields: `source.repoURL`, `destination.server`, `destination.namespace`, `syncPolicy`.
- [ ] `targetRevision` is set appropriately for the deployment model (main, release branch, `$patch`).
- [ ] `syncPolicy.automated` is configured per reliability requirements (prune, selfHeal).
- [ ] AppProject has destination and resource whitelists that allow the new Application's namespace and resource types.
- [ ] Run `argocd app list` to confirm the new Application appeared after the commit.
- [ ] Run `argocd app sync <name> --dry-run` to verify the Application is readable by Argo CD.