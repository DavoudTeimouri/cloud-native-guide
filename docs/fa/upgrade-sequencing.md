# UPGRADE-SEQUENCING

*مثالی است.*

## UPGRADE-SEQUENCING-1. مدل وابستگی

چندین گروه وابستگی:
- K8s & CNI، K8s & CSI، K8s & Rancher، Ceph & Rook، cert-manager & ingress، Vault & apps، Keycloak & OIDC، Prometheus & exporters، ArgoCD & K8s API، Gatekeeper/Kyverno & admission webhooks.

پیش‌ Required‌های directional؛ ترتیب universal اعمال نمی‌شود.
ترتیبی متداول با ۱۳ مرحله و explicit gates.
مهمان‌پذیری vs سریالی.

---

*SND 004-P11.6 — upgrade-sequencing (illustrative)*
