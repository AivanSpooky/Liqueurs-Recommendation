"""Value-объекты рекомендательной подсистемы: режим, профиль, запрос, оценка."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional


class Mode(Enum):
    """Версия рекомендательной системы (сценарий ЛР3)."""

    SEED = "v1"
    LIKES = "v2"
    FULL = "v3"

    @property
    def title(self) -> str:
        return {"v1": "Один ликёр-затравка", "v2": "Набор лайков", "v3": "Лайки и дизлайки"}[self.value]


@dataclass(frozen=True)
class UserProfile:
    """Предпочтения пользователя. Порядок лайков — порядок их установки (время)."""

    likes: tuple[str, ...] = ()
    dislikes: tuple[str, ...] = ()

    @property
    def rated(self) -> frozenset[str]:
        return frozenset(self.likes) | frozenset(self.dislikes)


@dataclass(frozen=True)
class RecommendRequest:
    """Полностью разобранный запрос рекомендации."""

    mode: Mode
    profile: UserProfile
    top_n: int = 5
    ranker: str = "group"
    policy: str = "contrastive"
    pool: Optional[tuple[str, ...]] = None


@dataclass(frozen=True)
class Scored:
    """Кандидат с числовой оценкой релевантности и «причинами» оценки."""

    item_id: str
    score: float
    anchor: Optional[str] = None
    penalty: float = 0.0
    blame: Optional[str] = None
    group: Optional[int] = None

    def penalized(self, penalty: float, blame: str) -> Scored:
        return replace(self, score=self.score - penalty, penalty=penalty, blame=blame)

    def in_group(self, group: int) -> Scored:
        return replace(self, group=group)


class ValidationError(ValueError):
    """Ошибка проверки пользовательского ввода; хранит список сообщений для интерфейса."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = list(messages)
