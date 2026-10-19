"""Поисковый запрос: набор фильтров (композиция спецификаций) и его разбор из JSON."""
from __future__ import annotations

import re

from dataclasses import dataclass, replace
from operator import attrgetter
from typing import Any, Callable, Mapping, Optional

from recsys.domain.catalog import Catalog
from recsys.domain.model import Liqueur, SugarClass
from recsys.domain.taxonomy import TasteTaxonomy
from recsys.recommend.types import ValidationError

from .filters import ChoiceFilter, Filter, FlagFilter, RangeFilter, SugarClassFilter, TasteFilter, TextFilter

# Важность фильтров в функции полезности (порядок согласован с весами меры ЛР2).
WEIGHTS = {
    "name": 3.0, "taste": 3.0, "abv": 2.0, "sugar": 2.0, "bitter": 1.5, "sugar_class": 1.0,
    "wood": 1.0, "country": 1.0, "producer": 1.0, "volume": 0.5,
}
RANGES = {  # ключ → (подпись, единица, атрибут, физически допустимые границы)
    "abv": ("Крепость", "%", "abv", (0.0, 100.0)),
    "sugar": ("Сахар", "г/л", "sugar", (0.0, 1000.0)),
    "volume": ("Объём", "л", "volume", (0.05, 5.0)),
}
FLAGS = {"bitter": ("Горечь", "bitter"), "wood": ("Выдержка в дереве", "wood_contact")}
CHOICES = {"countries": ("country", "Страна", "country"), "producers": ("producer", "Производитель", "producer")}
TRISTATE = {"any": None, "yes": True, "no": False}
MAX_TEXT = 100
NUMBER = re.compile(r"-?\d+(\.\d+)?")


@dataclass(frozen=True)
class SearchQuery:
    """Конъюнкция фильтров (AND); пустой запрос пропускает всё."""

    filters: tuple[Filter, ...] = ()

    def matches(self, item: Liqueur) -> bool:
        return all(f.matches(item) for f in self.filters)

    def utility(self, item: Liqueur) -> float:
        """Функция полезности U(x) = Σ w_f·deg_f(x) / Σ w_f — степень соответствия запросу."""
        total = sum(f.weight for f in self.filters)
        return sum(f.weight * f.degree(item) for f in self.filters) / total if total else 1.0

    def unmet(self, item: Liqueur) -> list[tuple[Filter, float]]:
        return [(f, f.degree(item)) for f in self.filters if not f.matches(item)]

    def describe(self) -> list[str]:
        return [f.describe() for f in self.filters]

    def with_filter(self, index: int, new: Optional[Filter]) -> SearchQuery:
        rest = self.filters[:index] + self.filters[index + 1:]
        return replace(self, filters=rest[:index] + ((new,) if new else ()) + rest[index:])


class QueryParser:
    """Builder: JSON формы фильтров → SearchQuery с проверкой корректности каждого поля."""

    def __init__(self, catalog: Catalog) -> None:
        self._catalog, self._taxonomy = catalog, TasteTaxonomy(catalog)
        spans = {key: self._span(attr) for key, (_, _, attr, _) in RANGES.items()}
        self._spans = spans

    def _span(self, attr: str) -> float:
        values = [getattr(item, attr) for item in self._catalog]
        return max(values) - min(values)

    def parse(self, payload: Mapping[str, Any]) -> SearchQuery:
        parts = [self._safe(build, payload) for build in self._builders()]
        errors = [m for part in parts if isinstance(part, ValidationError) for m in part.messages]
        if errors:
            raise ValidationError(errors)
        return SearchQuery(tuple(f for part in parts for f in part))

    def _builders(self) -> list[Callable[[Mapping[str, Any]], list[Filter]]]:
        ranges = [lambda p, k=key: self._range(p, k) for key in RANGES]
        flags = [lambda p, k=key: self._flag(p, k) for key in FLAGS]
        choices = [lambda p, k=key: self._choice(p, k) for key in CHOICES]
        return [self._text, self._taste, *choices, *ranges, self._sugar_classes, *flags]

    @staticmethod
    def _safe(build: Callable[[Mapping[str, Any]], list[Filter]], payload: Mapping[str, Any]) -> Any:
        try:
            return build(payload)
        except ValidationError as error:
            return error

    def _text(self, payload: Mapping[str, Any]) -> list[Filter]:
        text = str(payload.get("name") or "").strip()
        if len(text) > MAX_TEXT:
            raise ValidationError([f"название: не длиннее {MAX_TEXT} символов"])
        return [TextFilter(text, weight=WEIGHTS["name"])] if text else []

    def _taste(self, payload: Mapping[str, Any]) -> list[Filter]:
        nodes = tuple(tuple(node) for node in _list(payload, "taste") if isinstance(node, list))
        unknown = [" › ".join(map(str, n)) for n in nodes if not n or self._taxonomy.find(n) is None]
        if unknown or len(nodes) != len(_list(payload, "taste")):
            raise ValidationError([f"вкус: неизвестный узел таксономии {', '.join(unknown) or '(формат)'}"])
        return [TasteFilter(nodes, weight=WEIGHTS["taste"])] if nodes else []

    def _choice(self, payload: Mapping[str, Any], key: str) -> list[Filter]:
        weight_key, label, attr = CHOICES[key]
        values, known = frozenset(map(str, _list(payload, key))), set(self._catalog.distinct(attrgetter(attr)))
        if values - known:
            raise ValidationError([f"{label.lower()}: нет в каталоге — {', '.join(sorted(values - known))}"])
        return [ChoiceFilter(weight_key, label, attrgetter(attr), values, WEIGHTS[weight_key])] if values else []

    def _range(self, payload: Mapping[str, Any], key: str) -> list[Filter]:
        label, unit, attr, bounds = RANGES[key]
        low, high = (_number(payload.get(key) or {}, side, label) for side in ("min", "max"))
        _check_range(label, low, high, bounds)
        empty = low is None and high is None
        return [] if empty else [RangeFilter(key, label, unit, attrgetter(attr), self._spans[key], low, high, WEIGHTS[key])]

    def _sugar_classes(self, payload: Mapping[str, Any]) -> list[Filter]:
        values, labels = _list(payload, "sugar_classes"), {c.label: c for c in SugarClass}
        if any(value not in labels for value in values):
            raise ValidationError([f"класс сладости: допустимые термы — {', '.join(labels)}"])
        chosen = frozenset(labels[value] for value in values)
        return [SugarClassFilter(chosen, weight=WEIGHTS["sugar_class"])] if chosen else []

    def _flag(self, payload: Mapping[str, Any], key: str) -> list[Filter]:
        value = payload.get(key, "any")
        if value not in TRISTATE:
            raise ValidationError([f"{FLAGS[key][0].lower()}: допустимо any / yes / no"])
        expected, (label, attr) = TRISTATE[value], FLAGS[key]
        return [] if expected is None else [FlagFilter(key, label, attrgetter(attr), expected, WEIGHTS[key])]


def _list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key) or []
    if not isinstance(value, list):
        raise ValidationError([f"поле «{key}» должно быть списком"])
    return value


def _number(bounds: Any, side: str, label: str) -> Optional[float]:
    raw = _raw_bound(bounds, side, label)
    if raw and not NUMBER.fullmatch(raw):
        raise ValidationError([f"{label.lower()}: «{raw}» — не число"])
    return float(raw) if raw else None


def _raw_bound(bounds: Any, side: str, label: str) -> str:
    if not isinstance(bounds, Mapping):
        raise ValidationError([f"{label.lower()}: ожидается пара значений «от» и «до»"])
    return str(bounds.get(side) if bounds.get(side) is not None else "").strip().replace(",", ".")


def _check_range(label: str, low: Optional[float], high: Optional[float], bounds: tuple[float, float]) -> None:
    inside = all(bounds[0] <= v <= bounds[1] for v in (low, high) if v is not None)
    ordered = low is None or high is None or low <= high
    problems = ([f"{label.lower()}: допустимо от {bounds[0]:g} до {bounds[1]:g}"] if not inside else [])
    if problems or not ordered:
        raise ValidationError(problems + ([f"{label.lower()}: «от» больше «до»"] if not ordered else []))
