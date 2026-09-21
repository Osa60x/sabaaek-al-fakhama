# سبائك الفخامة — لوحة أسعار الذهب

موقع ثابت (GitHub Pages) يعرض سعر الأونصة والعيارات 24/21/18 بالريال السعودي، مع مخطط تفاعلي متعدد المديات، ثيمات، وإدارة أسعار معزولة.

## البنية الحالية (main)

- **واجهة**: HTML/CSS/JS ثابتة مع ثيمات `emerald_classic`, `obsidian_glass`, `ivory_luxe` ومنع وميض الثيم عند البدء
- **البيانات**: Cloudflare Worker `sabaaek-gold-api.osa60x.workers.dev` يحفظ:
  - `gold_points` (36 ساعة خام)
  - `gold_daily` (400 يوم ملخص)
  - `gold_monthly` (ملخص شهري)
  - `last_good_quote` مع كاش ذاكرة 25 ثانية + Edge Cache
- **المخطط**: 24 ساعة / شهر / سنة مع فجوات مرئية ونص عربي صحيح للعدد
- **الإدارة**: `admin.html` + Supabase Functions `sabaaek-admin` (تعديل أسعار العيارات فقط، مع عزل مشروع وكلمة مرور)
- **الأصول**: شعار شفاف، خلفية obsidian، QR يظهر فقط في الوضع الأفقي، تحسين LCP

## PWA (تمت إضافته من PR #1)

من PR #1 تم دمج:

- `manifest.webmanifest` + `sw.js` (عمل دون اتصال)
- أيقونات `icon-192.png`, `icon-512.png`, `icon-512-maskable.png`, `apple-touch-icon.png`, `favicon.svg`
- صورة مشاركة `og-image.png` (1200×630) + وسوم Open Graph
- تسجيل Service Worker في `index.html`

## مصادر البيانات

| # | المصدر | الاستخدام |
|---|--------|-----------|
| 1 | Worker `sabaaek-gold-api.osa60x.workers.dev` `/quote` + `/history?range=` | أساسي مع سجل تاريخي |
| 2 | `api.gold-api.com/price/XAU/USD` | احتياط مباشر (CORS) |
| 3 | `api.goldprice.dev` + `xaus.com` | احتياطات إضافية (موجودة في إصدار arena السابق) |

الـ Worker الحالي يتحقق من:
- `price` بين 1000 و 10000
- `sourceUpdatedAt` ليس أقدم من 30 دقيقة
- رفض القفزات >20% أو التواريخ الأقدم

## تحقق ما قبل النشر

قبل أي نشر يدوي، شغّل من جذر المشروع:

```bash
python3 tests/check_release_contracts.py
```

يتحقق العقد من:
- عزل مشروع سبائك
- مسار QR حسب الاتجاه
- الشعار الشفاف
- حركة التقليل
- مسار التخطّي للوحة المفاتيح
- حدود اللمس ورسائل الخطأ في لوحة الإدارة
- قراءة النسخة المنشورة للتحقق من بقائها متاحة

لا يرسل النموذج بيانات دخول ولا يغير الأسعار أو إعدادات الموقع.

## الاختبارات

```bash
# اختبارات الواجهة والسجل
python3 tests/test_chart_history_ranges.py
python3 tests/test_chart_history_count_arabic_grammar.py
python3 tests/test_theme_bootstrap.py
# ... وغيرها في tests/
```

## النشر

`push` إلى `main` ينشر تلقائياً عبر `.github/workflows/deploy-pages.yml`.

## الملفات المدمجة من PR #1

```
manifest.webmanifest
sw.js
assets/icon-*.png, apple-touch-icon.png, favicon.svg, og-image.png
assets/sabaaek-logo-360.png/webp, sabaaek-logo-720.webp
تقرير-التحليل-والتطوير.md
خطة-المرحلة-الثانية.md
تحليل-فخامة-الأسطورة.md
الرد-الموجه-إلى-Manus.md
```

## التالي (اختياري)

- تفعيل تعديل الأسعار عبر `config.js` بسيط للآيفون (مقترح في خطة المرحلة الثانية)
- زر وضع نهاري/ليلي صغير على الطرف
- تقليل حجم المشروع بإزالة الحاسبة والتيكر إذا لم تعد مطلوبة (كانت في إصدار arena)

الـ PR #1 تم دمجه في `main` بتاريخ 2026-09-21 عبر دمج يدوي مع حل تعارضات لصالح `main` المتقدم.
