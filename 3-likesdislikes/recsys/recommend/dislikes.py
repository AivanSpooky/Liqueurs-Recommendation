"""Политики учёта дизлайков (ПСВ3): корректируют оценку кандидата (паттерн Strategy)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..similarity.matrix import SimilarityMatrix
from .ranking import Adjust, keep
from .types import Scored, UserProfile

EXCLUDE_THRESHOLD = 0.7
PENALTY_WEIGHT = 1.0


class DislikePolicy(ABC):
    """Интерфейс: профиль → функция корректировки оценки (None — исключить объект)."""

    key = "base"
    title = ""
    default_strength = PENALTY_WEIGHT

    def __init__(self, matrix: SimilarityMatrix, strength: Optional[float] = None) -> None:
        self._matrix = matrix
        self._strength = self.default_strength if strength is None else strength

    def adjuster(self, profile: UserProfile) -> Adjust:
        if not profile.dislikes:
            return keep
        return lambda scored: self.adjust(scored, profile)

    @abstractmethod
    def adjust(self, scored: Scored, profile: UserProfile) -> Optional[Scored]:
        """Скорректированная оценка кандидата."""


class ExcludeOnly(DislikePolicy):
    """1. Исключаются только сами дизлайкнутые объекты (они и так не кандидаты)."""

    key = "exclude"
    title = "1. Только исключить дизлайки"

    def adjust(self, scored: Scored, profile: UserProfile) -> Optional[Scored]:
        return scored


class ThresholdExclusion(DislikePolicy):
    """2. Исключить объекты, слишком похожие на дизлайк: max sim(x, d_j) ≥ τ."""

    key = "threshold"
    title = "2. Исключить похожие на дизлайки"
    default_strength = EXCLUDE_THRESHOLD

    def adjust(self, scored: Scored, profile: UserProfile) -> Optional[Scored]:
        _, similarity = self._matrix.best(scored.item_id, profile.dislikes)
        return None if similarity >= self._strength else scored


class SubtractivePenalty(DislikePolicy):
    """3. Вычитание (как в формуле Роккио): score − β·max_j sim(x, d_j)."""

    key = "subtract"
    title = "3. Штраф за близость к дизлайку"

    def adjust(self, scored: Scored, profile: UserProfile) -> Optional[Scored]:
        blame, similarity = self._matrix.best(scored.item_id, profile.dislikes)
        return scored.penalized(self._strength * similarity, blame)


class ContrastivePenalty(DislikePolicy):
    """4. Контрастный штраф: β·max(0, sim(x, d) − sim(x, ближайший лайк)).

    Штрафуется только то, что ближе к дизлайку, чем к любому лайку: дизлайк одного
    объекта не «портит» весь любимый жанр, к которому он принадлежит.
    """

    key = "contrastive"
    title = "4. Контрастный штраф"

    def adjust(self, scored: Scored, profile: UserProfile) -> Optional[Scored]:
        blame, against = self._matrix.best(scored.item_id, profile.dislikes)
        support = (self._matrix.best(scored.item_id, profile.likes)[1]
                   if profile.likes else 0.0)
        penalty = self._strength * max(0.0, against - support)
        return scored.penalized(penalty, blame)
