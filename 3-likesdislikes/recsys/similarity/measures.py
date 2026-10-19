"""Частные меры близости (выбраны в ЛР2). Все возвращают sim ∈ [0, 1], sim(x, x) = 1."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Sequence

from ..domain.model import Liqueur


class SimilarityMeasure(ABC):
    """Интерфейс меры близости двух объектов (паттерн Strategy)."""

    name: str = "measure"

    @abstractmethod
    def similarity(self, a: Liqueur, b: Liqueur) -> float:
        """Близость пары объектов в шкале [0, 1]."""

    def __call__(self, a: Liqueur, b: Liqueur) -> float:
        return self.similarity(a, b)


@dataclass(frozen=True)
class NumericAxis:
    """Числовая ось признака с min-max нормировкой по каталогу."""

    name: str
    getter: Callable[[Liqueur], float]
    low: float
    high: float

    @classmethod
    def fit(cls, name: str, getter: Callable[[Liqueur], float], items: Iterable[Liqueur]) -> NumericAxis:
        values = [getter(item) for item in items]
        return cls(name, getter, min(values), max(values))

    @property
    def span(self) -> float:
        return self.high - self.low

    def normalize(self, item: Liqueur) -> float:
        return (self.getter(item) - self.low) / self.span if self.span else 0.0


class NormalizedEuclidean(SimilarityMeasure):
    """sim = 1 − sqrt(Σ (x'_d − y'_d)² / D): нормированное евклидово расстояние (ЛР 2.1a)."""

    name = "numeric"

    def __init__(self, axes: Sequence[NumericAxis]) -> None:
        self.axes = tuple(axes)

    def similarity(self, a: Liqueur, b: Liqueur) -> float:
        squares = [(axis.normalize(a) - axis.normalize(b)) ** 2 for axis in self.axes]
        return 1.0 - math.sqrt(sum(squares) / len(squares))


class SimpleMatching(SimilarityMeasure):
    """Сокал–Миченер: доля совпадающих бинарных признаков, (a + d) / n (ЛР 2.1b)."""

    name = "binary"

    def __init__(self, getters: Sequence[Callable[[Liqueur], bool]]) -> None:
        self._getters = tuple(getters)

    def similarity(self, a: Liqueur, b: Liqueur) -> float:
        matches = [get(a) == get(b) for get in self._getters]
        return sum(matches) / len(matches)


class WuPalmer(SimilarityMeasure):
    """У–Палмер по таксономии вкуса: 2·depth(LCA) / (depth(x) + depth(y)) (ЛР 2.2)."""

    name = "taste"

    def similarity(self, a: Liqueur, b: Liqueur) -> float:
        common = a.taste.common_depth(b.taste)
        return 2 * common / (len(a.taste.levels) + len(b.taste.levels))


class OrdinalSimilarity(SimilarityMeasure):
    """Порядковая шкала из k термов: sim = 1 − |ord x − ord y| / (k − 1)."""

    name = "sugar_class"

    def __init__(self, getter: Callable[[Liqueur], int], levels: int) -> None:
        self._getter = getter
        self._levels = levels

    def similarity(self, a: Liqueur, b: Liqueur) -> float:
        return 1.0 - abs(self._getter(a) - self._getter(b)) / (self._levels - 1)


class ExactMatch(SimilarityMeasure):
    """δ-функция для номинального признака: 1 — значения совпали, 0 — нет."""

    def __init__(self, name: str, getter: Callable[[Liqueur], Hashable]) -> None:
        self.name = name
        self._getter = getter

    def similarity(self, a: Liqueur, b: Liqueur) -> float:
        return 1.0 if self._getter(a) == self._getter(b) else 0.0
