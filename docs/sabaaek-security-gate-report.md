# تقرير بوابة التحقق الأمنية — سبائك الفخامة

الحالة: **POC staging فقط — غير معتمد للإنتاج**  
الفرع: `migration/sabaaek-cloudflare-staging`  
الإنتاج: **UNCHANGED**

## خلاصة القرار

تم اختبار السلوك الفعلي لمسارات Owner وManager وCSRF وOrigin ورفض الإعدادات غير الآمنة على Worker المنشور. نجحت الحدود الأساسية في الاختبار الحي، لكن البوابة لا تُغلق كـProduction Ready لأن اختبار rate limit الكامل علق أثناء سلسلة الطلبات، وقياس PBKDF2 عند 300k و600k رفضه runtime، بينما قياس 100k أعاد زمناً صفرياً غير صالح لاتخاذ قرار performance. لذلك **لا تبدأ واجهة الإدارة ولا تنقل حساب المالك الحقيقي بعد**.

## مصفوفة الحكم

| المجال | الحكم | الدليل الفعلي |
|---|---|---|
| AUTH | PASS جزئي / BLOCKED للإنتاج | bootstrap وlogin وsession نجحت بحسابات عشوائية؛ لا يوجد حساب اختباري باقٍ. recovery/password-change غير مختبرين |
| PASSWORD HASHING | BLOCKED | PBKDF2-HMAC-SHA256 يعمل عند 100k، لكن 300k و600k أعادا `503 benchmark_unavailable`، و100k أعاد 0ms بسبب دقة القياس؛ لا يكفي لاعتماد work factor إنتاجي |
| SESSION | PASS جزئي | إنشاء الجلسة وقراءتها نجحا، مع cookie HttpOnly/Secure/SameSite؛ expiry وrevocation وrefresh لم تُختبر حياً |
| CSRF | PASS | الطلب المغيّر بلا `X-CSRF-Token` رُفض بـ403 |
| RATE LIMIT | BLOCKED | لم تكتمل السلسلة الحية بصورة موثوقة؛ لا يُمنح PASS بسبب timeout في harness |
| RBAC | PASS للمسارات المختبرة | Manager نجح في تعديل السعر، ورُفض في settings/managers/audit بـ403، وanonymous رُفض بـ401 |
| AUDIT | FAIL جزئي | التسجيل موجود، لكن سجل تعديل السعر الحالي لا يحفظ old value وnew value وresult كاملاً كما يطلب العقد |
| D1 | PASS | schema منفصل، foreign keys، indexes، checks، unique email، cleanup للجلسات |
| BACKUP | PASS | export production تحقق محلياً من الجداول والصفوف |
| RESTORE | PASS | الاستعادة إلى D1 staging مستقل والتحقق من التطبيق نجحا |
| OWNER | PASS جزئي | bootstrap وإنشاء Manager اختُبرا حياً؛ settings الشرعية وdisable manager لم يُختبرا حياً بعد |
| MANAGER | PASS جزئي | login وتعديل السعر والرفض للمسارات الممنوعة اختُبرت حياً؛ disabled/expired/revoked لم تُختبر |
| PRICE SYSTEM | BLOCKED | عزل carat تحقق، لكن concurrency وold/new audit وcross-field integrity لم تُثبت حياً |
| CHART | PASS بصرياً على Chromium | اختبارات viewport السابقة نجحت؛ edge tooltip/drag/touch لم تُثبت كاملة |
| MOBILE | PASS لمحاكاة Chromium فقط | لا horizontal overflow في المقاسات المفحوصة؛ **NOT VERIFIED ON REAL DEVICE** |
| ACCESSIBILITY | BLOCKED | لم يُنفذ axe أو اختبار قارئ شاشة/keyboard/200% zoom بشكل مستقل |
| PERFORMANCE | BLOCKED | لا يوجد LCP/INP/CLS وbenchmark hashing صالح؛ لا يُدعى الأداء قبل القياس |
| PRODUCTION | UNCHANGED | لا DNS، لا main، لا production D1، لا production secrets |

## ما تم إصلاحه أثناء البوابة

كشف الاختبار الحي أن `contact_actions` كانت تُقبل دون validation كافٍ؛ تم إضافة validation تمنع HTML و`javascript:` والقيم غير الصالحة، وأعيدت بيانات staging إلى baseline. كما كشف الاختبار أن endpoint benchmark المؤقت كان يرجع SPA بـ200 بعد حذفه؛ أُغلق المسار صراحة بـ404 وحُذف سر benchmark.

## القيود الحالية

لا يمكن اعتبار 100,000 iteration قراراً نهائياً؛ توصية OWASP العامة لـPBKDF2-HMAC-SHA256 أعلى، لكن حد Workers وDoS وزمن login يحتاج قياساً صالحاً. لا تستخدم هذه النتيجة لإضافة بريد المالك الحقيقي أو كلمة مرور حقيقية أو فتح واجهة الإدارة.

## بوابة السماح التالية

قبل UI يجب إعادة اختبار rate limit بأداة مستقرة، اختبار expiry/revocation/disabled manager، إصلاح audit ليحفظ القيم السابقة والجديدة والنتيجة، اختبار التزامن، ثم إجراء benchmark مستقل قابل للقياس أو اعتماد adapter مصادقة موثوق. بعد ذلك فقط يُعاد تقييم فتح واجهة الإدارة في staging.

## References

[1]: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html "OWASP Password Storage Cheat Sheet"
[2]: https://developers.cloudflare.com/workers/runtime-apis/web-crypto/ "Cloudflare Workers Web Crypto"
[3]: https://better-auth.com/blog/1-5 "Better Auth 1.5"
[4]: https://developers.cloudflare.com/d1/reference/d1-api/ "Cloudflare D1 API"
