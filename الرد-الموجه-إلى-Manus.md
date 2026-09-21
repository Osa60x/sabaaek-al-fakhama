# 📋 الرد الموجه إلى Manus — ماذا يفعل، وكيف، وبماذا (خطة إصلاح وتطوير «فخامة الأسطورة»)

> أُعدّ هذا المستند بعد: تشريح مباشر للموقع المنشور، ملخص الحزمة الجنائية (22 وثيقة / 189 ملفاً)،
> بحث موسع موثق (2026)، وتحقق حي من كل مصدر وكل حد مجاني مذكور.
> **انسخ هذا المستند كاملاً إلى محادثة Manus** واطلب تنفيذ البنود المرقمة بالترتيب، ثم أعد لنا ملفاتك المحدثة.

---

## المرحلة 0 — التشخيص الإجباري (قبل أي تعديل)

اطلب من Manus تنفيذ هذه الفحوصات أولاً وإرجاع نتائجها بالأرقام:

1. **تشخيص سبب التوقف** — اقرأ سجلات المنصة/الاستضافة (Manus logs / server logs) وحدد: هل الانقطاع من
   - (أ) نوم الخادم بعد خمول (Render-like)؟
   - (ب) حد طلبات/موارد منصة Manus؟
   - (ج) فشل مصدر الأسعار الخارجي؟
   - (د) خطأ في الكود (unhandled exception يوقف الخدمة)؟
   أعد جدولاً: كل انقطاع مسجل ← سببه ← الوقت.
2. **خريطة المعمارية** — أعد `ARCHITECTURE.md` من المشروع الحالي: ما الخادم؟ قاعدة البيانات (SQLite/Postgres/JSON)؟ أين تُخزن الأسعار المعدّلة؟ ما مسار الـAPI الحقيقي؟
3. **فحص أمان المصادقة** — أجب بنعم/لا مدعومة بسطر الشيفرة: هل كلمة المرور مُجزّأة (hash)؟ هل توجد حماية من التخمين (rate limit)؟ هل أي سر موجود في ملفات يصل إليها المتصفح (`.env` يُحمَّل للعميل، مفتاح API في JS)؟ هل جلسات الإدارة تنتهي؟
4. **تدقيق الاختبارات** — شغّل الـ35 اختباراً المذكورة وأعد لائحة: 35/35 ناجحة أم أي فشل؟ (نطالب بالأرقام لا بالكلام)

**قاعدة صارمة:** أي إصلاح يبدأ بخطوة تحقق قابلة للإثبات (سجل، اختبار، قياس رقمي). لا تقبل "تم الإصلاح" بدون دليل.

---

## المرحلة 1 — علاج «الموقع يتوقف» (الأولوية القصوى)

### القرار الموصى به: نقل الاستضافة إلى Cloudflare (مجاني 100% وبلا نوم)

| المكوّن | المنصة المجانية | الحد الموثق | الرابط الرسمي |
|---------|----------------|-------------|---------------|
| الواجهة (الموقع) | Cloudflare Pages | نطاق ترددي غير محدود + 500 بناء/شهر | https://developers.cloudflare.com/pages/ |
| الـAPI (الأسعار + الإدارة) | Cloudflare Workers | **100,000 طلب/يوم** | https://developers.cloudflare.com/workers/platform/limits/ |
| تخزين الأسعار المعدّلة | Workers KV | 100,000 قراءة + 1,000 كتابة/يوم | https://developers.cloudflare.com/kv/platform/limits/ |
| مهام دورية (تحديث الأسعار) | Cron Triggers | 5 مهام مجانية | https://developers.cloudflare.com/workers/configuration/cron-triggers/ |

**لماذا:** مراجعات 2026 المتعددة توثق عدم استقرار خوادم Manus ("server busy"، تجمّد — nxcode.io، cybernews، taskade).
Cloudflare لا "ينام" ولا ينام معه موقعك، وحدوده تكفي: 100,000 طلب/يوم = أكثر من 3 أضعاف احتياجك حتى مع تحديث كل 5 ثوانٍ.

**الخطوات المطلوبة من Manus:**
1. انقل المشروع إلى مستودع GitHub **خاص** (أو استمر من أي مستودع موجود).
2. اربط المستودع بـCloudflare Pages (تبويب Workers & Pages ← Create ← Connect to Git) — النشر تلقائي عند كل `push`.
3. انقل منطق الخادم (جلب الأسعار، حفظ التعديلات، المصادقة) إلى Worker واحد، والتخزين إلى KV.
4. أضف ملف `wrangler.toml` بهذا الشكل:

```toml
name = "fakhama-api"
main = "src/worker.js"
compatibility_date = "2026-08-01"

[[kv_namespaces]]
binding = "PRICES"
id = "ضع_المعرف_هنا_من_لوحة_Cloudflare"
```

### كود Worker جاهز (جلب الأسعار بسلسلة احتياط من 4 مصادر متحققة)

```js
// src/worker.js — نواة الـAPI الجديد (مجاني: Workers + KV)
const SOURCES = [
  { url: "https://api.gold-api.com/price/XAU/USD", parse: r => ({ price: r.price, ts: Date.parse(r.updatedAt) }) },
  { url: "https://api.goldprice.dev/v1/prices?symbol=XAU-USD-SPOT", parse: r => { const s = r.symbols[0]; return { price: Number(s.price), ts: Date.parse(s.computed_at) }; } },
  { url: "https://xaus.com/api/v1/spot", parse: r => ({ price: r.xau.price, ts: Date.parse(r.updated_at) }) },
  { url: "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", parse: r => ({ price: (r[0].spreadProfilePrices[0].bid + r[0].spreadProfilePrices[0].ask) / 2, ts: r[0].ts }) }
];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    // 1) الواجهة: آخر سعر + التعديلات المعتمدة
    if (url.pathname === "/api/prices") {
      const cache = caches.default;
      const cached = await cache.match(request);
      if (cached) return cached;
      let quote = null, errors = [];
      for (const s of SOURCES) {
        try {
          const res = await fetch(s.url, { cf: { cacheTtl: 30 } });
          quote = s.parse(await res.json()); break;
        } catch (e) { errors.push(s.url + ": " + e.message); }
      }
      const adjustments = await env.PRICES.get("adjustments", "json") || { 24: 0, 21: 0, 18: 0 };
      const body = JSON.stringify({ ok: !!quote, quote, adjustments, source_errors: errors, fetched_at: Date.now() });
      const resp = new Response(body, { headers: { "content-type": "application/json", "cache-control": "public, max-age=30" } });
      await cache.put(request, resp.clone());
      return resp;
    }
    // 2) لوحة الإدارة: حفظ التعديلات (محمي بمفتاح سري على الخادم فقط)
    if (url.pathname === "/api/admin/adjust" && request.method === "POST") {
      if (request.headers.get("x-admin-key") !== env.ADMIN_KEY) return new Response("unauthorized", { status: 401 });
      const body = await request.json();
      const clean = {};
      for (const [k, v] of Object.entries(body.adjustments || {})) if (/^\d{1,2}$/.test(k) && Number.isFinite(v)) clean[k] = Math.round(v * 10) / 10;
      await env.PRICES.put("adjustments", JSON.stringify(clean));
      return new Response(JSON.stringify({ ok: true, adjustments: clean }));
    }
    return new Response("not found", { status: 404 });
  }
};
```

**ملاحظات أمان صارمة:** `ADMIN_KEY` يُعرَّف كمتغير بيئة في Cloudflare فقط (Settings ← Variables) —
**ممنوع** وضعه في أي ملف يصل إليه المتصفح، وممنوع إرساله في الرابط.

---

## المرحلة 2 — نظام الأسعار: تعديل 24/21/18 (و22/14/9) من الآيفون

### الخيار أ (الموصى به لصاحب واحد لا يفهم البرمجة): ملف إعدادات + GitHub

اطلب من Manus:
1. إنشاء ملف `config.js` في جذر المشروع بهذا الشكل (تعليقات عربية):

```js
// ===== إعدادات الأسعار — عدّل الأرقام فقط ثم Commit =====
// سالب (-) = خصم · موجب (+) = إضافة
window.SABAAEK_CONFIG = {
  karats: [
    { k: 24, purity: 0.9999, adjust: -5,   note: "يشمل ضبطاً معتمداً" },
    { k: 22, purity: 0.9166, adjust: 0,    note: "" },
    { k: 21, purity: 0.875,  adjust: -10,  note: "يشمل ضبطاً معتمداً" },
    { k: 18, purity: 0.750,  adjust: -20,  note: "" },
    { k: 14, purity: 0.5833, adjust: 0,    note: "" },
    { k: 9,  purity: 0.375,  adjust: 0,    note: "" }
  ],
  usd_sar: 3.75,          // سعر الصرف (الريال مرتبط بالدولار)
  refresh_seconds: 30     // فترة تحديث الأسعار
};
```

2. تعديل الواجهة لقراءة هذا الملف أولاً (`<script src="config.js"></script>` قبل سكربت الموقع) وحساب:
   `سعر_العرض = (أونصة × 3.75 ÷ 31.1035 × النقاء) + adjust`
3. **نشر الدليل للصاحب (نرفقه لك):** من الآيفون → تطبيق GitHub → المستودع → `config.js` → زر القلم ✏️ →
   غيّر الأرقام → Commit → خلال ~دقيقة يظهر السعر الجديد للزوار.
   (رسمي وموثق: https://docs.github.com/en/repositories/working-with-files/managing-files/editing-files
   وتطبيق iOS يدعم التعديل منذ 2022: https://github.blog/changelog/2022-11-15-github-for-ios-edit-files-from-browse-code)

### الخيار ب (إذا أصررت على لوحة إدارة داخلية): Worker محمي
- مسار غير شائع (مثال `/panel-x7` بدل `/admin`) + مفتاح سري من الخادم (الكود أعلاه) + **rate limit**:
  في Cloudflare: Security ← WAF ← Rate limiting rules (مجاني) — 5 محاولات/دقيقة لكل IP على مسار الدخول.
- سجل تدقيق: كل تعديل يُكتب في KV بمفتاح `log:YYYY-MM-DD` (الوقت + من عدّل).
- لا 2FA لصاحب واحد؟ يُنصح به لكنه اختياري (Google Authenticator مجاني).

**توصية صريحة:** للوصول الحالي (مدراء يعدّلون أسعاراً فقط) — الخيار أ أبسط وأأمن وأرخص:
لا قاعدة بيانات، لا جلسات، لا كلمات مرور تُخمَّن. الزوار لا يحتاجون أي حساب إطلاقاً.

---

## المرحلة 3 — مصادر البيانات: لا مصدر واحد

اطلب من Manus:
1. استخدام **سلسلة الاحتياط الأربعة** في الكود أعلاه (كلها مجانية — تحققنا منها حياً بفرق 0.007%).
2. عرض المصدر الحالي بجانب الوقت (شفافية)، وإظهار "آخر لقطة ناجحة" عند فشل كل المصادر.
3. مهلة طلب 5 ثوانٍ لكل مصدر (لا 8+).
4. **تحقق رقمي مطلوب من Manus:** جدول بأسعار المصادر الأربعة في نفس اللحظة وإثبات أن الأرقام المعروضة
   في موقعك = (الأونصة × 3.75 ÷ 31.1035 × النقاء) + الضبط — مطابقة لآخر منزلتين عشريتين.

---

## المرحلة 4 — تصميم الشاشة العرضية (Landscape) وترتيب أفضل

المشكلة: العرض على الشاشات العريضة غير مرتب مقارنة بموقع سبائك الفخامة (ملاحظة صاحب المشروع).
اطلب من Manus:
1. `@media (min-width: 1024px)` و `(orientation: landscape)`:
   - شبكة من عمودين: بطاقة الأونصة + المخطط جنباً إلى جنب (مثل سبائك الفخامة: `grid-template-columns: minmax(400px,.9fr) minmax(520px,1.1fr)`).
   - العيارات في صف واحد بارتفاع موحد، والـ"عرض المزيد" (22/14/9) يتمدد داخل الشبكة دون كسر الصف.
2. اختبار حقيقي: افتح الموقع على iPhone في الوضع الأفقي وعلى iPad وعلى شاشة 1366px — والتقط لقطات قبل/بعد.
3. حافظ على الوضع العمودي (الجوال) كما هو — لا تكسر ما يعمل.

---

## المرحلة 5 — الأداء والسرعة (أرقام قابلة للقياس)

1. شغّل **PageSpeed Insights** (مجاني): https://pagespeed.web.dev — اطلب من Manus رفع النتيجة من X إلى ≥90 على الجوال.
2. نقاط إلزامية:
   - ضغط الصور WebP/AVIF (مثال: الشعار 186KB ← 64KB جودة 82% — طبقناه على سبائك الفخامة بنجاح).
   - `preconnect` لواجهات الأسعار والخطوط.
   - خط واحد عربي بوزنين مع `display=swap` (IBM Plex Sans Arabic مجاني: https://fonts.google.com/specimen/IBM+Plex+Sans+Arabic).
   - `cache-control` مناسب للملفات الثابتة (كما في كود الـWorker أعلاه).
   - لا تحمّل مكتبات مخططات ثقيلة — ارسم بالـSVG يدوياً (مخطط سبائك الفخامة الحالي 100% SVG بدون مكتبات).
3. اختبر على شبكة 3G عبر DevTools وأعد زمن أول رسم (LCP).

---

## المرحلة 6 — مراقبة التوفر (تعرف قبل زبائنك)

اطلب من Manus تثبيت **واحد** من هذه (مجانية):
1. **Better Stack** (10 مراقبين، كل 3 دقائق، تنبيهات بريد): https://betterstack.com — الأنسب لأن
   UptimeRobot المجاني **ممنوع للاستخدام التجاري منذ ديسمبر 2024** (شروطهم — لا نوصي بمخالفتها).
2. **HetrixTools** (15 مراقباً، كل دقيقة): https://hetrixtools.com — الأسرع مجاناً.
3. مراقب على `/api/health` يعيد `{"ok":true}` — أضف هذا المسار في الـWorker (3 أسطر).

---

## المرحلة 7 — الأمان (فحص نهائي إلزامي)

اطلب من Manus تنفيذ قائمة OWASP الأساسية وتوقيعها بأسطر الشيفرة:
- [ ] لا أسرار في كود العميل (ابحث عن: `.env`، `apiKey`، `secret`، `token=` داخل `public/` أو `*.js` يُحمَّل للمتصفح)
- [ ] Rate limiting على الدخول (Cloudflare WAF مجاني)
- [ ] كلمات المرور مخزنة مُجزّأة (bcrypt/argon2) — لا plaintext
- [ ] جلسات الإدارة تنتهي (30-60 دقيقة) وتُدار على الخادم
- [ ] رفض الإدخال الخبيث (تطبيع الأرقام فقط: `Number.isFinite` + نطاق مسموح)
- [ ] رؤوس أمان: `Content-Security-Policy`، `X-Frame-Options: DENY`، `Referrer-Policy`
- [ ] لا تظهر مسارات الإدارة في `robots.txt` ولا في كود العميل

---

## المرحلة 8 — الملفات التي يجب أن يسلّمها Manus بعد التنفيذ

| الملف | الغرض |
|-------|-------|
| `config.js` | أرقام العيارات والتعديلات (يعدّلها صاحب المشروع من الآيفون) |
| `src/worker.js` | الـAPI الكامل (أسعار + إدارة + health) — الكود أعلاه أساساً |
| `wrangler.toml` | إعدادات Cloudflare (KV + Cron) |
| `ARCHITECTURE.md` | خريطة المعمارية النهائية |
| `TEST_REPORT.md` | نتائج الاختبارات بالأرقام (كم ناجح/كم فشل) |
| `FIX_LOG.md` | كل مشكلة ← سببها ← إصلاحها ← دليل الإثبات |
| دليل الآيفون | خطوات تعديل الأسعار بالصور (3-5 خطوات) |

---

## ملخص الروابط المجانية المعتمدة (كلها متحققة)

**استضافة:** Cloudflare Pages (developers.cloudflare.com/pages/) · الحدود الرسمية (developers.cloudflare.com/workers/platform/limits/ و /kv/platform/limits/)
**أسعار:** gold-api.com · goldprice.dev/docs · xaus.com/api · Swissquote (خادم فقط)
**مراقبة:** betterstack.com · hetrixtools.com
**تعديل من الآيفون:** docs.github.com (Editing files) · github.blog/changelog/2022-11-15
**أداء:** pagespeed.web.dev · webaim.org/resources/contrastchecker/
**أمان:** OWASP Authentication Cheat Sheet (cheatsheetseries.owasp.org)
**خط:** IBM Plex Sans Arabic (fonts.google.com)
