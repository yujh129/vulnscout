from __future__ import annotations

import gettext
from pathlib import Path

from vulnscout.core.config import settings

_LOCALE_DIR = Path(__file__).resolve().parent.parent.parent / "locales"
_translations: dict[str, gettext.NullTranslations] = {}

def setup_i18n(language: str | None = None) -> None:
    lang = language or settings.language
    if lang not in _translations:
        try:
            t = gettext.translation("vulnscout", localedir=str(_LOCALE_DIR), languages=[lang], fallback=True)
        except FileNotFoundError:
            t = gettext.NullTranslations()
        _translations[lang] = t

def gettext(message: str) -> str:
    lang = settings.language
    if lang not in _translations:
        setup_i18n(lang)
    return _translations[lang].gettext(message)

_ = gettext
