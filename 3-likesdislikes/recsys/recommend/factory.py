"""Сборка рекомендательной системы из компонентов (Composition Root)."""
from __future__ import annotations

from typing import Iterable, TypeVar

from ..domain.catalog import Catalog
from ..similarity.factory import MeasureFactory
from ..similarity.matrix import SimilarityMatrix
from .dislikes import ContrastivePenalty, DislikePolicy, ExcludeOnly, SubtractivePenalty, ThresholdExclusion
from .ranking import (
    BalancedRanker, GroupRanker, LikesRanker, MaxRanker, MeanRanker, RecencyRanker, RoundRobinRanker,
)
from .recommender import ContentRecommender

RANKER_TYPES = (MeanRanker, RecencyRanker, BalancedRanker, MaxRanker, RoundRobinRanker, GroupRanker)
POLICY_TYPES = (ExcludeOnly, ThresholdExclusion, SubtractivePenalty, ContrastivePenalty)
DEFAULT_RANKER = GroupRanker.key
DEFAULT_POLICY = ContrastivePenalty.key

S = TypeVar("S", LikesRanker, DislikePolicy)


def registry(types: Iterable[type[S]], matrix: SimilarityMatrix) -> dict[str, S]:
    """Реестр стратегий «ключ → экземпляр» (используется интерфейсом и валидатором)."""
    return {cls.key: cls(matrix) for cls in types}


def build_matrix(catalog: Catalog) -> SimilarityMatrix:
    return SimilarityMatrix(catalog, MeasureFactory(catalog).expert())


def build_recommender(catalog: Catalog, matrix: SimilarityMatrix | None = None) -> ContentRecommender:
    matrix = matrix or build_matrix(catalog)
    return ContentRecommender(catalog, matrix, registry(RANKER_TYPES, matrix), registry(POLICY_TYPES, matrix))
