# CEPH-DISASTER-RECOVERY

*مثالی است.*

## CEPH-DISASTER-RECOVERY-1.覆盖

 MON quorum recovery، OSD failure/replacement، PG degraded/inconsistent، pool+CRUSH backup، config+keyring protection، RBD backup/recovery، CephFS/RGW data+metadata، Rook-Ceph operator+K8s recovery، CSI/PVC recovery، cross-cluster/off-site.

## CEPH-DISASTER-RECOVERY-2. mechanisms

 replication، erasure coding، snapshot، clone، backup، async replication، DR — هر کدام risk profile مختلف.

## CEPH-DISASTER-RECOVERY-3. commands illustrative

 `ceph status`، `ceph health detail`، `ceph osd tree`، `ceph pg stat`، `ceph df`، `ceph osd perf`.

## CEPH-DISASTER-RECOVERY-4. warnings

 destructive Ceph commands را به عنوان routine recovery توصیح نکنید. specialist review برای عملیات خطرناک داده.

---

*SND 004-P11.5 — CEPH-DISASTER-RECOVERY (illustrative)*
