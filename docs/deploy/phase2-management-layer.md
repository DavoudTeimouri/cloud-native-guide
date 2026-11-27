<a id="step-11"></a>
## Step 11 — Management cluster build — Kubespray hosts-mgmt.ini inventory

**Purpose**: Build a dedicated management cluster with Kubespray using 3 control-plane + 3 infra workers, ensuring no worker nodes are shared with application clusters per ADR-0010/0011.

**Prerequisites**:
- Phase 1 (cluster foundation) complete: Kubernetes cluster(s) provisioned with Kubespray, networking (Calico/Cilium), and external load balancer reachable
- DNS: `management.internal` resolves to bastion/jump host IP
- TLS certificates provisioned for `management.internal`
- Administrative access to target hosts for Kubespray Ansible deployment

**Actions**:
```bash
# Clone Kubespray and checkout the release
git clone https://github.com/kubernetes-sigs/kubespray.git
cd kubespray
git checkout release-2.26

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create inventory from template
cp -rf inventory/sample inventory/mgmt
# Edit inventory/mgmt/hosts-mgmt.ini per the template below

# Edit hosts-mgmt.ini:
cat > inventory/mgmt/hosts-mgmt.ini << 'INI'
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
INI

# Generate inventory and apply Kubespray
ansible-inventory -i inventory/mgmt/hosts-mgmt.ini -y > inventory.json

# Apply Kubespray site.yml — this builds the management cluster
ansible-playbook -i inventory/mgmt/hosts-mgmt.ini site.yml --become --become-user root

# Verify three control-plane nodes are ready
kubectl get nodes -A | grep -E "control-plane|etcd"

# Verify no worker nodes overlap with app clusters
kubectl get nodes -o wide | grep mgmt-w
```

**Validation**:
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

**Expected**: 3 control-plane nodes + 3 worker nodes in `Ready` state; Etcd cluster healthy with 3 members; No worker nodes tagged with app-cluster labels; Kubeconfig at `/etc/kubernetes/admin.conf` valid.

**Navigation**:
- Previous: Step 10 (anchor `#step-step-10`)
- Next: Step 12 (anchor `#step-12`)

<a id="step-12"></a>
## Step 12 — Rancher HA installation via Helm

**Purpose**: Install Rancher HA with 3 replicas, external PostgreSQL, TLS termination, and private registry `harbor.internal`.

**Prerequisites**:
- External PostgreSQL database provisioned and reachable at `<postgres-host>:5432`
- TLS certificates for `rancher.internal` (generated via cert-manager or openssl)
- DNS: `rancher.internal` resolving to HAProxy/VIP
- HAProxy or cloud LB configured port 443 TLS to three Rancher control-plane nodes
- kubectl configured to target the management cluster

**Actions**:
```bash
# Add Rancher Helm repo and update
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm repo update

# Install Rancher HA via Helm
helm install rancher rancher-stable/rancher \
  --namespace cattle-system --create-namespace \
  --values values-ha.yaml
```

**values-ha.yaml content**:
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

**Validation**:
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

**Expected**: 3 Rancher server pods in `Running` state; ETCD cluster with 3 healthy members; Rancher UI reachable at `https://rancher.internal/v3/health` returning `healthy`; Load balancer distributing traffic across all 3 nodes.

**Navigation**:
- Previous: Step 11 (anchor `#step-11`)
- Next: Step 13 (anchor `#step-13`)

<a id="step-13"></a>
## Step 13 — Register application clusters into Rancher via agent manifest

**Purpose**: Register workload clusters into Rancher using the agent join command.

**Prerequisites**:
- Rancher HA installed and reachable via `rancher.internal` with TLS
- DNS for application clusters resolves
- kubectl configured to target the management cluster

**Actions**:
```bash
# Generate agent join token from Rancher UI
# From Rancher UI: Cluster Actions → Add cluster → Custom → Linux → Manual join settings
# Copy the full join command including the TLS bootstrap token

# Create agent join script (join-cluster.sh)
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

# Distribute and run on each application cluster
# On each app cluster (e.g., 3 clusters: workload-1, workload-2, workload-3)
./join-cluster.sh
```

**Validation**:
```bash
# In Rancher UI: Clusters → Your clusters should appear as "pending" → "active"
kubectl get clusters -A

# From Rancher
kubectl get nodes -A
```

**Expected**: 3 application clusters registered and showing `Active` in Rancher; Fleet and workload scheduling visible in Rancher; Cross-cluster `kubectl` access via Rancher cluster explorer.

**Navigation**:
- Previous: Step 12 (anchor `#step-12`)
- Next: Step 14 (anchor `#step-14`)

<a id="step-14"></a>
## Step 14 — Keycloak OIDC provider setup

**Purpose**: Deploy Keycloak as the identity broker with three realms (platform, ai, external) and six clients (rancher, argocd, grafana, harbor, gitlab, ai-gateway) including groups and uid protocol mappers.

**Prerequisites**:
- Management cluster from Step 11 running and reachable
- PostgreSQL external database provisioned and reachable at `postgres.platform-db.internal`
- DNS: `keycloak.internal` resolves to Keycloak service
- TLS certificates for `keycloak.internal`
- Helm installed on management cluster

**Actions**:
```bash
# Install Keycloak via Helm chart
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

**Realm configuration** (platform, ai, external):
```bash
# Configure realms via Keycloak admin API or UI
# Realms created: platform, ai, external
# - platform: Operators and developers of the platform
# - ai: Service accounts and tenant identities for inference API
# - external: Federates to AD/LDAP and exposes to other realms

# AD/LDAP federation for external realm
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

**Client configuration** (rancher, argocd, grafana, harbor, gitlab, ai-gateway):
```bash
# Create clients via Keycloak admin API or UI
# Clients: rancher, argocd, grafana, harbor, gitlab, ai-gateway
# All: Confidential type with appropriate redirect URIs

# Protocol mappers (required by Rancher + Argo CD)
# 1. groups mapper:
#    - Mapper type: Group membership
#    - Claim name: groups
#    - Full path: off
#    - Add to ID token: on
#    - Add to access token: on

# 2. uid mapper:
#    - Mapper type: User Attribute
#    - User attribute: uid
#    - Claim name: uid
#    - Add to ID token: on
```

**Validation**:
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

**Expected**: Keycloak reachable at `https://keycloak.internal` with 2 replicas running; Three realms (platform, ai, external) configured; Six clients (rancher, argocd, grafana, harbor, gitlab, ai-gateway) configured; `groups` and `uid` protocol mappers present and active; Group-to-platform-role mapping functional.

**Navigation**:
- Previous: Step 13 (anchor `#step-13`)
- Next: Step 15 (anchor `#step-15`)

<a id="step-15"></a>
## Step 15 — Argo CD deployment HA mode

**Purpose**: Deploy Argo CD in HA mode with Redis sentinel, PostgreSQL backend, OIDC to Keycloak, External Secrets for clientSecret, and ServerSideApply enabled.

**Prerequisites**:
- Keycloak from Step 14 running and reachable
- PostgreSQL database reachable at `postgres.argocd.internal`
- Redis Sentinel deployment reachable at `redis-sentinel.argocd.internal:26379`
- TLS certificates for `argocd.internal`
- Helm installed on management cluster

**Actions**:
```bash
# Create namespace
kubectl create namespace argocd

# Install Argo CD with HA values
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
  extraArgs:
    - --server-server-https-chauffeur-privacy-mode=off
  # OIDC Config
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
  # External Secrets setup
  externalSecrets:
    enabled: true
EOF

helm install argocd argo-cd/argo-cd \
  --namespace argocd --create-namespace \
  --values argocd-values-ha.yaml
```

**External Secrets for clientSecret** (Vault-backed):
```yaml
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

---
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

**Validation**:
```bash
# Argo CD server pods Ready
kubectl -n argocd get pods -l app.kubernetes.io/name=argocd-server

# Verify OIDC configuration
kubectl -n argocd get configmap argocd-cm -o jsonpath='{.data.oidc.config}'

# Login via OIDC
argocd login argocd.internal

# List applications
argocd app list

# Expected: Applications list shows synced apps; OIDC login succeeds without inline password; serverSideApply: true active
```

**Expected**: 3 Argo CD server pods in `Running` state; PostgreSQL backend reachable and storing Argo CD state; Redis Sentinel providing HA for session state; OIDC login to Argo CD UI succeeds via Keycloak; ExternalSecret for `clientSecret` populated from Vault; `serverSideApply: true` active in Argo CD server config.

**Navigation**:
- Previous: Step 14 (anchor `#step-14`)
- Next: Step 16 (anchor `#step-16`)

<a id="step-16"></a>
## Step 16 — Vault deployment on dedicated hosts outside management cluster

**Purpose**: Deploy Vault on 3 dedicated hosts with Raft storage, Shamir 3-of-5 unseal, and auth methods (OIDC via Keycloak, AppRole, K8s auth); secret delivery via Vault Agent Injector/External Secrets/CSI.

**Prerequisites**:
- 3 dedicated Vault hosts outside management cluster provisioned
- DNS: `vault.platform.internal` resolves to VIP or load balancer
- TLS certificates for `vault.platform.internal`
- Management cluster from Step 11 running

**Actions**:
```bash
# Define Vault hosts inventory
cat > vault-hosts.ini << 'INI'
[vault-nodes]
vault-1 ansible_host=<vault-node-1-ip>
vault-2 ansible_host=<vault-node-2-ip>
vault-3 ansible_host=<vault-node-3-ip>
INI

# Initialize the Vault cluster
vault operator init -key-shares=5 -threshold=3 \
  -root-token-format=hex \
  > /vault/initializer-output.json

# Unseal each node with 3 of 5 shares
for i in 1 2 3; do
  vault operator unseal $(jq -r ".unseal_keys_b64[$((i-1))]" /vault/initializer-output.json)
done

# Root token (keep in password manager, never in repo)
ROOT_TOKEN=$(jq -r ".root_token" /vault/initializer-output.json)
vault login $ROOT_TOKEN
```

**Auth methods configuration**:
```bash
# OIDC auth method via Keycloak
vault auth enable oidc keycloak-oidc \
  -path=keycloak-oidc \
  -default-role=platform-user \
  oidc_discovery_url="https://keycloak.internal/realms/platform/platform/.well-known/openid-configuration"

# AppRole role for machines
vault role-create -description "Argo CD deployment role" \
  -policy=argocd-policy \
  -period=72h \
  -max-ttl=12h \
  argocd-role

# Generate secret ID (rotate regularly)
vault write -f auth/approle/role/argocd-role/secret-id

# Kubernetes auth backend
vault auth enable kubernetes k8s \
  -map-server="https://kubernetes.default.svc"

# Configure K8s auth role
vault write auth/kubernetes/role/ns-role \
  bound_service_account_names=harbor-sa \
  bound_service_account_namespaces=harbor-system \
  policies=harbor-policy
```

**Secret delivery methods**:
```bash
# Vault Agent Injector example for Harbor
cat > harbor-injector.yaml << 'YAMl'
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
YAMl
```

**Validation**:
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

# Expected: Vault 3-node Raft cluster healthy; all auth methods operational
```

**Expected**: 3 Vault nodes running with Raft storage healthy (`vault status` shows `Sealed: false`); Shamir unseal: 3 of 5 shares configured and operational; Auth methods: OIDC (Keycloak), AppRole, Kubernetes — all responding; Secret delivery: Vault Agent Injector and External Secrets syncing secrets to K8s; Policies attached to roles granting least-privilege access.

**Navigation**:
- Previous: Step 15 (anchor `#step-15`)
- Next: Step 17 (anchor `#step-17`)

<a id="step-17"></a>
## Step 17 — Platform services: Harbor + GitLab integration with Keycloak OIDC and Vault

**Purpose**: Integrate Harbor container registry and GitLab source control with Keycloak OIDC and Vault secret delivery.

**Prerequisites**:
- Vault from Step 16 running and reachable
- Keycloak from Step 14 running and reachable
- DNS: `harbor.internal` and `gitlab.internal` resolves
- TLS certificates for `harbor.internal` and `gitlab.internal`

**Actions**:

```bash
# A. Harbor configuration (Keycloak OIDC + Vault)
cat > values-harbor.yaml << 'EOF'
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
    protocol: https
EOF

# Install Harbor Helm chart with values-harbor.yaml
helm install harbor harbor/harbor \
  --namespace harbor-system --create-namespace \
  --values values-harbor.yaml
```

```bash
# B. GitLab configuration (Keycloak OIDC + Vault)
cat > gitlab-values.yaml << 'EOF'
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
  secret_store:
    type: vault
    vault_url: https://vault.platform.internal:8200
    vault_token_secret: vault-token   # referenced from K8s secret
EOF

# Install/configure GitLab with values-gitlab.yaml
# (GitLab Helm chart installation with OAuth and Vault integration)
```

```bash
# C. Vault-backed secrets for Harbor + GitLab (ExternalSecrets)
# ExternalSecret for Harbor clientSecret
cat > harbor-oidc-secret.yaml << 'EOF'
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
EOF

# ExternalSecret for GitLab clientSecret
cat > gitlab-oidc-secret.yaml << 'EOF'
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
EOF

# Apply ExternalSecret manifests
kubectl apply -f harbor-oidc-secret.yaml
kubectl apply -f gitlab-oidc-secret.yaml
```

**Validation**:
```bash
# Harbor UI reachable at https://harbor.internal with Keycloak login
curl -k https://harbor.internal/api/v2.0/users/me -H "Authorization: Bearer ..."

# GitLab UI reachable at https://gitlab.internal with Keycloak login
curl -k https://gitlab.internal/api/v4/user -H "Authorization: Bearer ..."

# Harbor registry push/pull test
docker tag myimage harbor.internal/myimage:latest
docker push harbor.internal/myimage:latest

# GitLab API authenticated via OIDC session verified via UI

# Vault secrets synced to Harbor + GitLab Secrets
kubectl get secret -n harbor-system vault-secrets
kubectl get secret -n gitlab-system vault-secrets
```

**Expected**: Harbor UI reachable at `https://harbor.internal`; Keycloak OIDC login works; GitLab UI reachable at `https://gitlab.internal`; Keycloak OIDC login works; Harbor + GitLab OIDC client secrets populated from Vault via External Secrets; Image push/pull to Harbor functional; GitLab repo cloning functional with Keycloak-authenticated user; Vault secrets (DB passwords, API keys) synced to both Harbor and GitLab configurations.

**Navigation**:
- Previous: Step 16 (anchor `#step-16`)
- Next: Step 18 (anchor `#step-18`)

<a id="step-18"></a>
## Step 18 — Cross-component validation

**Purpose**: Validate OIDC login across all components and External Secrets synchronization.

**Prerequisites**:
- All previous steps complete: Rancher (12), Keycloak (14), Argo CD (15), Vault (16), Harbor + GitLab (17)
- DNS resolves for all internal hostnames

**Actions**:
```bash
# OIDC login to Rancher
curl -k https://rancher.internal/v3/auth/login \
  -d "redirect_url=https://rancher.internal/v3/console" \
  -H "Content-Type: application/x-www-form-urlencoded"

# OIDC login to Argo CD
argocd login argocd.internal --token-arg-hash=false
# Successful login returns no authentication error

# OIDC login to Grafana (if configured)
# Access via https://grafana.internal/login/generic_oauth

# OIDC login to Harbor
# Access via https://harbor.internal; login with Keycloak credentials

# OIDC login to GitLab
# Access via https://gitlab.internal; login with Keycloak credentials

# Verify External Secrets sync status
kubectl get externalsecret -A

# Verify Vault secrets are reachable
vault secrets list
```

**Expected**:
- OIDC login to Rancher/Argo CD/Grafana/Harbor/GitLab all succeed via Keycloak
- External Secrets are synced and populated in respective namespaces
- Vault secrets list returns expected secret engines and paths
- All component health checks pass

**Navigation**:
- Previous: Step 17 (anchor `#step-17`)
- Next: Step 19 (anchor `#step-19`)

<a id="step-19"></a>
## Step 19 — Exit criteria checklist

**Purpose**: Verify all Phase 2 exit criteria are met before proceeding to Phase 3.

**Exit criteria**:
- [ ] Management cluster running Kubespray with 3 control-plane + 3 infra workers (no worker nodes shared with application clusters per ADR-0010/0011)
- [ ] Rancher HA installed and reachable via `rancher.internal` with TLS
- [ ] Keycloak OIDC with three realms (platform, ai, external) and six clients configured
- [ ] Argo CD HA deployed with Redis sentinel + PostgreSQL, OIDC to Keycloak, External Secrets for client secrets, ServerSideApply enabled
- [ ] Vault deployed on 3 dedicated hosts outside management cluster with Raft storage, Shamir 3-of-5 unseal, and auth methods configured (OIDC via Keycloak, AppRole, K8s auth)
- [ ] Harbor + GitLab integrated with Keycloak OIDC and Vault secret delivery
- [ ] All validation checks pass (Step 18)
- [ ] Rollback procedures documented and tested (Step 20)

**Navigation**:
- Previous: Step 18 (anchor `#step-18`)
- Next: Step 20 (anchor `#step-20`)

<a id="step-20"></a>
## Step 20 — Rollback procedures

**Purpose**: Document and test rollback procedures for all Phase 2 components.

**Rollback procedures**:

```bash
# Management cluster rollback (Step 11)
# - Re-run Kubespray with the original hosts.ini (pre-mgmt scaling)
# - Or destroy and recreate the management cluster from scratch if etcd data is corrupted

# Rancher HA rollback (Step 12)
# - helm uninstall rancher -n cattle-system
# - Re-install with previous values-ha.yaml snapshot
# - If etcd data lost, restore from PostgreSQL backup

# Keycloak rollback (Step 14)
# - helm uninstall keycloak -n keycloak
# - Restore PostgreSQL database from backup
# - Re-deploy from Helm chart with previous values

# Argo CD rollback (Step 15)
# - helm uninstall argocd -n argocd
# - Wipe PostgreSQL and Redis data; re-install from previous values backup
# - Restore Argo CD state from etcd/PG backup if needed

# Vault rollback (Step 16)
# - vault operator raft remove-node <node-id> to remove failed node
# - Re-initialize Vault if Raft quorum lost
# - Rotate all secret IDs and OIDC client secrets after rollback

# Harbor + GitLab rollback (Step 17)
# - helm uninstall harbor -n harbor-system (if Helm-deployed)
# - Revert ExternalSecret configurations to previous values
# - Restore Harbor and GitLab databases from backup
# - Rotate all OIDC client secrets and Vault tokens
```

**Expected**: All rollback procedures documented; each procedure tested in staging environment; data recovery paths validated; rollback timeline documented (< 30 minutes for critical components).

**Navigation**:
- Previous: Step 19 (anchor `#step-19`)
- End of Phase 2 guide
