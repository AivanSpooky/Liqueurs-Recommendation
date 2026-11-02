"""Правила опорных слов (паттерн Specification): срабатывают на вопросе и дают вес классу."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .lexicon import Lexicon, Mention
from .text import normalize


@dataclass(frozen=True)
class Utterance:
    """Вопрос после нормализации вместе с найденными местозаменителями."""

    text: str
    mentions: tuple[Mention, ...]

    @classmethod
    def parse(cls, raw: str, lexicon: Lexicon) -> Utterance:
        text = normalize(raw)
        return cls(text, lexicon.mentions(text))

    def count(self, kind: str) -> int:
        return sum(1 for mention in self.mentions if mention.kind == kind)


class Rule(ABC):
    """Опорное слово или условие на местозаменители."""

    weight: float
    label: str

    @abstractmethod
    def fires(self, utterance: Utterance) -> bool:
        """Сработало ли правило на вопросе."""


@dataclass(frozen=True)
class PatternRule(Rule):
    """Основа слова или словосочетание (регулярное выражение по нормализованному тексту)."""

    pattern: str
    weight: float = 1.0

    @property
    def label(self) -> str:
        return self.pattern

    def fires(self, utterance: Utterance) -> bool:
        return re.search(self.pattern, utterance.text) is not None


@dataclass(frozen=True)
class MentionRule(Rule):
    """Число упоминаний местозаменителя вида kind в диапазоне [low, high]."""

    kind: str
    low: int = 1
    high: Optional[int] = None
    weight: float = 1.0

    @property
    def label(self) -> str:
        return f"<{self.kind}>×{self.low}..{self.high if self.high is not None else '∞'}"

    def fires(self, utterance: Utterance) -> bool:
        count = utterance.count(self.kind)
        return count >= self.low and (self.high is None or count <= self.high)


@dataclass(frozen=True)
class AllRule(Rule):
    """Конъюнкция правил (паттерн Composite): например, «сравни» вместе с упоминанием ликёра."""

    parts: tuple[Rule, ...]
    weight: float = 1.0

    @property
    def label(self) -> str:
        return " & ".join(part.label for part in self.parts)

    def fires(self, utterance: Utterance) -> bool:
        return all(part.fires(utterance) for part in self.parts)


def rule_from(spec: Mapping[str, Any]) -> Rule:
    """Фабрика правил из записи keywords.json."""
    if "all" in spec:
        return AllRule(tuple(rule_from(part) for part in spec["all"]), spec.get("weight", 1.0))
    if "mention" in spec:
        return MentionRule(spec["mention"], spec.get("min", 1), spec.get("max"), spec.get("weight", 1.0))
    return PatternRule(spec["pattern"], spec.get("weight", 1.0))
