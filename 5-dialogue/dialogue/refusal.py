"""Вежливый ответ по шаблону для вопросов класса 6 «нельзя дать ответ»."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .rules import Rule, Utterance, rule_from


@dataclass(frozen=True)
class RefusalKind:
    """Причина отказа: опорные слова, объяснение причины и встречное предложение."""

    key: str
    rules: tuple[Rule, ...]
    reason: str
    offer: str

    def matches(self, utterance: Utterance) -> bool:
        return any(rule.fires(utterance) for rule in self.rules)


def kind_from(spec: Mapping[str, Any]) -> RefusalKind:
    rules = tuple(rule_from(r) for r in spec.get("rules", []))
    return RefusalKind(spec["key"], rules, spec["reason"], spec["offer"])


class RefusalTemplates:
    """Шаблон «<извинение> <причина> <что могу предложить>» с выбором причины по опорным словам."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._template, self._apology = data["template"], data["apology"]
        self._kinds = [kind_from(spec) for spec in data["kinds"]]
        self._default = kind_from(data["default"])

    @classmethod
    def load(cls, path: Path) -> RefusalTemplates:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def kind(self, utterance: Utterance) -> RefusalKind:
        return next((kind for kind in self._kinds if kind.matches(utterance)), self._default)

    def answer(self, utterance: Utterance) -> str:
        kind = self.kind(utterance)
        return self._template.format(apology=self._apology, reason=kind.reason, offer=kind.offer)
