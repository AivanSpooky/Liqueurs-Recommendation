"""Матрица смежности G_ij = sim(o_i, o_j): кэш попарных близостей (паттерн Proxy)."""
from __future__ import annotations

from typing import Sequence

from ..domain.catalog import Catalog
from .measures import SimilarityMeasure


class SimilarityMatrix:
    """Предвычисленные близости всех пар каталога; n = 30 → 900 значений, O(1) доступ."""

    def __init__(self, catalog: Catalog, measure: SimilarityMeasure) -> None:
        self.measure = measure
        self._values = {(a.id, b.id): measure(a, b) for a in catalog for b in catalog}

    def get(self, a_id: str, b_id: str) -> float:
        return self._values[(a_id, b_id)]

    def row(self, a_id: str, others: Sequence[str]) -> list[float]:
        return [self.get(a_id, other) for other in others]

    def best(self, target: str, anchors: Sequence[str]) -> tuple[str, float]:
        """Ближайший к target объект из anchors и близость до него."""
        anchor = max(anchors, key=lambda other: self.get(target, other))
        return anchor, self.get(target, anchor)
