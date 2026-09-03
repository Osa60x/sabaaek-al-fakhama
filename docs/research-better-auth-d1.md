# نتائج مراجعة Better Auth وCloudflare D1

تاريخ المراجعة: 2026-09-02 بتوقيت المستخدم.

## Better Auth 1.5

المصدر الرسمي: https://better-auth.com/blog/1-5

يذكر إعلان Better Auth 1.5 أن Cloudflare D1 أصبح خيار قاعدة بيانات مدعوماً أصلاً، مع تمرير binding العامل مباشرة إلى `betterAuth({ database: env.DB })` دون adapter مخصص. كما يذكر أن dialect الخاص بـD1 يدعم تنفيذ الاستعلامات وعمليات batch والاستبطان من خلال API الأصلي لـD1.

القيد المهم الموثق في المصدر هو أن D1 لا يدعم interactive transactions؛ ويستخدم Better Auth `batch()` بدلاً منها لتحقيق الذرية. لذلك يجب اختبار تسجيل المستخدم وتغيير كلمة المرور وإنشاء الجلسة ضمن عمليات batch، وعدم تصميم POC على افتراض معاملات تفاعلية.

## Cloudflare D1

المصدر الرسمي الذي تمت مراجعته: https://developers.cloudflare.com/d1/reference/d1-api/

المسار السابق أعاد 404 لكنه أظهر فهرس Cloudflare الرسمي، بما في ذلك صفحات Workers Binding API وD1 Database وPrepared statements وTime Travel and backups. تم التحقق عملياً في المشروع من أوامر Wrangler الحالية ومن نجاح D1 export وremote execute وTime Travel info.

## قرار مرحلي

Better Auth + D1 صالحان لتجربة منفصلة في staging، لكن لا يجوز نقل مستخدمي Supabase أو صلاحيات Owner/Manager مباشرة. يبدأ POC بمخطط منفصل، جلسات HttpOnly/Secure/SameSite، صلاحيات server-side، audit log، rate limiting، واختبارات رفض Manager لعمليات Owner. لا تُستخدم localStorage أو KV لتخزين كلمات المرور أو الدور.
