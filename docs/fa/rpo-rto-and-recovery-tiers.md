# RPO-RTO-RECOVERY-TIERS

*مثالی است — 약속 production-committed نیست. همه مقادیر illustrative هستند.*

## RPO-RTO-RECOVERY-TIERS-1. تعریف‌ها

**RPO (Recovery Point Objective)**: حداکثر از دست دادنش‌پذیر دیتا (مثلاً ۱۵ دقیقه).
**RTO (Recovery Time Objective)**: حداکثر acceptable downtime (مثلاً ۳۰ دقیقه).
**MTD (Maximum Tolerable Downtime)**: حداکثر tolerate شده down time.
 دیتا Consistency الزامها.
 **Recovery tiers**: ۰–۴.
 **Business impact و service dependencies.**
 **Recovery order و prioritization.**

## RPO-RTO-RECOVERY-TIERS-2. 테이블 recovery tiers

| Tier | توضیح | RPO illustrative | RTO illustrative | مثال |
|---|---|---|---|---|
| ۰ | Critical،no data loss | ۰ دقیقه | < ۱۵ دقیقه | etcd control plane |
| ۱ | Low data loss | < ۱ دقیقه | < ۳۰ دقیقه | stateful workloads |
| ۲ | Moderate | < ۱۵ دقیقه | < ۲ ساعت | Ceph storage |
| ۳ | Tolerable | < ۱ ساعت | < ۴ ساعت | identity/secrets, registry |
| ۴ | Best effort | < ۲۴ ساعت | < ۸ ساعت | monitoring/logging, GitOps |

## RPO-RTO-RECOVERY-TIERS-3. RPO/RTO illustrative per component

| Component | RPO illustrative | RTO illustrative | توضیح |
|---|---|---|---|
| K8s control plane | ۰–۵ دقیقه | < ۳۰ دقیقه | etcd snapshot هر ۴–۶ ساعت |
| Stateful workloads | < ۱۵ دقیقه | < ۲ ساعت | Velero + CSI snapshot |
| Ceph storage | < ۱۵ دقیقه | < ۲ ساعت | replication + snapshot |
| Identity/secrets (Vault/Keycloak) | < ۱ ساعت | < ۴ ساعت | Vault Raft snapshot، Keycloak DB |
| Registry/repository | < ۱ ساعت | < ۴ ساعت | Harbor/Nexus backup |
| Monitoring/logging | < ۱ ساعت | < ۴ ساعت | TSDB/Loki backup |
| GitOps/config repos | < ۲۴ ساعت | < ۸ ساعت | Git commit |

همه مقادیر illustrative هستند — 약속 production-committed نیست.

## RPO-RTO-RECOVERY-TIERS-4. đoasuring RPO/RTO

 در تمرین بازیابی: زمان شروع وقفه، زمان بازیابی، مقدار از دست دادنش‌پذیر دیتا را ثبت کنید.
 RTO = زمان بازیابی − زمان شروع وقفه.
 RPO = آخرین بکاپ معتبر − زمان وقفه.

## RPO-RTO-RECOVERY-TIERS-5. Recovery order

 ۱. Control plane (etcd → API server)
 ۲. CNI و Storage (Ceph)
 ۳. Ingress
 ۴. Argo CD و Git
 ۵. Identity/Secrets (Vault/Keycloak)
 ۶. Registry (Harbor/Nexus)
 ۷. Monitoring/Logging
 ۸. برنامه‌ها

---

*SND 004-P11.5 — RPO-RTO-RECOVERY-TIERS (illustrative)*
