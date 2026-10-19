"""Контентная рекомендательная система ПСВ1–ПСВ3 (ЛР3)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from ..domain.catalog import Catalog
from ..domain.model import Liqueur
from ..similarity.composite import WeightedSum
from ..similarity.matrix import SimilarityMatrix
from .dislikes import DislikePolicy
from .ranking import Adjust, AvoidRanker, LikesRanker
from .types import RecommendRequest, Scored


@dataclass(frozen=True)
class Recommendation:
    """Элемент выдачи с объяснением: на какой лайк похож и за счёт каких признаков."""

    rank: int
    item: Liqueur
    score: float
    anchor: Optional[Liqueur]
    contributions: Mapping[str, float]
    penalty: float
    blame: Optional[Liqueur]
    group: Optional[int]


class ContentRecommender:
    """Фасад рекомендательного ядра: кандидаты → стратегия → дизлайки → top-N + объяснение."""

    def __init__(self, catalog: Catalog, matrix: SimilarityMatrix, rankers: Mapping[str, LikesRanker],
                 policies: Mapping[str, DislikePolicy]) -> None:
        self._catalog, self._matrix = catalog, matrix
        self.rankers, self.policies = dict(rankers), dict(policies)

    @property
    def matrix(self) -> SimilarityMatrix:
        return self._matrix

    def recommend(self, request: RecommendRequest) -> list[Recommendation]:
        ranked = self.rank(request)[: request.top_n]
        return [self._present(position, scored) for position, scored in enumerate(ranked, start=1)]

    def rank(self, request: RecommendRequest) -> list[Scored]:
        """Полный ранжированный список кандидатов (без отсечения top-N)."""
        profile, candidates = request.profile, self.candidates(request)
        if not profile.likes:
            return AvoidRanker(self._matrix).rank(profile.dislikes, candidates)
        return self.rankers[request.ranker].rank(profile.likes, candidates, self._adjuster(request))

    def candidates(self, request: RecommendRequest) -> list[str]:
        pool = request.pool if request.pool is not None else self._catalog.ids()
        return [item for item in pool if item not in request.profile.rated]

    def _adjuster(self, request: RecommendRequest) -> Adjust:
        return self.policies[request.policy].adjuster(request.profile)

    def _present(self, position: int, scored: Scored) -> Recommendation:
        item, anchor, blame = (self._optional(key) for key in (scored.item_id, scored.anchor, scored.blame))
        parts = self._explain(item, anchor) if anchor else {}
        return Recommendation(position, item, scored.score, anchor, parts, scored.penalty, blame, scored.group)

    def _optional(self, item_id: Optional[str]) -> Optional[Liqueur]:
        return self._catalog.get(item_id) if item_id else None

    def _explain(self, item: Liqueur, anchor: Liqueur) -> Mapping[str, float]:
        measure = self._matrix.measure
        return measure.contributions(anchor, item) if isinstance(measure, WeightedSum) else {}
