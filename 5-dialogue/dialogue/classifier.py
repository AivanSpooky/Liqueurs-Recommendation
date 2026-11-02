"""Классификатор вопросов по опорным словам: сумма весов сработавших правил каждого класса."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .lexicon import Lexicon
from .rules import Rule, Utterance, rule_from


@dataclass(frozen=True)
class QuestionClass:
    """Класс вопросов и его опорные слова."""

    key: str
    rules: tuple[Rule, ...]

    def hits(self, utterance: Utterance) -> list[Rule]:
        return [rule for rule in self.rules if rule.fires(utterance)]

    def score(self, utterance: Utterance) -> float:
        return sum(rule.weight for rule in self.hits(utterance))


@dataclass(frozen=True)
class Prediction:
    """Решение классификатора и его обоснование: баллы классов и сработавшие опорные слова."""

    key: str
    scores: Mapping[str, float]
    hits: Mapping[str, list[str]]
    utterance: Utterance


class KeywordClassifier:
    """Выбирает класс с наибольшим баллом; ниже порога — класс «нельзя ответить»."""

    def __init__(self, classes: Sequence[QuestionClass], lexicon: Lexicon, fallback: str, threshold: float) -> None:
        self._classes, self._lexicon = tuple(classes), lexicon
        self._fallback, self._threshold = fallback, threshold

    @classmethod
    def load(cls, keywords: Path, lexicon: Path) -> KeywordClassifier:
        spec = json.loads(Path(keywords).read_text(encoding="utf-8"))
        classes = [QuestionClass(c["key"], tuple(rule_from(r) for r in c["rules"])) for c in spec["classes"]]
        return cls(classes, Lexicon.load(lexicon), spec["fallback"], spec["threshold"])

    def classify(self, text: str) -> Prediction:
        utterance = Utterance.parse(text, self._lexicon)
        scores = {c.key: c.score(utterance) for c in self._classes}
        hits = {c.key: [rule.label for rule in c.hits(utterance)] for c in self._classes}
        return Prediction(self._decide(scores), scores, hits, utterance)

    def _decide(self, scores: Mapping[str, float]) -> str:
        best = max(scores, key=lambda key: scores[key])
        return best if scores[best] >= self._threshold else self._fallback
