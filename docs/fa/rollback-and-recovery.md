# ROLLBACK-AND-RECOVERY

*مثالی است.*

## ROLLBACK-AND-RECOVERY-1. خيارات rollback

هر komponent اصلی: in-place rollback مدعوم، بازیازی از بکاپ، reinstallation و بازیازی داده، forward-fix فقط، downgrade مدعوم نیست/دنeler.

تفاوت‌ها:rollback پیکربندی، نسخه binary/bin، schema دیتابیس، CRD، داده پایدار، کنترل‌پلین K8s.

درخت تصمیم بازیازی.

هشدار: بازیازی داده قدیمی در نسخه جدید/قدیم نرم‌افزار خطرناک است.

---

*SND 004-P11.6 — rollback-and-recovery (illustrative)*
