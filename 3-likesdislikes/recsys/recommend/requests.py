"""Разбор и проверка корректности пользовательского запроса рекомендаций."""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Collection, Mapping, Optional

from ..domain.catalog import Catalog
from .types import Mode, RecommendRequest, UserProfile, ValidationError

Rule = Callable[[RecommendRequest, Catalog], list[str]]
MODE_SHAPE = {  # (минимум лайков, максимум лайков, разрешены ли дизлайки)
    Mode.SEED: (1, 1, False), Mode.LIKES: (1, None, False), Mode.FULL: (0, None, True),
}
MODE_HINT = {
    Mode.SEED: "v1: выберите ровно один ликёр-затравку",
    Mode.LIKES: "v2: отметьте хотя бы один понравившийся ликёр",
    Mode.FULL: "v3: отметьте хотя бы один лайк или дизлайк",
}
DISLIKES_UNUSED = "в этом режиме дизлайки не используются — переключитесь на v3"


def _ids(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError([f"поле «{key}» должно быть списком идентификаторов"])
    return tuple(item.strip() for item in value)


def _top_n(payload: Mapping[str, Any]) -> int:
    value = payload.get("top_n", 5)
    if isinstance(value, bool) or not str(value).strip().lstrip("-").isdigit():
        raise ValidationError(["число рекомендаций N должно быть целым числом"])
    return int(str(value).strip())


def _mode(payload: Mapping[str, Any]) -> Mode:
    modes = {mode.value: mode for mode in Mode}
    if payload.get("mode") not in modes:
        raise ValidationError([f"неизвестный режим {payload.get('mode')!r}; допустимо: v1, v2, v3"])
    return modes[payload["mode"]]


def _optional_ids(key: str) -> Callable[[Mapping[str, Any]], Optional[tuple[str, ...]]]:
    return lambda payload: _ids(payload, key) if payload.get(key) is not None else None


def _text(key: str, default: str) -> Callable[[Mapping[str, Any]], str]:
    return lambda payload: str(payload.get(key, default))


FIELDS: dict[str, Callable[[Mapping[str, Any]], Any]] = {
    "mode": _mode, "likes": lambda p: _ids(p, "likes"), "dislikes": lambda p: _ids(p, "dislikes"),
    "top_n": _top_n, "ranker": _text("ranker", "group"), "policy": _text("policy", "contrastive"),
    "pool": _optional_ids("pool"),
}


class RequestParser:
    """Синтаксический уровень: JSON → RecommendRequest; ошибки всех полей собираются вместе."""

    def parse(self, payload: Mapping[str, Any]) -> RecommendRequest:
        results = {name: self._field(parse, payload) for name, parse in FIELDS.items()}
        errors = [message for value in results.values() if isinstance(value, ValidationError) for message in value.messages]
        if errors:
            raise ValidationError(errors)
        return self._build(results)

    @staticmethod
    def _field(parse: Callable[[Mapping[str, Any]], Any], payload: Mapping[str, Any]) -> Any:
        try:
            return parse(payload)
        except ValidationError as error:
            return error

    @staticmethod
    def _build(values: dict[str, Any]) -> RecommendRequest:
        profile = UserProfile(values.pop("likes"), values.pop("dislikes"))
        return RecommendRequest(profile=profile, **values)


def unknown_ids(request: RecommendRequest, catalog: Catalog) -> list[str]:
    ids = request.profile.likes + request.profile.dislikes + (request.pool or ())
    return [f"объекта {item!r} нет в каталоге" for item in dict.fromkeys(ids) if item not in catalog]


def duplicates(request: RecommendRequest, catalog: Catalog) -> list[str]:
    counts = Counter(request.profile.likes) + Counter(request.profile.dislikes)
    return [f"объект {item!r} указан несколько раз" for item, n in counts.items() if n > 1
            and item not in set(request.profile.likes) & set(request.profile.dislikes)]


def overlap(request: RecommendRequest, catalog: Catalog) -> list[str]:
    both = sorted(set(request.profile.likes) & set(request.profile.dislikes))
    return [f"объект {item!r} одновременно в лайках и дизлайках" for item in both]


def mode_shape(request: RecommendRequest, catalog: Catalog) -> list[str]:
    low, high, dislikes_allowed = MODE_SHAPE[request.mode]
    count, profile = len(request.profile.likes), request.profile
    errors = [MODE_HINT[request.mode]] if count < low or (high is not None and count > high) else []
    return errors + ([DISLIKES_UNUSED] if profile.dislikes and not dislikes_allowed else [])


def anything_rated(request: RecommendRequest, catalog: Catalog) -> list[str]:
    empty = request.mode is Mode.FULL and not request.profile.rated
    return ["отметьте хотя бы один лайк или дизлайк"] if empty else []


def has_candidates(request: RecommendRequest, catalog: Catalog) -> list[str]:
    pool = request.pool if request.pool is not None else tuple(catalog.ids())
    left = [item for item in pool if item not in request.profile.rated]
    return [] if left else ["не осталось объектов для рекомендации: все уже оценены"]


def top_n_range(request: RecommendRequest, catalog: Catalog) -> list[str]:
    valid = 1 <= request.top_n <= len(catalog)
    return [] if valid else [f"N должно быть в диапазоне от 1 до {len(catalog)}"]


DEFAULT_RULES: tuple[Rule, ...] = (
    unknown_ids, duplicates, overlap, mode_shape, anything_rated, has_candidates, top_n_range,
)


class RequestValidator:
    """Семантический уровень: проверка запроса набором правил (паттерн Specification/Rules)."""

    def __init__(self, catalog: Catalog, rankers: Collection[str], policies: Collection[str]) -> None:
        self._catalog = catalog
        self._choices = {"ranker": set(rankers), "policy": set(policies)}

    def validate(self, request: RecommendRequest) -> RecommendRequest:
        errors = [message for rule in DEFAULT_RULES for message in rule(request, self._catalog)]
        errors += self._unknown_choices(request)
        if errors:
            raise ValidationError(errors)
        return request

    def _unknown_choices(self, request: RecommendRequest) -> list[str]:
        chosen = {"ranker": request.ranker, "policy": request.policy}
        return [f"неизвестная стратегия {key}={value!r}" for key, value in chosen.items()
                if value not in self._choices[key]]
