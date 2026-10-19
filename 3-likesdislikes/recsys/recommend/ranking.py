"""Стратегии ранжирования по набору лайков (ПСВ2): подходы А, Б, В, Г и их варианты."""
from __future__ import annotations

from abc import ABC, abstractmethod
from itertools import zip_longest
from typing import Callable, Iterable, Optional, Sequence

from ..similarity.matrix import SimilarityMatrix
from .types import Scored

Adjust = Callable[[Scored], Optional[Scored]]
RECENCY_DECAY = 0.7
GROUP_THRESHOLD = 0.65


def keep(scored: Scored) -> Optional[Scored]:
    """Корректировка по умолчанию: оценку не меняет."""
    return scored


def by_score(items: Iterable[Optional[Scored]]) -> list[Scored]:
    """Убывание оценки; None (исключённые объекты) отбрасываются; при равенстве — по id."""
    return sorted((s for s in items if s is not None), key=lambda s: (-s.score, s.item_id))


def unique(items: Iterable[Scored]) -> list[Scored]:
    """Устранение дубликатов с сохранением первого вхождения."""
    first: dict[str, Scored] = {}
    for scored in items:
        first.setdefault(scored.item_id, scored)
    return list(first.values())


def interleave(lists: Sequence[Sequence[Scored]]) -> list[Scored]:
    """«Сшивание» списков: по одному объекту из каждого списка по очереди."""
    rounds = zip_longest(*lists)
    return unique(scored for row in rounds for scored in row if scored is not None)


class LikesRanker(ABC):
    """Интерфейс стратегии: лайки + кандидаты → ранжированный список."""

    key = "base"
    title = ""

    def __init__(self, matrix: SimilarityMatrix, threshold: float = GROUP_THRESHOLD) -> None:
        self._matrix = matrix
        self._threshold = threshold

    @abstractmethod
    def rank(self, likes: Sequence[str], candidates: Sequence[str], adjust: Adjust = keep) -> list[Scored]:
        """Ранжированный список кандидатов (adjust применяет дизлайки ПСВ3)."""


class WeightedMeanRanker(LikesRanker):
    """Шаблонный метод: score(x) = Σ w_i·sim(x, like_i) / Σ w_i; веса задают наследники."""

    def rank(self, likes: Sequence[str], candidates: Sequence[str], adjust: Adjust = keep) -> list[Scored]:
        weights = self.weights(likes)
        return by_score(adjust(self._score(likes, weights, item)) for item in candidates)

    def _score(self, likes: Sequence[str], weights: Sequence[float], item: str) -> Scored:
        sims = self._matrix.row(item, likes)
        value = sum(w * s for w, s in zip(weights, sims)) / sum(weights)
        return Scored(item, value, self._matrix.best(item, likes)[0])

    def weights(self, likes: Sequence[str]) -> list[float]:
        return [1.0] * len(likes)


class MeanRanker(WeightedMeanRanker):
    """А. Среднее арифметическое близостей ко всем лайкам."""

    key = "mean"
    title = "А. Среднее по лайкам"


class RecencyRanker(WeightedMeanRanker):
    """Б. Учёт времени: вес лайка затухает как γ^(возраст), последний лайк — вес 1."""

    key = "recency"
    title = "Б. С учётом времени лайков"

    def weights(self, likes: Sequence[str]) -> list[float]:
        return [RECENCY_DECAY ** (len(likes) - 1 - i) for i in range(len(likes))]


class BalancedRanker(WeightedMeanRanker):
    """В. Взвешенная сумма: вес лайка 1/|группа|, каждая группа интересов весит одинаково."""

    key = "balanced"
    title = "В. Взвешенная сумма (баланс групп)"

    def weights(self, likes: Sequence[str]) -> list[float]:
        groups = LikeGrouper(self._matrix, self._threshold).groups(likes)
        size = {like: len(group) for group in groups for like in group}
        return [1.0 / size[like] for like in likes]


class MaxRanker(LikesRanker):
    """Близость к ближайшему лайку: score(x) = max_i sim(x, like_i)."""

    key = "max"
    title = "Максимум по лайкам"

    def rank(self, likes: Sequence[str], candidates: Sequence[str], adjust: Adjust = keep) -> list[Scored]:
        return by_score(adjust(self._score(likes, item)) for item in candidates)

    def _score(self, likes: Sequence[str], item: str) -> Scored:
        anchor, value = self._matrix.best(item, likes)
        return Scored(item, value, anchor)


class RoundRobinRanker(LikesRanker):
    """Г′. Отдельный список для каждого лайка, затем сшивание по очереди без дубликатов."""

    key = "roundrobin"
    title = "Г′. Сшивание списков по каждому лайку"

    def rank(self, likes: Sequence[str], candidates: Sequence[str], adjust: Adjust = keep) -> list[Scored]:
        return interleave([self._for_like(like, candidates, adjust) for like in likes])

    def _for_like(self, like: str, candidates: Sequence[str], adjust: Adjust) -> list[Scored]:
        return by_score(adjust(Scored(item, self._matrix.get(like, item), like)) for item in candidates)


class GroupRanker(LikesRanker):
    """Г. Выделение групп лайков: среднее внутри группы, сшивание списков групп."""

    key = "group"
    title = "Г. Группы лайков + сшивание"

    def rank(self, likes: Sequence[str], candidates: Sequence[str], adjust: Adjust = keep) -> list[Scored]:
        groups = LikeGrouper(self._matrix, self._threshold).groups(likes)
        lists = [MeanRanker(self._matrix).rank(group, candidates, adjust)
                 for group in groups]
        return interleave([[s.in_group(i) for s in ranked]
                           for i, ranked in enumerate(lists)])


class AvoidRanker(LikesRanker):
    """Только дизлайки (лайков нет): score(x) = 1 − max_j sim(x, dislike_j)."""

    key = "avoid"
    title = "Удаление от дизлайков"

    def rank(self, likes: Sequence[str], candidates: Sequence[str], adjust: Adjust = keep) -> list[Scored]:
        return by_score(self._score(likes, item) for item in candidates)

    def _score(self, dislikes: Sequence[str], item: str) -> Scored:
        blame, value = self._matrix.best(item, dislikes)
        return Scored(item, 1.0 - value, blame=blame)


class LikeGrouper:
    """Группы интересов: компоненты связности графа лайков с ребром sim ≥ θ (single linkage)."""

    def __init__(self, matrix: SimilarityMatrix, threshold: float = GROUP_THRESHOLD) -> None:
        self._matrix = matrix
        self._threshold = threshold

    def groups(self, likes: Sequence[str]) -> list[list[str]]:
        groups: list[list[str]] = []
        for like in likes:
            groups = self._attach(groups, like)
        return sorted(groups, key=lambda g: (-len(g), min(map(likes.index, g))))

    def _attach(self, groups: list[list[str]], like: str) -> list[list[str]]:
        linked = [g for g in groups if self._linked(like, g)]
        rest = [g for g in groups if not self._linked(like, g)]
        return rest + [[member for g in linked for member in g] + [like]]

    def _linked(self, like: str, group: Sequence[str]) -> bool:
        return any(self._matrix.get(like, member) >= self._threshold
                   for member in group)
