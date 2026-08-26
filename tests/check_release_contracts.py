from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_URL = "https://osa60x.github.io/sabaaek-al-fakhama/?locale=ar&theme-preview=obsidian_glass"


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    admin = (ROOT / "admin.html").read_text(encoding="utf-8")

    # Public-page isolation and resilient visual contracts.
    require("onlptehmvnzzbxswkcrh.supabase.co/functions/v1/sabaaek-admin" in index,
            "العزل: الصفحة العامة لا تستخدم وظيفة سبائك المستقلة", failures)
    require("gold.osa60x.workers.dev" not in index and "rsrtwubjdfdnflkttwwy" not in index,
            "العزل: وُجد مرجع لمشروع فخامة الأسطورة في الصفحة العامة", failures)
    require("@media(orientation:portrait){.site-qr{display:none}}" in index,
            "QR: لا توجد قاعدة إخفاء للوضع الطولي", failures)
    require("sabaaek-logo-user.png" in index,
            "الهوية: الرأس لا يستخدم أصل الشعار الشفاف الذي زوّده المستخدم", failures)
    require('class="brand-logo-user"' in index and 'fetchpriority="high"' in index,
            "الأداء: الشعار الرئيسي لا يطلب بأولوية عالية رغم كونه عنصر LCP مثبت", failures)
    require('<div class="brand"><img class="brand-logo-user"' in index and "brand-window" not in index and "brand-logo-source" not in index,
            "الهوية: ما زالت نافذة اقتصاص أو بطاقة داخلية تحيط بالشعار", failures)
    require('.topbar::after,body[data-theme="obsidian_glass"] .topbar::after{content:none!important' in index,
            "الهوية: ما زال تأثير بطاقة الرأس يرسم إطارًا حول الشعار", failures)
    require('filter:brightness(.98) saturate(.90) contrast(1.04) drop-shadow' in index,
            "الهوية: لا يوجد ضبط محافظ لحدة لون الشعار وتباينه", failures)
    require("data-theme-pending" in index and "sabaaek-public-theme" in index,
            "الثيم: لا توجد حماية بدء مبكر تمنع وميض الثيم الافتراضي", failures)
    require("localStorage.setItem('sabaaek-public-theme',settings.theme)" in admin,
            "الثيم: حفظ إعدادات الإدارة لا يحدّث ذاكرة الثيم للزيارة التالية", failures)
    require("prefers-reduced-motion" in index,
            "الحركة: لا توجد حماية تقليل الحركة", failures)
    require('class="skip-link" href="#prices"' in index and 'id="prices" tabindex="-1"' in index,
            "الواجهة العامة: لا يوجد مسار تخطٍّ مباشر إلى الأسعار للوحة المفاتيح", failures)
    require("touch-action:manipulation" in index,
            "الواجهة العامة: لا توجد حماية لمس لمنع تأخر النقر المزدوج", failures)

    # Admin accessibility contracts: these intentionally fail before the B improvement.
    require('id="login-error-summary" class="error-summary" role="alert" tabindex="-1" hidden' in admin,
            "الإدارة: لا يوجد ملخص أخطاء متاح لقارئات الشاشة", failures)
    require('id="email"' in admin and 'aria-describedby="email-error"' in admin,
            "الإدارة: حقل البريد لا يرتبط برسالة خطأ محلية", failures)
    require('id="password"' in admin and 'aria-describedby="password-error"' in admin,
            "الإدارة: حقل كلمة المرور لا يرتبط برسالة خطأ محلية", failures)
    require('id="email" name="email" type="email" inputmode="email" autocomplete="email" autocapitalize="none" spellcheck="false"' in admin,
            "الإدارة: حقل البريد يفتقد بيانات الإدخال المناسبة للهاتف ومدير كلمات المرور", failures)
    require('id="password" name="password" type="password" autocomplete="current-password" autocapitalize="none" spellcheck="false"' in admin,
            "الإدارة: حقل كلمة المرور يفتقد بيانات الإدخال المناسبة للهاتف ومدير كلمات المرور", failures)
    require("font:16px/1.5 Kufi,system-ui,sans-serif" in admin,
            "الإدارة: حجم نص حقول الإدخال أقل من خط القراءة المريح على الهاتف", failures)
    require("function refreshLoginField" in admin and "addEventListener('input',()=>refreshLoginField('email'))" in admin and "addEventListener('input',()=>refreshLoginField('password'))" in admin,
            "الإدارة: لا تُحدَّث رسائل أخطاء الدخول عند تصحيح الحقول", failures)
    require("input,select{width:100%;min-height:44px" in admin,
            "الإدارة: حقول الإدخال لا تلتزم بحد لمس 44px", failures)
    require("button{border:0;border-radius:11px;min-height:44px" in admin,
            "الإدارة: أزرار الإدارة لا تلتزم بحد لمس 44px", failures)
    require(":focus-visible" in admin,
            "الإدارة: لا توجد حلقة تركيز مخصصة للوحة المفاتيح", failures)
    require('.stepper button{min-width:44px;min-height:44px' in admin,
            "الإدارة: أزرار ضبط الأسعار أصغر من مساحة لمس 44px", failures)
    require('.danger{min-height:44px' in admin,
            "الإدارة: زر إيقاف المدير أصغر من مساحة لمس 44px", failures)

    try:
        request = urllib.request.Request(LIVE_URL, headers={"User-Agent": "Sabaaek-contract-check/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            live = response.read().decode("utf-8", errors="replace")
            require(response.status == 200, "النشر: الصفحة العامة لم تعد HTTP 200", failures)
            require("sabaaek-logo-user.png" in live or "sabaaek-logo-transparent.webp" in live,
                    "النشر: النسخة الحية لا تحتوي مرجع أصل شعار شفاف", failures)
    except Exception as error:
        failures.append(f"النشر: تعذر قراءة الصفحة الحية ({type(error).__name__})")

    if failures:
        print("FAILED CONTRACTS:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("ALL_RELEASE_CONTRACTS_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
