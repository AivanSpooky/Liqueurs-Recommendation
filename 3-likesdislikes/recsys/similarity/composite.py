"""Итоговая мера — взвешенная сумма частных мер (паттерн Composite, ЛР 2.3)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..domain.model import Liqueur
from .measures import SimilarityMeasure


@dataclass(frozen=True)
class Component:
    """Частная мера и её вес ω_k в итоговой сумме."""

    measure: SimilarityMeasure
    weight: float


class WeightedSum(SimilarityMeasure):
    """sim(x, y) = Σ ω_k · sim_k(x, y), Σ ω_k = 1 — выпуклая комбинация остаётся в [0, 1]."""

    name = "total"

    def __init__(self, components: Sequence[Component]) -> None:
        total = sum(component.weight for component in components)
        self._components = tuple(Component(c.measure, c.weight / total) for c in components)

    @property
    def weights(self) -> dict[str, float]:
        return {c.measure.name: c.weight for c in self._components}

    def contributions(self, a: Liqueur, b: Liqueur) -> dict[str, float]:
        """Вклад ω_k · sim_k каждой частной меры — основа объяснения рекомендации."""
        return {c.measure.name: c.weight * c.measure(a, b) for c in self._components}

    def similarity(self, a: Liqueur, b: Liqueur) -> float:
        return sum(self.contributions(a, b).values())
