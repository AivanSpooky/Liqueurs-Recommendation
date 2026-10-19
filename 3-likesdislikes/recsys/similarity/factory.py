"""Фабрика мер близости: собирает итоговую меру ЛР2 под конкретный каталог."""
from __future__ import annotations

from operator import attrgetter
from typing import Mapping

from ..domain.catalog import Catalog
from ..domain.model import SugarClass
from .composite import Component, WeightedSum
from .measures import (
    ExactMatch, NormalizedEuclidean, NumericAxis, OrdinalSimilarity,
    SimilarityMeasure, SimpleMatching, WuPalmer,
)

# Экспертные веса ω из ЛР 2.3 (обоснование — отчёт, раздел 2.5).
EXPERT_WEIGHTS: Mapping[str, float] = {
    "taste": 0.35, "numeric": 0.30, "binary": 0.15,
    "sugar_class": 0.10, "country": 0.05, "producer": 0.05,
}
NUMERIC_FIELDS = ("abv", "sugar", "volume")
BINARY_FIELDS = ("bitter", "wood_contact")


class MeasureFactory:
    """Паттерн Factory: создание частных и итоговой мер для каталога."""

    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    def expert(self) -> WeightedSum:
        return self.weighted(EXPERT_WEIGHTS)

    def weighted(self, weights: Mapping[str, float]) -> WeightedSum:
        parts = self.partial_measures()
        return WeightedSum([Component(parts[name], weight) for name, weight in weights.items()])

    def partial_measures(self) -> dict[str, SimilarityMeasure]:
        measures = [WuPalmer(), self.numeric(), SimpleMatching([attrgetter(f) for f in BINARY_FIELDS]),
                    OrdinalSimilarity(lambda item: item.sugar_class.rank, len(SugarClass)),
                    ExactMatch("country", attrgetter("country")), ExactMatch("producer", attrgetter("producer"))]
        return {measure.name: measure for measure in measures}

    def numeric(self) -> NormalizedEuclidean:
        return NormalizedEuclidean([NumericAxis.fit(f, attrgetter(f), self._catalog) for f in NUMERIC_FIELDS])
