"""Корпус вопросов ЛР5: исходные вопросы и их переформулировки по классам."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

ORIGINAL, PARAPHRASE = "вопрос", "переформулировка"


@dataclass(frozen=True)
class Sample:
    """Одна формулировка вопроса с эталонным классом."""

    text: str
    label: str
    question: str
    kind: str


def samples_of(cls: Mapping[str, Any]) -> Iterator[Sample]:
    for q in cls["questions"]:
        yield Sample(q["text"], cls["key"], q["id"], ORIGINAL)
        yield from (Sample(text, cls["key"], q["id"], PARAPHRASE) for text in q["paraphrases"])


class Corpus:
    """Набор классов вопросов (questions.json)."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self.classes = list(data["classes"])

    @classmethod
    def load(cls, path: Path) -> Corpus:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def samples(self) -> list[Sample]:
        return [sample for cls in self.classes for sample in samples_of(cls)]

    def titles(self) -> dict[str, str]:
        return {cls["key"]: cls["title"] for cls in self.classes}
