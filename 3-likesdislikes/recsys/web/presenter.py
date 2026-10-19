"""Преобразование доменных объектов в JSON для интерфейса (паттерн Presenter)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..domain.model import Liqueur
from ..domain.taxonomy import TaxonomyNode
from ..recommend.recommender import Recommendation

FEATURE_LABELS = {
    "taste": "вкус (таксономия)", "numeric": "крепость, сахар, объём", "binary": "горечь, выдержка в дереве",
    "sugar_class": "класс сладости", "country": "страна", "producer": "производитель",
}


def liqueur(item: Liqueur) -> dict[str, Any]:
    plain = {key: getattr(item, key) for key in ("id", "name", "producer", "country", "bitter", "wood_contact")}
    numbers = {"abv": item.abv, "sugar": item.sugar, "volume": item.volume, "notes": item.notes}
    taste = {"taste": list(item.taste.levels), "taste_code": item.taste.code, "sugar_class": item.sugar_class.label}
    return {**plain, **numbers, **taste}


def reference(item: Optional[Liqueur]) -> Optional[dict[str, str]]:
    return {"id": item.id, "name": item.name} if item else None


def recommendation(rec: Recommendation) -> dict[str, Any]:
    parts = [{"key": k, "label": FEATURE_LABELS.get(k, k), "value": round(v, 4)} for k, v in rec.contributions.items()]
    head = {"rank": rec.rank, "item": liqueur(rec.item), "score": round(rec.score, 4), "group": rec.group}
    reasons = {"anchor": reference(rec.anchor), "blame": reference(rec.blame), "penalty": round(rec.penalty, 4)}
    return {**head, **reasons, "contributions": parts}


def taxonomy(node: TaxonomyNode) -> dict[str, Any]:
    children = [taxonomy(child) for child in node.children.values()]
    return {"label": node.label, "path": list(node.path), "items": node.item_ids(), "children": children}


def strategies(registry: Mapping[str, Any]) -> list[dict[str, str]]:
    return [{"key": key, "title": item.title, "description": (item.__doc__ or "").strip()} for key, item in registry.items()]
