"""Что делать, если точных совпадений нет: функция полезности и подсказка по ослаблению фильтров."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from recsys.domain.model import Liqueur

from .query import SearchQuery

RELEVANCE_SHARE = 0.5
MAX_RELAX_STEPS = 12
DROP_COST, WIDEN_COST = 1.0, 0.5


class UtilityFunction:
    """score(x) = U(x)·((1 − λ) + λ·r(x)): соответствие фильтрам × релевантность рекомендации.

    U(x) — взвешенная степень выполнения фильтров (очки за совпадение, штраф за нарушение
    пропорционален «расстоянию» до границы); r(x) — оценка рекомендателя ЛР3, если она есть.
    """

    def __init__(self, relevance_share: float = RELEVANCE_SHARE) -> None:
        self._share = relevance_share

    def score(self, query: SearchQuery, item: Liqueur, relevance: Optional[float] = None) -> float:
        fit = query.utility(item)
        return fit if relevance is None else fit * ((1.0 - self._share) + self._share * max(0.0, relevance))


@dataclass(frozen=True)
class Advice:
    """Подсказка: какие фильтры ослабить, чтобы появились точные совпадения."""

    changes: tuple[str, ...]
    query: SearchQuery
    found: int


@dataclass(frozen=True)
class Relaxation:
    """Один шаг ослабления: описание и получившийся запрос."""

    text: str
    query: SearchQuery
    cost: float


class RelaxationAdvisor:
    """Жадное ослабление: на каждом шаге — шаг, сильнее всего приближающий объекты к запросу."""

    def advise(self, query: SearchQuery, items: Sequence[Liqueur], changes: tuple[str, ...] = ()) -> Optional[Advice]:
        found = sum(query.matches(item) for item in items)
        if found or len(changes) >= MAX_RELAX_STEPS:
            return Advice(changes, query, found) if found and changes else None
        step = self._best(query, items)
        return self.advise(step.query, items, changes + (step.text,)) if step else None

    def _best(self, query: SearchQuery, items: Sequence[Liqueur]) -> Optional[Relaxation]:
        options = [self._option(query, index) for index in range(len(query.filters))]
        return max(options, key=lambda option: self._gain(option, items)) if options else None

    @staticmethod
    def _option(query: SearchQuery, index: int) -> Relaxation:
        old = query.filters[index]
        new = old.relaxed()
        text = f"{old.describe()} → {new.describe() if new else 'фильтр снят'}"
        return Relaxation(text, query.with_filter(index, new), old.weight * (WIDEN_COST if new else DROP_COST))

    @staticmethod
    def _gain(option: Relaxation, items: Sequence[Liqueur]) -> tuple[bool, float, float]:
        has_matches = any(option.query.matches(item) for item in items)
        return has_matches, round(max(option.query.utility(item) for item in items), 6), -option.cost
