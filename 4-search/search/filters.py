"""Фильтры параметрического поиска (паттерн Specification).

Каждый фильтр умеет: проверить объект строго (matches), оценить степень соответствия
degree ∈ [0, 1] для «мягкого» поиска, описать себя и предложить ослабленную версию.
"""
from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from typing import Callable, Optional

from recsys.domain.model import Liqueur, SugarClass

RANGE_TOLERANCE = 0.25  # выход за границу на 25 % размаха признака → степень 0
RANGE_RELAX_STEP = 0.10  # шаг ослабления диапазона — 10 % размаха
EPS = 1e-9
FUZZY_MIN = 0.7  # нечёткое совпадение слабее 0.7 считается несовпадением


def normalize(text: str) -> str:
    """Регистр и диакритика не важны: «KAHLUA» найдёт «Kahlúa»."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


class Filter(ABC):
    """Ограничение на признак объекта; key, label, weight задают наследники-dataclass."""

    key: str
    label: str
    weight: float

    @abstractmethod
    def degree(self, item: Liqueur) -> float:
        """Степень соответствия объекта фильтру: 1 — полностью, 0 — совсем нет."""

    @abstractmethod
    def describe(self) -> str:
        """Человекочитаемое описание ограничения."""

    @abstractmethod
    def relaxed(self) -> Optional[Filter]:
        """Следующая, более мягкая версия фильтра; None — фильтр снимается целиком."""

    def matches(self, item: Liqueur) -> bool:
        return self.degree(item) >= 1.0 - EPS


@dataclass(frozen=True)
class RangeFilter(Filter):
    """Числовой диапазон [low, high]; вне диапазона степень убывает линейно с расстоянием."""

    key: str
    label: str
    unit: str
    getter: Callable[[Liqueur], float]
    span: float
    low: Optional[float] = None
    high: Optional[float] = None
    weight: float = 1.0

    def distance(self, item: Liqueur) -> float:
        value = self.getter(item)
        below = self.low - value if self.low is not None else 0.0
        return max(0.0, below, value - self.high if self.high is not None else 0.0)

    def degree(self, item: Liqueur) -> float:
        return max(0.0, 1.0 - self.distance(item) / (RANGE_TOLERANCE * self.span))

    def describe(self) -> str:
        low = "…" if self.low is None else f"{self.low:g}"
        high = "…" if self.high is None else f"{self.high:g}"
        return f"{self.label}: {low}–{high} {self.unit}".strip()

    def relaxed(self) -> Optional[Filter]:
        step = RANGE_RELAX_STEP * self.span
        low, high = (None if b is None else b + sign * step for b, sign in ((self.low, -1), (self.high, 1)))
        return replace(self, low=None if low is not None and low <= 0 else low, high=high)


@dataclass(frozen=True)
class ChoiceFilter(Filter):
    """Номинальный признак: значение из разрешённого множества (δ-функция)."""

    key: str
    label: str
    getter: Callable[[Liqueur], str]
    allowed: frozenset[str]
    weight: float = 1.0

    def degree(self, item: Liqueur) -> float:
        return 1.0 if self.getter(item) in self.allowed else 0.0

    def describe(self) -> str:
        return f"{self.label}: {', '.join(sorted(self.allowed))}"

    def relaxed(self) -> Optional[Filter]:
        return None


@dataclass(frozen=True)
class FlagFilter(Filter):
    """Бинарный признак: требуемое значение (да/нет)."""

    key: str
    label: str
    getter: Callable[[Liqueur], bool]
    expected: bool
    weight: float = 1.0

    def degree(self, item: Liqueur) -> float:
        return 1.0 if self.getter(item) == self.expected else 0.0

    def describe(self) -> str:
        return f"{self.label}: {'да' if self.expected else 'нет'}"

    def relaxed(self) -> Optional[Filter]:
        return None


@dataclass(frozen=True)
class TasteFilter(Filter):
    """Узлы таксономии вкуса; вне узла степень = доля общего пути (идея меры У–Палмера, ЛР2)."""

    nodes: tuple[tuple[str, ...], ...]
    key: str = "taste"
    label: str = "Вкус"
    weight: float = 1.0

    def degree(self, item: Liqueur) -> float:
        return max(item.taste.common_depth(node) / len(node) for node in self.nodes)

    def describe(self) -> str:
        return f"{self.label}: {'; '.join(' › '.join(node) for node in self.nodes)}"

    def relaxed(self) -> Optional[Filter]:
        parents = tuple(dict.fromkeys(node[:-1] if len(node) > 1 else node for node in self.nodes))
        return replace(self, nodes=parents) if parents != self.nodes else None


@dataclass(frozen=True)
class SugarClassFilter(Filter):
    """Порядковый признак «класс сладости»: соседний терм соответствует частично."""

    allowed: frozenset[SugarClass]
    key: str = "sugar_class"
    label: str = "Класс сладости"
    weight: float = 1.0

    def degree(self, item: Liqueur) -> float:
        gap = min(abs(item.sugar_class.rank - allowed.rank) for allowed in self.allowed)
        return 1.0 - gap / (len(SugarClass) - 1)

    def describe(self) -> str:
        return f"{self.label}: {', '.join(c.label for c in SugarClass if c in self.allowed)}"

    def relaxed(self) -> Optional[Filter]:
        ranks = {c.rank + d for c in self.allowed for d in (-1, 0, 1)}
        wider = frozenset(c for c in SugarClass if c.rank in ranks)
        return replace(self, allowed=wider) if wider != self.allowed else None


@dataclass(frozen=True)
class TextFilter(Filter):
    """Подстрока в названии или производителе; при опечатке — нечёткое совпадение (difflib)."""

    needle: str
    key: str = "name"
    label: str = "Название"
    weight: float = 1.0

    def degree(self, item: Liqueur) -> float:
        hay, needle = normalize(f"{item.name} {item.producer}"), normalize(self.needle)
        windows = [hay[i:i + len(needle)] for i in range(max(1, len(hay) - len(needle) + 1))]
        best = max(SequenceMatcher(None, needle, window).ratio() for window in windows)
        return best if best >= FUZZY_MIN else 0.0

    def describe(self) -> str:
        return f"{self.label}: «{self.needle}»"

    def relaxed(self) -> Optional[Filter]:
        return None
