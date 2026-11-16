"""
Technical Terminology Glossary and Name Preservation for Video Editing.

Provides:
- Bidirectional Persian <-> English terminology mappings for video editing, software, and common dialogue
- Preservation of proper names, product names, acronyms, and technical terms
"""

from typing import Dict, List, Tuple


COMMON_GLOSSARY: List[Tuple[str, str]] = [
    # Video & Tech terms
    ("timeline", "تایم‌لاین"),
    ("sequence", "سکانس"),
    ("clip", "کلیپ"),
    ("cut", "برش"),
    ("audio", "صدا"),
    ("video", "ویدیو"),
    ("track", "ترک"),
    ("transition", "ترنزیشن"),
    ("subtitle", "زیرنویس"),
    ("caption", "کپشن"),
    ("frame rate", "نرخ فریم"),
    ("fps", "فریم بر ثانیه"),
    ("resolution", "کیفیت تصویر"),
    ("export", "خروجی گرفتن"),
    ("import", "وارد کردن"),
    ("render", "رندر"),
    ("effect", "افکت"),
    ("layer", "لایه"),
    ("silence", "سکوت"),
    ("speech", "گفتار"),
    ("transcript", "متن پیاده شده"),
    ("whisper", "ویسپر"),
    ("ai", "هوش مصنوعی"),
    ("premiere", "پریمیر"),
    ("adobe", "ادوبی"),
    ("youtube", "یوتیوب"),
    ("tutorial", "آموزش"),
    ("editor", "تدوین‌گر"),
    ("project", "پروژه"),
    ("microphone", "میکروفون"),
    ("volume", "میزان صدا"),
    ("gain", "گین"),
    ("noise", "نویز"),

    # Common spoken conversational phrases
    ("hello and welcome", "سلام و خوش آمدید"),
    ("in this video", "در این ویدیو"),
    ("as you can see", "همان‌طور که مشاهده می‌کنید"),
    ("thank you for watching", "از تماشای شما متشکرم"),
    ("don't forget to subscribe", "سابسکرایب کردن را فراموش نکنید"),
    ("let's get started", "بیایید شروع کنیم"),
    ("first of all", "قبل از هر چیز"),
    ("next step", "مرحله بعدی"),
    ("finally", "در نهایت"),
    ("for example", "برای مثال"),
    ("good luck", "موفق باشید"),
]

EN_TO_FA: Dict[str, str] = {en.lower(): fa for en, fa in COMMON_GLOSSARY}
FA_TO_EN: Dict[str, str] = {fa: en for en, fa in COMMON_GLOSSARY}
