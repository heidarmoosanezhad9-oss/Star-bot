import database as db
from languages import TEXTS, DEFAULT_LANG

def t(user_id: int, key: str, **kwargs) -> str:
    lang = db.get_user_lang(user_id)
    if lang not in TEXTS:
        lang = DEFAULT_LANG
    overrides = db.get_text_overrides(lang)
    text = overrides.get(key) or TEXTS[lang].get(key) or TEXTS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text

def lang_of(user_id: int) -> str:
    return db.get_user_lang(user_id)
