"""Фасад объединённой системы (РК1): ядро ЛР3 + поиск ЛР4 + история сессий."""
from __future__ import annotations

from operator import attrgetter
from typing import Any, Mapping

from recsys.domain.model import SugarClass
from recsys.recommend.types import ValidationError
from recsys.service import RecommendationService
from search.engine import SearchEngine
from search.query import RANGES, WEIGHTS, QueryParser

from .operations import Command, RecommendCommand, RefineCommand, SearchCommand
from .session import Session, Step

COMMANDS = {"search": SearchCommand, "refine": RefineCommand, "recommend": RecommendCommand}
RATINGS = ("like", "dislike", "remove")


class UnifiedService:
    """Единая точка входа для интерфейса: операции, профиль, история, справочники фильтров."""

    def __init__(self, recsys: RecommendationService) -> None:
        self.recsys = recsys
        parser, engine = QueryParser(recsys.catalog), SearchEngine(recsys.catalog)
        self._commands: dict[str, Command] = {key: cls(recsys, parser, engine) for key, cls in COMMANDS.items()}

    def execute(self, session: Session, kind: str, payload: Mapping[str, Any]) -> Step:
        return self._commands[kind].execute(session, payload)

    def rate(self, session: Session, payload: Mapping[str, Any]) -> None:
        action, item_id = payload.get("action"), str(payload.get("id", ""))
        if action not in RATINGS or item_id not in self.recsys.catalog:
            raise ValidationError([f"отметка: действие {action!r} или объект {item_id!r} недопустимы"])
        session.rate(action, item_id)

    def filter_options(self) -> dict[str, Any]:
        catalog = self.recsys.catalog
        ranges = {key: self._bounds(attr) for key, (_, _, attr, _) in RANGES.items()}
        lists = {"countries": sorted(catalog.distinct(attrgetter("country"))),
                 "producers": sorted(catalog.distinct(attrgetter("producer")))}
        return {**lists, "ranges": ranges, "sugar_classes": [c.label for c in SugarClass], "weights": WEIGHTS}

    def _bounds(self, attr: str) -> dict[str, float]:
        values = [getattr(item, attr) for item in self.recsys.catalog]
        return {"min": min(values), "max": max(values)}
