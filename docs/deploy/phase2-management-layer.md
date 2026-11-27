# Phase 2 — Management Layer

**Purpose**: Deploy the centralized management plane consisting of a Kubespray-managed management cluster, Rancher HA, Keycloak OIDC, Argo CD GitOps, Vault secrets management, and platform services (Harbor + GitLab). All components integrate via OIDC and External Secrets with Vault.

**Entry criteria**:
- Phase 1 (cluster foundation) complete: Kubernetes cluster(s) provisioned with Kubespray, networking (Calico/Cilium), and external load balancer reachable.
- DNS: `management.internal`, `rancher.internal`, `keycloak.internal`, `argocd.internal`, `harbor.internal`, `gitlab.internal`, `postgres.platform-db.internal` all resolve.
- TLS certificates provisioned for all internal hostnames.
- PostgreSQL external database provisioned and reachable.
- Harbor internal registry running.
- GitLab instance running with internal user directory.

**Exit criteria**:
- Management cluster running Kubespray with 3 control-plane + 3 infra workers (no worker nodes shared with application clusters per ADR-0010/0011).
- Rancher HA installed and reachable via `rancher.internal` with TLS.
- Keycloak OIDC with three realms (platform, ai, external) and six clients configured.
- Argo CD HA deployed with Redis sentinel + PostgreSQL, OIDC to Keycloak, External Secrets for client secrets, ServerSideApply enabled.
- Vault deployed on 3 dedicated hosts outside management cluster with Raft storage, Shamir 3-of-5 unseal, and auth methods configured.
- Harbor + GitLab integrated with Keycloak OIDC and Vault secret delivery.
- All validation checks pass; rollback procedures documented and tested.

---

## 1. Management Cluster Build (Kubespray, hosts-mgmt.ini)

Build a dedicated management cluster separate from application clusters. Worker nodes must NOT be shared with app clusters per ADR-0010/0011.

### A. Inventory — hosts-mgmt.ini

```ini
[mgmt-control-plane]
mgmt-cp-1 ansible_host=<ip1>
mgmt-cp-2 ansible_host=<ip2>
mgmt-cp-3 ansible_host=<ip3>

[mgmt-workers]
mgmt-w-1 ansible_host=<ip4>
mgmt-w-2 ansible_host=<ip5>
mgmt-w-3 ansible_host=<ip6>

[mgmt:children:vars]
# Ensure worker nodes are NOT tagged for app clusters
kubespray_node_role=worker
kubespray_node_role=control-plane

# Etcd on control-plane nodes only
etcd_endpoints="https://mgmt-cp-1:2379,https://mgmt-cp-2:2379,https://mgmt-cp-3:2379"

# Networking (Cilium recommended)
cluster_network=10.30.0.0/16
service_network=10.32.0.0/16

# Container runtime
container_runtime=containerd

# TLS bootstrap
admin_access_ip=<bastion-or-jump-host-ip>

# Do NOT overlap with app-cluster node pools
```

### B. Kubespray deployment

```bash
# Clone Kubespray and checkout the release
git clone https://github.com/kubernetes-sigs/kubespray.git
cd kubespray
git checkout release-2.26

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Generate inventory from template or create new
cp -rf inventory/sample inventory/mgmt
# Edit inventory/mgmt/hosts-mgmt.ini per the template above

# Scale to 3 control-plane nodes + 3 infra workers
ansible-inventory -i inventory/mgmt/hosts-mgmt.ini -y > inventory.json

# Apply Kubespray site.yml — this builds the management cluster
ansible-playbook -i inventory/mgmt/hosts-mgmt.ini site.yml --become --become-user root

# Verify three control-plane nodes are ready
kubectl get nodes -A | grep -E "control-plane|etcd"

# Verify no worker nodes overlap with app clusters
kubectl get nodes -o wide | grep mgmt-w
```

### C. Validation

```bash
# All mgmt CP + worker nodes Ready
kubectl get nodes -A | grep mgmt

# Etcd member list (3 members expected)
for node in mgmt-cp-1 mgmt-cp-2 mgmt-cp-3; do
  ssh $node "etcdctl member list -w table https://localhost:2379 \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert /etc/kubernetes/pki/etcd/peer.crt \
    --key /etc/kubernetes/pki/etcd/peer.key"
done
```

### D. Exit criteria

- 3 control-plane nodes + 3 worker nodes in `Ready` state.
- Etcd cluster healthy with 3 members.
- No worker nodes tagged with app-cluster labels.
- Kubeconfig at `/etc/kubernetes/admin.conf` valid.

### E. Rollback

- Re-run Kubespray with the original `hosts.ini` (pre-mgmt scaling).
- Destroy and recreate the management cluster from scratch if etcd data is corrupted.

---

## 2. Rancher HA Installation (Helm, rancher-stable repo)

Install Rancher HA with 3 replicas, external PostgreSQL, TLS termination, and private registry `harbor.internal`.

### A. Prerequisites (from installation-ha.md section F-H)

- External PostgreSQL database (provisioned, reachable at `<postgres-host>:5432`).
- TLS certificates for `rancher.internal` (generated via cert-manager or openssl).
- DNS: `rancher.internal` resolving to HAProxy/VIP.
- HAProxy or cloud LB configured port 443 TLS to three Rancher control-plane nodes.

### B. Add Helm repo and install

```bash
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm repo update
```

### C. values-ha.yaml

```yaml
hostname: rancher.internal
replicas: 3
ingress:
  enabled: true
  ingressClassName: nginx
  tls:
    source: secret
    existingSecret: rancher-tls
privateRegistry: harbor.internal
rancherImage: harbor.internal/platform/rancher/rancher
systemDefaultRegistry: harbor.internal
useBundledSystemChart: true
bootstrapPassword: ""            # from External Secrets, not inline
extraEnv:
  - name: CATTLE_SYSTEM_DB_TYPE
    value: "postgresql"
  - name: CATTLE_SYSTEM_DB_URL
    value: "postgresql://rancher:***@<postgres-host>:5432/rancher?sslmode=require"
  - name: CATTLE_ETCD_SERVERS
    value: "https://etcd-1.internal:2379,https://etcd-2.internal:2379,https://etcd-3.internal:2379"
```

### D. Install Rancher

```bash
helm install rancher rancher-stable/rancher \
  --namespace cattle-system --create-namespace \
  --values values-ha.yaml
```

### E. Validation

```bash
# 3 Rancher server pods Running
kubectl -n cattle-system get pods -l app=rancher

# ETCD member status (3 members)
for node in etcd-1.internal etcd-2.internal etcd-3.internal; do
  kubectl run etcd-check-$node --image=bitnami/etcd --rm -i --restart=Never \
    --command -- etcdctl member list \
    -w endpoints=https://$node:2379 \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert /etc/kubernetes/pki/etcd/peer.crt \
    --key /etc/kubernetes/pki/etcd/peer.key
done

# Rancher UI health via LB
curl -k https://rancher.internal/v3/health

# Expected: {"status":"healthy"}
```

### F. Exit criteria

- 3 Rancher server pods in `Running` state.
- ETCD cluster with 3 healthy members.
- Rancher UI reachable at `https://rancher.internal/v3/health` returning `healthy`.
- Load balancer distributing traffic across all 3 nodes.

### G. Rollback

- `helm uninstall rancher -n cattle-system`
- Re-install with previous `values-ha.yaml` snapshot.
- If etcd data lost, restore from PostgreSQL backup.

---

## 3. Register Application Clusters into Rancher (Agent Manifest)

Register workload clusters via the Rancher agent join command.

### A. Generate agent join token

```bash
# From Rancher UI: Cluster Actions → Add cluster → Custom → Linux → Manual join settings
# Copy the full join command including the TLS bootstrap token
```

### B. Agent manifest template (Linux worker)

```bash
cat > join-cluster.sh << 'EOF'
#!/bin/bash
# Replace <RANCHER_IP> with the Rancher VIP or LB DNS
sudo docker run -d --rm \
  --privileged \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /etc/kubernetes:/etc/kubernetes \
  rancher/rancher-agent:<version> \
  --server-url https://<rancher.internal>:9343 \
  --token <TOKEN> \
  --etcd-image bitnami/etcd:<version> \
  --before-pull-image
EOF
chmod +x join-cluster.sh
```

### C. Distribute and run on each application cluster

```bash
# On each app cluster (e.g., 3 clusters: workload-1, workload-2, workload-3)
./join-cluster.sh
```

### D. Verify registration

```bash
# In Rancher UI: Clusters → Your clusters should appear as "pending" → "active"
kubectl get clusters -A

# From Rancher
kubectl get nodes -A
```

### E. Validation

- 3 application clusters registered and showing `Active` in Rancher.
- Fleet and workload scheduling visible in Rancher.
- Cross-cluster `kubectl` access via Rancher cluster explorer.

### F. Rollback

- Remove cluster from Rancher UI: Cluster Actions → Delete.
- Wipe etcd data on the application cluster and re-start from scratch.

---

## 4. Keycloak OIDC Provider Setup

Keycloak is the identity broker for the platform with three realms and six clients.

### A. Deploy Keycloak (from keycloak.md)

```bash
# Chart values subset (from keycloak.md section B)
cat > keycloak-values.yaml << 'EOF'
replicas: 2
image:
  repository: harbor.internal/platform/keycloak/keycloak
  tag: "26.8.1"
dbchecker:
  image:
    repository: harbor.internal/platform/keycloak/keycloak
extraEnv:
  - name: KC_HOSTNAME
    value: keycloak.internal
  - name: KC_HTTP_ENABLED
    value: "true"
  - name: KC_PROXY_HEADERS
    value: xforwarded
  - name: KC_HEALTH_ENABLED
    value: "true"
  - name: KC_DB
    value: postgres
  - name: KC_DB_URL_HOST
    value: postgres.platform-db.internal
  - name: KC_DB_URL_DATABASE
    value: keycloak
  - name: KC_DB_USERNAME
    value: keycloak
  - name: KC_DB_PASSWORD
    value: ${DB_PASSWORD}   # from ExternalSecret
  - name: JAVA_OPTS_APPEND
    value: "-XX:MaxRAMPercentage=70.0"
command:
  - "/opt/keycloak/bin/kc.sh"
  - "start"
  - "--http-enabled=true"
  - "--hostname-strict=false"
EOF

helm install keycloak oci://harbor.internal/helm/keycloak \
  --namespace keycloak --create-namespace \
  --values keycloak-values.yaml
```

### B. Realms (from keycloak.md section C)

| Realm | Purpose | Upstream |
|---|---|---|
| `platform` | Operators and developers of the platform | AD/LDAP federation + local break-glass |
| `ai` | Service accounts and tenant identities for inference API | Local |
| `external` | Federates to AD/LDAP and exposes to other realms | AD/LDAP |

**AD/LDAP federation for `external` realm** (from keycloak.md section C):

```bash
kc.sh config ldap --hostname=ldap.internal --port=636 --protocol=ldaps \
  --truststore-path=... --truststore-password=... \
  --bind-dn="cn=svc-keycloak,ou=services,dc=example,dc=com" \
  --bind-credential="$BIND_PASSWORD" \
  --users-query="(&(objectClass=person)(sAMAccountType=805306368)(uid={0}))" \
  --username-attribute=uid \
  --first-name-attribute=givenName \
  --last-name-attribute=sn \
  --email-attribute=mail \
  --group-query="(&(objectClass=group)(member={0}))" \
  --groups-attribute=memberOf
```

### C. Clients (from keycloak.md section D)

| Client | Type | Redirect URI | Notes |
|---|---|---|---|
| `rancher` | Confidential | `https://rancher.internal/oidc/authorize` | groups + uid claims required |
| `argoccd` | Confidential | `https://argocd.internal/auth/callback` | Same |
| `grafana` | Confidential | `https://grafana.internal/login/generic_oauth` | email + groups required |
| `harbor` | Confidential | `https://harbor.internal/c/oidc/callback` | — |
| `gitlab` | Confidential | `https://gitlab.internal/users/auth/oidc/callback` | — |
| `ai-gateway` | Confidential | `https://llm.internal/callback` | Token validation for inference |

**Protocol mappers (required by Rancher + Argo CD)**:

1. **groups mapper**:
   - Mapper type: `Group membership`
   - Claim name: `groups`
   - Full path: `off`
   - Add to ID token: `on`
   - Add to access token: `on`

2. **uid mapper**:
   - Mapper type: `User Attribute`
   - User attribute: `uid`
   - Claim name: `uid`
   - Add to ID token: `on`

### D. Roles and group mapping (from keycloak.md section E)

| Keycloak group | Platform role | Grants |
|---|---|---|
| `platform-admins` | Administrator | Everything |
| `platform-operators` | Operator | Cluster and platform operations, no secret values |
| `developers` | Developer | Own namespaces only |
| `auditors` | Auditor | Read-only access to logs and audit data |
| `team-<name>` | Team member | The team's namespace and its Argo CD project |

### E. Validation

```bash
# Discovery document
curl -k https://keycloak.internal/realms/platform/.well-known/openid-configuration | jq .

# Token with groups claim
curl -sk -X POST https://keycloak.internal/realms/platform/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=argocd-ci \
  -d client_secret="$SECRET" | jq -r '.access_token' | cut -d. -f2 | base64 -d 2>/dev/null | jq .groups

# Expected: groups and uid present for federated user
```

### F. Exit criteria

- Keycloak reachable at `https://keycloak.internal` with 2 replicas running.
- Three realms (platform, ai, external) configured.
- Six clients (rancher, argocd, grafana, harbor, gitlab, ai-gateway) configured.
- `groups` and `uid` protocol mappers present and active.
- Group-to-platform-role mapping functional.

### G. Rollback

- `helm uninstall keycloak -n keycloak`
- Restore PostgreSQL database from backup.
- Re-deploy from Helm chart with previous values.

---

## 5. Argo CD Deployment (HA: Redis Sentinel + PostgreSQL)

Deploy Argo CD in HA mode with Redis sentinel, PostgreSQL backend, OIDC to Keycloak, External Secrets for clientSecret, and ServerSideApply.

### A. Infrastructure prerequisites

- PostgreSQL database reachable at `postgres.argocd.internal`.
- Redis Sentinel deployment reachable at `redis-sentinel.argocd.internal:26379`.
- TLS certificates for `argocd.internal`.

### B. Install Argo CD (from argocd.md sections B-F)

```bash
# Create namespace
kubectl create namespace argocd

# Install Argo CD with HA values (custom values below)
helm repo add argo-cd https://argoproj.github.io/argo-helm
helm repo update

# Apply custom HA values
cat > argocd-values-ha.yaml << 'EOF'
server:
  replicaCount: 3
  ha:
    enabled: true
    persistence:
      enabled: true
      type: pvc
      storageSize: 10Gi
      existingClaim: argocd-pvc
  # PostgreSQL connection
  postgresql:
    enabled: false    # Use external PostgreSQL
    # Use external Redis Sentinel instead
  extraArgs:
    - --server-server-https-chauffeur-privacy-mode=off

  # OIDC Config (from argocd.md section F)
  oidc:
    enabled: true
    name: Keycloak
    issuer: https://keycloak.internal/realms/platform
    clientID: argocd
    clientSecret: $oidc-keycloak:oidc.clientSecret   # ExternalSecret
    requestedScopes: openid,profile,email,groups
    groupMappingEnabled: "true"
    groupsClaim: groups
    groupMapping:
      "platform-admins": role:admin
      "platform-operators": role:admin
      "developers": role:readonly

  # Redis Sentinel config
  redis:
    sentinel:
      enabled: true
      sentinelCount: 3
      service: redis-sentinel
      port: 26379

  # ServerSideApply
  serverSuite:
    serverSideApply: true

  # External Secrets setup (see section 7)
  externalSecrets:
    enabled: true
EOF

helm install argocd argo-cd/argo-cd \
  --namespace argocd --create-namespace \
  --values argocd-values-ha.yaml
```

### C. External Secrets for clientSecret

```yaml
# ClusterSecretStore for Vault (see section 7)
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-secret-store
spec:
  provider:
    vault:
      server: "https://vault.platform.internal:8200"
      path: "secret/data/keycloak/oidc"
      authentication:
        token:
          secretRef:
            name: vault-token
            key: token

# ExternalSecret for Argo CD OIDC client secret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: argocd-oidc-client-secret
  namespace: argocd
spec:
  secretStoreRef:
    name: vault-secret-store
    kind: ClusterSecretStore
  target:
    name: oidc-keycloak-client-secret
    type: Opaque
  data:
    - secretKey: clientSecret
      remoteRef:
        key: oidc
        property: clientSecret
```

### D. Validation

```bash
# Argo CD server pods Ready
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-server

# Verify OIDC configuration
kubectl -n argocd get configmap argocd-cm -o jsonpath='{.data.oidc.config}'

# Login via OIDC
argocd login argocd.internal

# List applications
argocd app list

# Expected: Applications list shows synced apps; OIDC login succeeds without inline password.
```

### E. Exit criteria

- 3 Argo CD server pods in `Running` state.
- PostgreSQL backend reachable and storing Argo CD state.
- Redis Sentinel providing HA for session state.
- OIDC login to Argo CD UI succeeds via Keycloak.
- ExternalSecret for `clientSecret` populated from Vault.
- `serverSideApply: true` active in Argo CD server config.

### F. Rollback

- `helm uninstall argocd -n argocd`
- Wipe PostgreSQL and Redis data; re-install from previous values backup.
- Restore Argo CD state from etcd/PG backup if needed.

---

## 6. Vault Deployment (Dedicated Hosts Outside Management Cluster)

Deploy Vault on 3 dedicated hosts with Raft storage, Shamir 3-of-5 unseal, and multiple auth methods.

### A. Infrastructure — 3 Vault hosts outside management cluster

```ini
[vault-nodes]
vault-1 ansible_host=<vault-node-1-ip>
vault-2 ansible_host=<vault-node-2-ip>
vault-3 ansible_host=<vault-node-3-ip>
```

### B. Vault Raft configuration (3 nodes, Shamir 3-of-5)

```bash
# Initialize the Vault cluster
vault operator init -key-shares=5 -threshold=3 \
  -root-token-format=hex \
  > /vault/initializer-output.json

# Unseal each node with 3 of 5 shares (distribute shares securely)
for i in 1 2 3; do
  vault operator unseal $(jq -r ".unseal_keys_b64[$((i-1))]" /vault/initializer-output.json)
done

# Root token (keep in password manager, never in repo)
ROOT_TOKEN=$(jq -r ".root_token" /vault/initializer-output.json)
vault login $ROOT_TOKEN
```

### C. Auth methods (from vault-architecture.md)

| Auth Method | Configuration |
|---|---|
| **OIDC via Keycloak** | Vault OIDC auth pointing to `https://keycloak.internal/realms/platform`; groups claim mapped to policies. |
| **AppRole** | Role ID + Secret ID stored in External Secrets; machines fetch tokens at startup. |
| **Kubernetes auth** | `kubernetes_auth_backend` for in-cluster service accounts; role binding scoped per namespace. |

**Example: OIDC auth method**

```bash
vault auth enable oidc keycloak-oidc \
  -path=keycloak-oidc \
  -default-role=platform-user \
  oidc_discovery_url="https://keycloak.internal/realms/platform/platform/.well-known/openid-configuration"
```

**Example: AppRole**

```bash
# Create role
vault role-create -description "Argo CD deployment role" \
  -policy=argocd-policy \
  -period=72h \
  -max-ttl=12h \
  argocd-role

# Generate secret ID (rotate regularly)
vault write -f auth/approle/role/argocd-role/secret-id
```

**Example: Kubernetes auth**

```bash
# Create K8s auth backend
vault auth enable kubernetes k8s \
  -map-server="https://kubernetes.default.svc"

# Configure role
vault write auth/kubernetes/role/ns-role \
  bound_service_account_names=harbor-sa \
  bound_service_account_namespaces=harbor-system \
  policies=harbor-policy
```

### D. Secret delivery methods

| Method | Description |
|---|---|
| **Vault Agent Injector** | Sidecar that injects secrets into pods via annotations; uses `sidecar.va.hashicorp.com/inject REAL` and `sidecar.va.hashicorp.com/inject-literal` |
| **External Secrets Operator** | Syncs Vault secrets to K8s `Secret`; referenced by Argo CD, Keycloak, etc. |
| **CSI driver** | `vault-secrets-csi` mounts secrets as volumes into pods. |

**Example: Vault Agent Injector annotation**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harbor-repo-server
  annotations:
    vault.hashicorp.com/role: vault-role
    vault.hashicorp.com/secret-volume-path: "/vault/secrets"
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-status: "update"
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/role: vault-role
        vault.hashicorp.com/secret-volume-path: "/vault/secrets"
    spec:
      containers:
        - name: repo-server
          volumeMounts:
            - name: vault secrets
              mountPath: /vault/secrets
      volumes:
        - name: vault secrets
          vaultSecret:
            secretName: vault-secrets
```

### E. Validation

```bash
# Seal/unseal status
vault status

# OIDC auth login
vault login -method=oidc role=platform-user

# AppRole login
vault write auth/approle/login role=argocd-role secret-id=$(cat /tmp/secret-id) user-id="argocd"

# Kubernetes auth login (from within a pod)
vault write auth/kubernetes/login role=ns-role

# List secrets engine
vault secrets list

# Expected: Vault 3-node Raft cluster healthy; all auth methods operational.
```

### F. Exit criteria

- 3 Vault nodes running with Raft storage healthy (`vault status` shows `Sealed: false`).
- Shamir unseal: 3 of 5 shares configured and operational.
- Auth methods: OIDC (Keycloak), AppRole, Kubernetes — all responding.
- Secret delivery: Vault Agent Injector and External Secrets syncing secrets to K8s.
- Policies attached to roles granting least-privilege access.

### G. Rollback

- `vault operator raft remove-node <node-id>` to remove failed node.
- Re-initialize Vault if Raft quorum lost.
- Rotate all secret IDs and OIDC client secrets after rollback.

---

## 7. Platform Services: Harbor + GitLab Integration with Keycloak OIDC and Vault

Integrate Harbor container registry and GitLab source control with Keycloak OIDC and Vault secret delivery.

### A. Harbor configuration (Keycloak OIDC + Vault)

```yaml
# values-harbor.yaml (from platform-services index)
harbor:
  config:
    # External URL
    ui_url: https://harbor.internal

    # Keycloak OIDC integration
    oauth2:
      enabled: true
      clientID: harbor
      clientSecret: $harbor:oidc.clientSecret   # from ExternalSecret
      discovery: https://keycloak.internal/realms/platform/.well-known/openid-configuration
      usernameClaim: uid
      groupsClaim: groups
      autoRegister: true

    # Token duration
    tokenDuration: 24h
    tokenMaxRefresh: 24h

    # PostgreSQL (external)
    database:
      type: postgres
      host: postgres.platform-db.internal
      port: 5432
      database: harbor
      username: harbor
      password: ${HARBOR_DB_PASSWORD}   # from ExternalSecret

    # Redis
    redis:
      host: redis.platform.internal
      port: 6379

    # Trust CA for internal TLS
    trustedProxy:
      enabled: true

    # Proxy protocol
    protocol: https
```

### B. GitLab configuration (Keycloak OIDC + Vault)

```yaml
# GitLab config (from automation/ or via Helm)
gitlab:
  oauth:
    enable: true
    external_url: https://gitlab.internal

    gitlab_rails:
      oauth2:
        client_id: gitlab
        client_secret: $gitlab:oidc.clientSecret   # from ExternalSecret
        auth_uri: https://keycloak.internal/realms/platform/protocol/openid-connect/auth
        token_uri: https://keycloak.internal/realms/platform/protocol/openid-connect/token
        user_info_uri: https://keycloak.internal/realms/platform/protocol/openid-connect/userinfo
        scope: openid profile email groups

  # Vault-integrated secrets
  secret_store:
    type: vault
    vault_url: https://vault.platform.internal:8200
    vault_token_secret: vault-token   # referenced from K8s secret
```

### C. Vault-backed secrets for Harbor + GitLab

```yaml
# ExternalSecret for Harbor clientSecret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: harbor-oidc-client-secret
  namespace: harbor-system
spec:
  secretStoreRef:
    name: vault-secret-store
    kind: ClusterSecretStore
  target:
    name: harbor-oidc-secret
    type: Opaque
  data:
    - secretKey: clientSecret
      remoteRef:
        key: harbor
        property: oidc.clientSecret

# ExternalSecret for GitLab clientSecret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: gitlab-oidc-client-secret
  namespace: gitlab-system
spec:
  secretStoreRef:
    name: vault-secret-store
    kind: ClusterSecretStore
  target:
    name: gitlab-oidc-secret
    type: Opaque
  data:
    - secretKey: clientSecret
      remoteRef:
        key: gitlab
        property: oidc.clientSecret
```

### D. Validation

```bash
# Harbor UI reachable at https://harbor.internal with Keycloak login
curl -k https://harbor.internal/api/v2.0/users/me -H "Authorization: Bearer $(vault token lookup)"

# GitLab UI reachable at https://gitlab.internal with Keycloak login
curl -k https://gitlab.internal/api/v4/user -H "Authorization: Bearer $(vault token lookup)"

# Harbor registry push/pull test
docker tag myimage harbor.internal/myimage:latest
docker push harbor.internal/myimage:latest

# GitLab API authenticated via OIDC token
gitlab personal token or OIDC session verified via UI.

# Vault secrets synced to Harbor + GitLab Secrets
kubectl get secret -n harbor-system vault-secrets
kubectl get secret -n gitlab-system vault-secrets
```

### E. Exit criteria

- Harbor UI reachable at `https://harbor.internal`; Keycloak OIDC login works.
- GitLab UI reachable at `https://gitlab.internal`; Keycloak OIDC login works.
- Harbor + GitLab OIDC client secrets populated from Vault via External Secrets.
- Image push/pull to Harbor functional.
- GitLab repo cloning functional with Keycloak-authenticated user.
- Vault secrets (DB passwords, API keys) synced to both Harbor and GitLab configurations.

### F. Rollback

- `helm uninstall harbor -n harbor-system` (if Helm-deployed).
- Revert ExternalSecret configurations to previous values.
- Restore Harbor and GitLab databases from backup.
- Rotate all OIDC client secrets and Vault tokens.

---

## Summary Checklist — Phase 2 Complete

| # | Component | Status |
|---|---|---|
| 1 | Management cluster (Kubespray, 3 CP + 3 workers, no share with app clusters) | ✅ / ❌ |
| 2 | Rancher HA (Helm, 3 replicas, hostname, TLS, harbor.internal registry) | ✅ / ❌ |
| 3 | App clusters registered via agent manifest | ✅ / ❌ |
| 4 | Keycloak OIDC (3 realms: platform/ai/external; 6 clients: rancher/argocd/grafana/harbor/gitlab/ai-gateway) | ✅ / ❌ |
| 5 | Argo CD HA (Redis sentinel + PostgreSQL, OIDC to Keycloak, ExternalSecret clientSecret, ServerSideApply) | ✅ / ❌ |
| 6 | Vault (3 nodes Raft, Shamir 3-of-5 unseal, OIDC/AppRole/K8s auth; Injector/External Secrets/CSI) | ✅ / ❌ |
| 7 | Harbor + GitLab (Keycloak OIDC + Vault secret delivery) | ✅ / ❌ |

**Next**: Proceed to Phase 3 — Application Workloads and GitOps Fleet if all exit criteria pass.

**References**:
- `docs/management-cluster/rancher/installation-ha.md` — Rancher HA installation
- `docs/management-cluster/argocd/argocd.md` — Argo CD GitOps
- `docs/secrets-management/vault/vault-architecture.md` — Vault architecture
- `docs/security/kubewarden.md` — Policy admission control
- `docs/deploy/choose-cluster-type.md` — Path selection
- `docs/deploy/other-deployment-methods.md` — Alternative deployment methods
- ADR-0010, ADR-0011 — Management cluster worker node separation
- ADR-0025 — Identity provider isolation
