"""Рекомендательное ядро ЛР3: стратегии лайков, политики дизлайков, проверка запросов."""
from .dislikes import ContrastivePenalty, DislikePolicy, ExcludeOnly, SubtractivePenalty, ThresholdExclusion
from .factory import DEFAULT_POLICY, DEFAULT_RANKER, build_matrix, build_recommender
from .ranking import (
    AvoidRanker, BalancedRanker, GroupRanker, LikeGrouper, LikesRanker, MaxRanker, MeanRanker,
    RecencyRanker, RoundRobinRanker,
)
from .recommender import ContentRecommender, Recommendation
from .requests import RequestParser, RequestValidator
from .types import Mode, RecommendRequest, Scored, UserProfile, ValidationError

__all__ = [
    "ContrastivePenalty", "DislikePolicy", "ExcludeOnly", "SubtractivePenalty", "ThresholdExclusion",
    "DEFAULT_POLICY", "DEFAULT_RANKER", "build_matrix", "build_recommender",
    "AvoidRanker", "BalancedRanker", "GroupRanker", "LikeGrouper", "LikesRanker", "MaxRanker",
    "MeanRanker", "RecencyRanker", "RoundRobinRanker", "ContentRecommender", "Recommendation",
    "RequestParser", "RequestValidator", "Mode", "RecommendRequest", "Scored", "UserProfile",
    "ValidationError",
]
