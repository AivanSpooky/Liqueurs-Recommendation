"""Лексикон местозаменителей: ликёры, коктейли, вкусы, страны, признаки."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Pattern, Sequence

from .text import normalize


@dataclass(frozen=True)
class Mention:
    """Найденное в вопросе значение местозаменителя, например <ликёр> = L28."""

    kind: str
    value: str
    alias: str


@dataclass(frozen=True)
class Entry:
    kind: str
    value: str
    alias: str
    pattern: Pattern[str]

    def find(self, text: str) -> Mention | None:
        return Mention(self.kind, self.value, self.alias) if self.pattern.search(text) else None


def entry(kind: str, value: str, alias: str) -> Entry:
    """Псевдоним ищется с начала слова: основа «шартрез» находит «шартреза»."""
    return Entry(kind, value, alias, re.compile(rf"(?<![\w-]){re.escape(normalize(alias))}"))


class Lexicon:
    """Словарь местозаменителей (паттерн Repository над lexicon.json)."""

    def __init__(self, table: Mapping[str, Mapping[str, Sequence[str]]]) -> None:
        kinds = {kind: values for kind, values in table.items() if isinstance(values, Mapping)}
        self._entries = [entry(k, v, a) for k, values in kinds.items() for v, aliases in values.items() for a in aliases]

    @classmethod
    def load(cls, path: Path) -> Lexicon:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def mentions(self, text: str) -> tuple[Mention, ...]:
        """Различные значения, упомянутые в нормализованном тексте."""
        found = (e.find(text) for e in self._entries)
        unique = {(m.kind, m.value): m for m in found if m is not None}
        return tuple(unique.values())
