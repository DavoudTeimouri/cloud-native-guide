# READINESS-OPERATIONAL

*مثالی است — پیکربندی‌های production-confirmed نیست. هیچ polymerization از این سند به یک Cluster زنده اعمال نمی‌شود.*

## READINESS-ARCH-1. READINESS-MODEL

م델 READINESS-CAPABLE برای 14 لایه زیرساخت و پلتفرم، هر کدام با: وابستگی‌های حیاتی، دامنه‌های شکست، شاخص‌های سلامت/READINESS، الزام بکاپ، Procedure بازیابی، Validation بازیابی، مالکیت عملیات، وابستگی‌های مانیتورینگ و هشدار. تفکیک بازیابی پلتفرم- پهنا از بازیابی komponent- individuelles.

## READINESS-ARCH-2. READINESS-COMPONENTS

| لایه | وابستگی‌های حیاتی | دامنه شکست | شاخص READINESS | بکاپ | بازیابی | مالکیت |
|---|---|---|---|---|---|---|
| زیرساخت فیزیکی/مجازی | Energy, Network | rack, host | node Ready | بکاپ host | جایگزینی host | زیرساخت |
| OS | Kernel, Packages | host | systemd services | بکاپ OS | reinstall OS | OS- Admin |
| K8s Control Plane | etcd, API Server | control-plane node | API healthy | etcd snapshot | etcd restore | پلتفرم |
| CNI | kube-dns | network | pod reachable | CNI config | CNI redeploy | شبکه |
| Ceph/Rook-Ceph | MON quorum | storage domain | PG active+clean | Ceph snapshot | OSD replace | ذخیره |
| Rancher | K8s clusters | management domain | cluster registered | Rancher backup | Rancher redeploy | مدیریت |
| Nexus/Harbor | DB, blob storage | registry node | API healthy | repo backup | repo restore | república- 저장 |
| HAProxy/Nginx/Keepalived | backend VIP | edge domain | LB healthy | proxy config | proxy redeploy | شبکه |
| Prometheus/Grafana/Alertmanager/Thanos | TSDB storage | monitoring domain | targets up | monitoring backup | monitoring redeploy | نظارت |
| Loki/Fluent Bit | chunk storage | logging domain | ingestion up | log backup | log redeploy | نظارت |
| Vault/OpenBao, Keycloak | seal/unseal, DB | identity domain | Vault unsealed | Vault snapshot | Vault restore | امنیت |
| Argo CD, Ingress, cert-manager | Git repo, certs | gitops domain | apps synced | Git + Argo CD DB | Argo CD sync | gitops |
| security/admission policy | Gatekeeper/Kyverno | policy domain | policies enforced | policy export | policy reapply | امنیت |

## READINESS-ARCH-3. PLATFORM vs COMPONENT

 بازیابی پلتفرم- پهنا: کلaster از ابتدا (control plane → CNI → storage → ingress → Argo CD → apps).
 بازیابی komponent- individuelles: یک سرویس (مثلاً Harbor) بدون touching کلaster.

---

*SND 004-P11.5 — READINESS-OPERATIONAL (illustrative)*
