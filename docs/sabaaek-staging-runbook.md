# سبائك الفخامة — دليل staging والاستعادة

## الحالة الحالية

تم إنشاء فرع `migration/sabaaek-cloudflare-staging` ونشر Worker مستقل باسم `sabaaek-site-staging`.

الرابط الحالي للتجربة:

`https://sabaaek-site-staging.osa60x.workers.dev/?locale=ar`

إصدار staging الأخير: `60533371-4d7f-4d37-9dd6-7118bbbffc29`.

## حدود staging

يخدم Worker الأصول العامة من `workers/sabaaek-site-staging/public`، ويمرر فقط `GET /api/quote` و`GET /api/history` إلى عامل سبائك العام. يمنع `/admin.html`، ويرفض طرق POST وPUT وDELETE قبل تمريرها. لا يحتوي إعداد staging على D1 binding أو Supabase secret أو أي مورد من مشروع فخامة الأسطورة.

أضيفت compatibility flag الرسمية `global_fetch_strictly_public` بعد ظهور خطأ Cloudflare 1042 في الاستدعاء بين Workerين داخل المنطقة نفسها. لم تُضف هذه الراية إلى عامل الإنتاج.

## نتائج تحقق staging

- اختبار العقد وعزل الموارد: ناجح.
- فحص JavaScript: ناجح.
- الصفحة العربية والأصول: 200.
- `GET /api/quote`: ناجح بعد إصلاح 1042.
- `GET /api/history?range=24h`: ناجح بعد إصلاح 1042.
- `/admin.html`: 404.
- `POST /api/quote`: 405، ولا يصل إلى العامل الأعلى.
- التحقق البصري: الشعار، السعر، بطاقات العيارات، المخطط، أزرار النطاقات وQR ظهرت في staging.

## النسخ والاستعادة

الالتزام Git يحفظ الكود والتكوين، لكنه لا يحفظ بيانات D1 الحية أو أسرار Supabase. يجب أخذ تصدير D1 كامل قبل أي تغيير بنيوي، ثم تحميله إلى قاعدة staging منفصلة واختبار استعادة جدول واحد على الأقل ومقارنة عدد الصفوف والمخطط.

حاولت تصدير قاعدة سبائك المحددة قراءةً فقط باستخدام:

`npx wrangler d1 export sabaaek_gold --remote --output /tmp/sabaaek-production-d1.sql --config workers/sabaaek-gold-api/wrangler.toml -y`

لكن Cloudflare أعاد `Authentication error [code: 10000]`، مع أن `wrangler whoami` يثبت الحساب الصحيح. لذلك لم أعتبر النسخ الاحتياطي مكتملاً، ولم أبدأ نقل الإدارة أو قاعدة البيانات.

## سبب التعذر والإجراء المطلوب

رمز التعذر يخص صلاحيات API Token المستخدمة في Wrangler، وليس دليلاً على تلف قاعدة البيانات أو فشل Worker الإنتاجي. يلزم إنشاء أو تعديل Token بصلاحية D1 المناسبة للحساب الصحيح، مع تقييد المورد إلى قاعدة سبائك قدر الإمكان، ثم إعادة التصدير والتحقق من الملف قبل أي استعادة. لا تُرسل قيمة Token أو كلمة المرور في المحادثة.

## rollback

طالما أن main وGitHub Pages وعامل الأسعار الإنتاجي لم تتغير، فإن rollback الحالي هو عدم تبديل DNS أو الإنتاج وإيقاف Worker staging أو حذف فرعه فقط بعد موافقة المستخدم. أي تبديل لاحق يحتاج الاحتفاظ بنسخة الإنتاج الحالية، وتوثيق DNS السابق، ورابط الإصدار السابق، وخطة إعادة التوجيه.

## شرط الانتقال التالي

لا تبدأ مهاجرة الإدارة أو تغيير DNS أو حذف Supabase إلا بعد نجاح تصدير D1، اختبار restore منفصل، اختبار parity للواجهة والمخطط، واختبارات Owner/Manager server-side كاملة.
