"""Операции объединённой системы (паттерн Command): поиск, уточнение, рекомендация.

Цикл работы: поиск → лайки/дизлайки → рекомендации (ЛР3) → уточнение фильтрами → …
Каждая операция создаёт шаг истории; уточнение работает с результатами текущего шага.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Mapping, Optional, Sequence

from recsys.recommend.recommender import Recommendation
from recsys.recommend.types import Mode, UserProfile, ValidationError
from recsys.service import RecommendationService
from search.engine import SearchEngine, SearchResult
from search.query import QueryParser, SearchQuery

from .session import Row, Session, Step

SCOPES = ("catalog", "current")


class Command(ABC):
    """Операция над сессией: разбор параметров → вычисление → новый шаг истории."""

    def __init__(self, recsys: RecommendationService, parser: QueryParser, engine: SearchEngine) -> None:
        self._recsys, self._parser, self._engine = recsys, parser, engine

    def execute(self, session: Session, payload: Mapping[str, Any]) -> Step:
        return session.history.push(self.step(session, payload))

    @abstractmethod
    def step(self, session: Session, payload: Mapping[str, Any]) -> Step:
        """Новый шаг (индекс и родителя проставляет история)."""

    def _query(self, payload: Mapping[str, Any]) -> SearchQuery:
        filters = payload.get("filters") or {}
        return self._parser.parse(filters if isinstance(filters, Mapping) else _bad_filters())


def _bad_filters() -> Mapping[str, Any]:
    raise ValidationError(["фильтры должны быть JSON-объектом"])


def search_rows(result: SearchResult, explanations: Mapping[str, Recommendation]) -> tuple[Row, ...]:
    """Выдача поиска → строки истории (объяснения рекомендаций сохраняются)."""
    return tuple(Row(h.item.id, h.score, h.fit, h.exact, h.unmet, h.relevance, explanations.get(h.item.id))
                 for h in result.hits)


def search_step(kind: str, title: str, result: SearchResult, filters: Mapping[str, Any], **extra: Any) -> Step:
    rows = search_rows(result, extra.pop("explanations", {}))
    return Step(0, kind, title, rows, filters, exact=result.exact, message=result.message, advice=result.advice, **extra)


def summary(query: SearchQuery) -> str:
    return "; ".join(query.describe()) or "без ограничений"


class SearchCommand(Command):
    """ЛР4: новый поиск по всему каталогу."""

    def step(self, session: Session, payload: Mapping[str, Any]) -> Step:
        query = self._query(payload)
        return search_step("search", f"Поиск: {summary(query)}", self._engine.search(query), payload.get("filters") or {})


class RefineCommand(Command):
    """РК1: фильтрация результатов текущего шага (поиска или рекомендаций)."""

    def step(self, session: Session, payload: Mapping[str, Any]) -> Step:
        current, query = _require_current(session), self._query(payload)
        relevance = {row.item_id: row.relevance for row in current.rows if row.relevance is not None}
        result = self._engine.search(query, current.ids(), relevance or None)
        return search_step("refine", f"Уточнение шага №{current.index + 1}: {summary(query)}", result,
                           payload.get("filters") or {}, explanations=_explanations(current.rows))


def _require_current(session: Session) -> Step:
    if session.history.current is None:
        raise ValidationError(["нечего уточнять: сначала выполните поиск или запросите рекомендации"])
    return session.history.current


def _explanations(rows: Sequence[Row]) -> dict[str, Recommendation]:
    return {row.item_id: row.recommendation for row in rows if row.recommendation is not None}


def auto_mode(profile: UserProfile) -> Mode:
    """v1 — одна затравка; v2 — только лайки; v3 — есть дизлайки (или только они)."""
    if profile.dislikes or not profile.likes:
        return Mode.FULL
    return Mode.SEED if len(profile.likes) == 1 else Mode.LIKES


class RecommendCommand(Command):
    """ЛР3 внутри РК1: рекомендации по профилю сессии; область — каталог или текущая выдача."""

    def step(self, session: Session, payload: Mapping[str, Any]) -> Step:
        request = self._recsys.parse(self._request_payload(session, payload))
        ranked = self._recsys.recommend(replace(request, top_n=len(self._recsys.catalog)))
        title = f"Рекомендации {request.mode.value} · {self._recsys.recommender.rankers[request.ranker].title}"
        return self._filtered(request.top_n, ranked, title, payload) if payload.get("use_filters") else \
            Step(0, "recommend", title, tuple(_rec_row(rec) for rec in ranked[: request.top_n]), settings=dict(payload))

    def _request_payload(self, session: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
        profile, pool = session.profile, self._pool(session, payload.get("scope", "catalog"))
        base = {"mode": auto_mode(profile).value, "likes": list(profile.likes), "dislikes": list(profile.dislikes)}
        options = {key: payload[key] for key in ("top_n", "ranker", "policy") if key in payload}
        return {**base, **options, "pool": pool}

    def _pool(self, session: Session, scope: Any) -> Optional[list[str]]:
        if scope not in SCOPES:
            raise ValidationError([f"область рекомендаций: допустимо {', '.join(SCOPES)}"])
        return _require_current(session).ids() if scope == "current" else None

    def _filtered(self, top_n: int, ranked: list[Recommendation], title: str, payload: Mapping[str, Any]) -> Step:
        query, explanations = self._query(payload), {rec.item.id: rec for rec in ranked}
        result = self._engine.search(query, list(explanations), {i: rec.score for i, rec in explanations.items()})
        result = replace(result, hits=result.hits[:top_n])
        return search_step("recommend", f"{title} + фильтры: {summary(query)}", result, payload.get("filters") or {},
                           settings=dict(payload), explanations=explanations)


def _rec_row(rec: Recommendation) -> Row:
    return Row(rec.item.id, rec.score, relevance=rec.score, recommendation=rec)
