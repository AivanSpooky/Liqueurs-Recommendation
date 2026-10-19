"""Сравнение способов ответа на пустую выдачу: функция полезности vs ослабление фильтров.

Протокол «восстановления задуманного объекта»: берём объект x, строим запрос из его
вкуса (узел L2), класса сладости и выдержки в дереве и портим два ограничения
(сдвигаем диапазон, меняем страну или горечь) так, чтобы точных совпадений не было.
Хорошая стратегия должна поставить x как можно выше. Запуск: python experiments/compare_fallback.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from itertools import combinations
from statistics import mean
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bootstrap  # noqa: E402,F401
from recsys.domain.catalog import Catalog  # noqa: E402
from recsys.domain.model import Liqueur  # noqa: E402
from recsys.service import RecommendationService  # noqa: E402
from search.engine import SearchEngine  # noqa: E402
from search.query import QueryParser, SearchQuery  # noqa: E402

OUT = ROOT / "experiments" / "out"
Perturb = Callable[[Liqueur, Catalog], dict]
PERTURBATIONS: dict[str, Perturb] = {
    "крепость +3..8 п.п.": lambda x, c: {"abv": {"min": x.abv + 3, "max": x.abv + 8}},
    "сахар +20..60 г/л": lambda x, c: {"sugar": {"min": x.sugar + 20, "max": x.sugar + 60}},
    "чужая страна": lambda x, c: {"countries": [next(i.country for i in c if i.country != x.country)]},
    "обратная горечь": lambda x, c: {"bitter": "no" if x.bitter else "yes"},
}


def base_filters(item: Liqueur) -> dict:
    flags = {"wood": "yes" if item.wood_contact else "no"}
    return {"taste": [list(item.taste.prefix(2))], "sugar_classes": [item.sugar_class.label], **flags}


def rank_of(item_id: str, ids: list[str]) -> Optional[int]:
    return ids.index(item_id) + 1 if item_id in ids else None


def utility_rank(engine: SearchEngine, query: SearchQuery, item: Liqueur) -> Optional[int]:
    return rank_of(item.id, [hit.item.id for hit in engine.search(query).hits])


def relaxation_rank(engine: SearchEngine, query: SearchQuery, item: Liqueur) -> Optional[int]:
    advice = engine.search(query).advice
    return rank_of(item.id, [hit.item.id for hit in engine.search(advice.query).hits]) if advice else None


def taste_dropped(engine: SearchEngine, query: SearchQuery) -> bool:
    advice = engine.search(query).advice
    return bool(advice) and any(text.startswith("Вкус") for text in advice.changes)


def spoiled(item: Liqueur, pair: tuple, catalog: Catalog) -> dict:
    return {key: value for name in pair for key, value in PERTURBATIONS[name](item, catalog).items()}


def case_row(engine: SearchEngine, parser: QueryParser, item: Liqueur, pair: tuple, catalog: Catalog) -> Optional[list]:
    query, name = parser.parse({**base_filters(item), **spoiled(item, pair, catalog)}), " + ".join(pair)
    if engine.search(query).exact:
        return None
    ranks = [utility_rank(engine, query, item), relaxation_rank(engine, query, item)]
    return [item.id, name, *ranks, taste_dropped(engine, query)]


def hit(ranks: list[Optional[int]], k: int) -> float:
    return round(mean(r is not None and r <= k for r in ranks), 4)


def summary(rows: list[list]) -> list[list]:
    columns = {"функция полезности": 2, "ослабление фильтров": 3}
    table = [[name, hit([r[i] for r in rows], 1), hit([r[i] for r in rows], 5)] for name, i in columns.items()]
    return table + [["доля советов «ослабить вкус»", round(mean(r[4] for r in rows), 4), ""]]


def main() -> None:
    service = RecommendationService.from_dataset()
    engine, parser, catalog = SearchEngine(service.catalog), QueryParser(service.catalog), service.catalog
    pairs = list(combinations(PERTURBATIONS, 2))
    _write([r for x in catalog for pair in pairs if (r := case_row(engine, parser, x, pair, catalog))])


def _write(rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "fallback_cases.csv", "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows([["item", "perturbation", "utility_rank", "relax_rank", "taste_dropped"], *rows])
    with open(OUT / "fallback_summary.csv", "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows([["strategy", "hit@1", "hit@5"], *summary(rows), ["cases", len(rows), ""]])


if __name__ == "__main__":
    main()
