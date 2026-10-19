"""Поисковая система: точная выборка по фильтрам, иначе — «возможно, Вам понравится»."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from recsys.domain.catalog import Catalog
from recsys.domain.model import Liqueur

from .fallback import Advice, RelaxationAdvisor, UtilityFunction
from .query import SearchQuery

NOT_FOUND = "Не найдено точного соответствия, однако, возможно, Вам понравится:"
FALLBACK_SIZE = 5


@dataclass(frozen=True)
class Hit:
    """Найденный объект: оценка, степень соответствия и невыполненные ограничения."""

    item: Liqueur
    score: float
    fit: float
    exact: bool
    unmet: tuple[tuple[str, float], ...] = ()
    relevance: Optional[float] = None


@dataclass(frozen=True)
class SearchResult:
    """Поисковая выдача; при exact=False — приближённая выдача с сообщением и подсказкой."""

    hits: tuple[Hit, ...]
    exact: bool
    message: Optional[str] = None
    advice: Optional[Advice] = None


class SearchEngine:
    """Параметрический поиск по каталогу или по заданному упорядоченному пулу объектов."""

    def __init__(self, catalog: Catalog, utility: Optional[UtilityFunction] = None,
                 advisor: Optional[RelaxationAdvisor] = None, fallback_size: int = FALLBACK_SIZE) -> None:
        self._catalog, self._size = catalog, fallback_size
        self._utility, self._advisor = utility or UtilityFunction(), advisor or RelaxationAdvisor()

    def search(self, query: SearchQuery, pool: Optional[Sequence[str]] = None,
               relevance: Optional[Mapping[str, float]] = None) -> SearchResult:
        items = [self._catalog.get(i) for i in pool] if pool is not None else list(self._catalog)
        hits = [self._hit(query, item, (relevance or {}).get(item.id)) for item in items]
        exact = tuple(hit for hit in hits if hit.exact)
        return SearchResult(exact, True) if exact else self._fallback(query, items, hits)

    def _hit(self, query: SearchQuery, item: Liqueur, relevance: Optional[float]) -> Hit:
        unmet = tuple((f.describe(), round(degree, 4)) for f, degree in query.unmet(item))
        score = self._utility.score(query, item, relevance)
        return Hit(item, score, query.utility(item), not unmet, unmet, relevance)

    def _fallback(self, query: SearchQuery, items: list[Liqueur], hits: list[Hit]) -> SearchResult:
        ranked = sorted((hit for hit in hits if hit.score > 0), key=lambda hit: (-hit.score, hit.item.id))
        advice = self._advisor.advise(query, items)
        return SearchResult(tuple(ranked[: self._size]), False, NOT_FOUND, advice)
