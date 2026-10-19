"""JSON-представление состояния сессии для интерфейса."""
from __future__ import annotations

from typing import Any, Optional

from recsys.domain.catalog import Catalog
from recsys.web import presenter as lr3
from search.fallback import Advice

from .session import Row, Session, Step


def row(catalog: Catalog, entry: Row) -> dict[str, Any]:
    explanation = lr3.recommendation(entry.recommendation) if entry.recommendation else None
    unmet = [{"filter": text, "degree": degree} for text, degree in entry.unmet]
    base = {"item": lr3.liqueur(catalog.get(entry.item_id)), "score": round(entry.score, 4), "fit": round(entry.fit, 4)}
    return {**base, "exact": entry.exact, "unmet": unmet, "relevance": entry.relevance, "explanation": explanation}


def advice(value: Optional[Advice]) -> Optional[dict[str, Any]]:
    return {"changes": list(value.changes), "found": value.found} if value else None


def step(catalog: Catalog, value: Step) -> dict[str, Any]:
    head = {"index": value.index, "kind": value.kind, "title": value.title, "parent": value.parent}
    body = {"exact": value.exact, "message": value.message, "advice": advice(value.advice)}
    return {**head, **body, "filters": value.filters, "settings": value.settings,
            "rows": [row(catalog, entry) for entry in value.rows]}


def summary(value: Step) -> dict[str, Any]:
    return {"index": value.index, "kind": value.kind, "title": value.title, "count": len(value.rows),
            "exact": value.exact, "parent": value.parent}


def state(catalog: Catalog, session: Session) -> dict[str, Any]:
    current = session.history.current
    profile = {"likes": list(session.profile.likes), "dislikes": list(session.profile.dislikes)}
    history = [summary(entry) for entry in session.history.steps]
    return {"profile": profile, "history": history, "current": step(catalog, current) if current else None}
