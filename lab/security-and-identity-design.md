# Security and Identity Design (TASK 006)

## 1. Purpose
Plan identity, authentication, authorization, secrets, certificates, and recovery for the Lab. No actual secrets, domains, or identity integration settings are invented. All values are placeholders.

## 2. Identity architecture
| Component | Role | Placement | Notes |
|---|---|---|---|
| Keycloak | Centralized OIDC/SAML identity (ADR-0031) | Management cluster | Realms, SSO, MFA, LDAP/SAML connectors |
| Active Directory / LDAP | Optional directory sync | External | Keycloak connects as client; not required for Lab |
| Kubernetes RBAC | Cluster authorization | Each cluster | ClusterRole/RoleBinding, PSS restricted baseline |
| Vault / OpenBao | Secret management (ADR-0016) | Dedicated hosts outside clusters | PKI, secrets engine, transit |

Identity options:
- **Local identity only**: Keycloak with local users/realms. Simplest for Lab; no external dependency.
- **AD-integrated**: Keycloak connects to Active Directory/LDAP for user sync. Requires `<DC_INTERNAL>`, LDAPS (636) or LDAP (389), service account. Do not invent domain names or service credentials.

Recommendation for initial Lab: local identity in Keycloak; add AD/LDAP integration after the Lab is validated.

## 3. Authentication and authorization flow
- Users authenticate to Keycloak (OIDC) → obtain tokens → access Rancher UI, Argo CD UI, Grafana, Kubernetes via kubectl OIDC exec plugin.
- One kubeconfig per user or group with the OIDC exec plugin; never a shared client certificate.
- Automation tokens from `kubectl create token` with short duration, stored in CI secret store.
- Kubernetes RBAC: PSS restricted baseline enforced; Gatekeeper/Kyverno constraints for admission control.

## 4. Certificate authority and cert-manager
- cert-manager manages TLS certificates for ingress, webhooks, internal services.
- Issuer: Vault PKI issuer (preferred) or self-signed bootstrapper for the Lab.
- cert-manager depends on the Kubernetes API for normal operation; existing certificates continue serving traffic during a control-plane outage (management plane vs data plane distinction).
- Do not issue real public-domain certificates for the Lab. Use internal DNS names and self-signed/internal CA.

## 5. Secret recovery path
Critical: define recovery before any secret is stored.

- **Vault unseal**: initial unseal keys stored offline (printed or in a sealed envelope), not in the cluster. Shamir shares distributed to named custodians.
- **Vault storage backend**: integrated Raft on 3 dedicated hosts (ADR-0016), **not** etcd. Vault is independent of the Kubernetes control plane; losing a cluster does not by itself lose Vault secrets.
- **Keycloak**: PostgreSQL backend. Requires database backup/restore procedure.
- **Recovery if Keycloak is unavailable**: local emergency admin account in Keycloak; break-glass kubeconfig with static admin credentials for cluster recovery.
- **Recovery if Vault is unavailable**: restore Vault from its own storage snapshot plus offline unseal material and root token (ADR-0025). Vault backup and Kubernetes backup are separate procedures; Velero does not include Vault data.

Do not store unseal keys or backup credentials in Git, in the cluster, or in any image.

## 6. BMC and hypervisor access control
- IPMI/BMC access for out-of-band installation: dedicated management network, strong credentials, no public exposure.
- Hypervisor access: role-based, MFA where supported, audit logging.
- Administrative access paths: ops workstation → LB VIPs (443, 22) → management cluster → workload clusters.

## 7. Circular dependencies and bootstrap credential risks
| Circular dependency | Resolution |
|---|---|
| Keycloak needs K8s API (OIDC discovery) | Bootstrap K8s API first with static admin credentials; add Keycloak OIDC after |
| Vault uses integrated Raft on dedicated hosts (ADR-0016); restore Vault first per ADR-0025 | Deploy Vault before Management Cluster restore; Vault is independent of etcd |
| cert-manager needs K8s API | cert-manager deployed after K8s API healthy |
| Harbor needs K8s + storage | Bootstrap local registry first; deploy Harbor after K8s + storage |

Bootstrap order (summary): infrastructure → OS → network/DNS/NTP → local bootstrap registry → K8s control plane → CNI → storage → identity/secrets → management services → registries.

## 8. Open questions
1. Is Active Directory available for identity integration, or is local Keycloak identity acceptable for the Lab?
2. Who are the named custodians for Vault unseal shares?
3. Is there an internal CA for TLS certificates, or does the Lab use self-signed certs?
4. Is there a break-glass / emergency access procedure for cluster recovery?
