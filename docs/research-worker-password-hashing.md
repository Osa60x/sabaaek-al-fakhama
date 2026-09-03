# مراجعة hashing كلمات المرور في Workers

المصدر الرسمي: https://developers.cloudflare.com/workers/runtime-apis/web-crypto/

تم التحقق في 2026-09-03 من جدول الخوارزميات في وثائق Cloudflare Web Crypto. يدعم Workers خوارزمية PBKDF2 في عمليات `deriveBits()` و`deriveKey()`، كما يوضح المصدر أن `importKey()` يتطلب `ArrayBuffer` وalgorithm object، وأن `deriveBits()` يعيد `ArrayBuffer`.

نتيجة الاختبار الحي في staging: فشل POC الحالي داخل hashing قبل الكتابة إلى D1، لذلك لم يُنشأ أي حساب اختبار ولم تُحفظ أي كلمة مرور. بما أن PBKDF2 مدعوم رسمياً، يجب عزل الخطأ بصيغة مدخلات Web Crypto أو إصدار runtime، ثم إعادة اختبار hashing محلياً وعلى Worker. لا يُسمح بتجاوز الفشل باستخدام SHA-256 منفرداً لتخزين كلمات المرور.

المسار الآمن التالي هو استخدام adapter مصادقة مُختبر مثل Better Auth مع D1، أو نقل hashing إلى مكتبة/مسار موثوق يدعم password hashing فعلياً، مع إبقاء bootstrap مغلقاً وعدم إضافة سر إنتاجي.
