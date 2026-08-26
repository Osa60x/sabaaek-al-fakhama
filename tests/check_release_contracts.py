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
    require("sabaaek-logo-transparent.webp" in index,
            "الهوية: بطاقة الرأس لا تستخدم الشعار الشفاف", failures)
    require("prefers-reduced-motion" in index,
            "الحركة: لا توجد حماية تقليل الحركة", failures)
    require('class="skip-link" href="#prices"' in index and 'id="prices" tabindex="-1"' in index,
            "الواجهة العامة: لا يوجد مسار تخطٍّ مباشر إلى الأسعار للوحة المفاتيح", failures)
    require("touch-action:manipulation" in index,
            "الواجهة العامة: لا توجد حماية لمس لمنع تأخر النقر المزدوج", failures)

    # Admin accessibility contracts: these intentionally fail before the B improvement.
    require('id="login-error-summary" class="error-summary" role="alert" tabindex="-1" hidden' in admin,
            "الإدارة: لا يوجد ملخص أخطاء متاح لقارئات الشاشة", failures)
    require('id="email" type="email" autocomplete="email" required aria-describedby="email-error"' in admin,
            "الإدارة: حقل البريد لا يرتبط برسالة خطأ محلية", failures)
    require('id="password" type="password" autocomplete="current-password" required aria-describedby="password-error"' in admin,
            "الإدارة: حقل كلمة المرور لا يرتبط برسالة خطأ محلية", failures)
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
            require("sabaaek-logo-transparent.webp" in live,
                    "النشر: النسخة الحية لا تحتوي مرجع الشعار الشفاف", failures)
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
