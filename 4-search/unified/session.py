"""Состояние пользователя объединённой системы: профиль и история запросов (паттерн Memento)."""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Optional

from recsys.recommend.recommender import Recommendation
from recsys.recommend.types import UserProfile, ValidationError
from search.fallback import Advice


@dataclass(frozen=True)
class Row:
    """Строка выдачи: объект, итоговая оценка, соответствие фильтрам, объяснение рекомендации."""

    item_id: str
    score: float
    fit: float = 1.0
    exact: bool = True
    unmet: tuple[tuple[str, float], ...] = ()
    relevance: Optional[float] = None
    recommendation: Optional[Recommendation] = None


@dataclass(frozen=True)
class Step:
    """Снимок (memento) одного шага: что спросили и что получили."""

    index: int
    kind: str
    title: str
    rows: tuple[Row, ...]
    filters: Mapping[str, Any] = field(default_factory=dict)
    settings: Mapping[str, Any] = field(default_factory=dict)
    exact: bool = True
    message: Optional[str] = None
    advice: Optional[Advice] = None
    parent: Optional[int] = None

    def ids(self) -> list[str]:
        return [row.item_id for row in self.rows]


class History:
    """Хранитель снимков: можно вернуться к любому шагу и уточнять от него дальше."""

    def __init__(self) -> None:
        self.steps: list[Step] = []
        self.cursor: Optional[int] = None

    @property
    def current(self) -> Optional[Step]:
        return self.steps[self.cursor] if self.cursor is not None else None

    def push(self, step: Step) -> Step:
        self.steps.append(replace(step, index=len(self.steps), parent=self.cursor))
        self.cursor = len(self.steps) - 1
        return self.steps[-1]

    def select(self, index: int) -> Step:
        if not 0 <= index < len(self.steps):
            raise ValidationError([f"в истории нет шага №{index + 1}"])
        self.cursor = index
        return self.steps[index]

    def clear(self) -> None:
        self.steps, self.cursor = [], None


@dataclass
class Session:
    """Сессия пользователя: профиль лайков/дизлайков и история шагов."""

    profile: UserProfile = field(default_factory=UserProfile)
    history: History = field(default_factory=History)

    def rate(self, kind: str, item_id: str) -> None:
        """kind: like / dislike — переключение отметки; remove — снять отметку."""
        likes = tuple(i for i in self.profile.likes if i != item_id)
        dislikes = tuple(i for i in self.profile.dislikes if i != item_id)
        toggled = {"like": item_id not in self.profile.likes, "dislike": item_id not in self.profile.dislikes}
        self.profile = UserProfile(likes + ((item_id,) if kind == "like" and toggled["like"] else ()),
                                   dislikes + ((item_id,) if kind == "dislike" and toggled["dislike"] else ()))

    def reset(self, keep_profile: bool = True) -> None:
        self.history.clear()
        self.profile = self.profile if keep_profile else UserProfile()


class SessionStore:
    """Сессии по идентификатору из cookie; потокобезопасно (сервер многопоточный)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def resolve(self, session_id: Optional[str]) -> tuple[str, Session]:
        with self._lock:
            key = session_id if session_id in self._sessions else uuid.uuid4().hex
            return key, self._sessions.setdefault(key, Session())
