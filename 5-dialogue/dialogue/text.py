"""Нормализация текста вопроса перед поиском опорных слов."""
from __future__ import annotations

import re
import unicodedata

NOISE = re.compile(r"[^\w\s%-]|(?<!\w)-|-(?!\w)")


def plain(char: str) -> str:
    """Снимает диакритику только с латиницы: «é» -> «e», но «й» остаётся «й»."""
    if char.isascii() or not "À" <= char <= "ɏ":
        return char
    return "".join(c for c in unicodedata.normalize("NFKD", char) if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Нижний регистр, ё -> е, без диакритики и пунктуации (дефис внутри слова сохраняется)."""
    lowered = "".join(plain(char) for char in text.casefold().replace("ё", "е"))
    return " ".join(NOISE.sub(" ", lowered).split())
