# تست‌هاییکپارچگی مخزن و زنجیره ارزشی

*مثالی است.*

## تست‌هاییکپارچگی مخزن-1. جریان artifact

External Upstream → Internal Manager (Nexus/Harbor) → Reverse Proxy پایا → K8s/CI.

ب retrieval بسته OS، تصویر کانتینر، چارت Helm و OCI، auth، TLS/CA trust، proxy و hosted repo، transfer تصویر بزرگ، digest verification، اسکن، امضا، تایید امضا، اجبار در admission، artifact آفلاین.

Nexus و Harbor جداگانه.

موارد شکست: upstream unavailable، proxy unavailable، hosted repo unavailable، cert نامعتبر، auth failure، digest غائب، امضا نامعتبر، artifact آفلاین غائب.

اسکن، امضا، تایید و اجبار هم‌معنی نیستند.

---

*SND 004-P11.7 — تست‌هاییکپارچگی مخزن (illustrative)*
