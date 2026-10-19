"""Офлайн-сравнение стратегий ПСВ2 (лайки) и ПСВ3 (дизлайки) по протоколу hold-out.

Истинные интересы пользователя моделируются группами L2 таксономии вкуса (ЛР1):
пользователь лайкает все объекты группы, кроме одного скрытого; хорошая система
должна вернуть скрытый объект в top-N. Запуск: python experiments/evaluate.py
"""
from __future__ import annotations

import csv
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import mean
from typing import Callable, Iterable, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from recsys.domain import Catalog, JsonCatalogLoader  # noqa: E402
from recsys.recommend import (  # noqa: E402
    ContentRecommender, Mode, Recommendation, RecommendRequest, UserProfile, build_recommender,
)
from recsys.recommend.factory import POLICY_TYPES, RANKER_TYPES  # noqa: E402
from recsys.recommend.ranking import GroupRanker  # noqa: E402

DATASET = ROOT.parent / "1-dataset" / "dataset.json"
OUT = ROOT / "experiments" / "out"
TOP_N = 5
SIZES = (1, 2, 3)
THRESHOLDS = [round(0.40 + 0.05 * i, 2) for i in range(9)]
STRENGTHS = {"threshold": (0.6, 0.7, 0.8), "subtract": (0.25, 0.5, 1.0), "contrastive": (0.5, 1.0, 2.0)}


@dataclass(frozen=True)
class Case:
    """Сценарий: профиль, скрытые объекты, группы интересов и группа дизлайка."""

    profile: UserProfile
    hidden: tuple[str, ...]
    interests: tuple[tuple[str, ...], ...]
    avoid: tuple[str, ...] = ()


@dataclass
class Env:
    """Общее окружение проверки подходов."""

    catalog: Catalog
    recommender: ContentRecommender
    likes: dict[int, list[Case]]
    inner: list[Case]
    outer: list[Case]


Run = Callable[[Case], list[Recommendation]]
Metric = Callable[[Case, list[Recommendation]], float]


def l2_groups(catalog: Catalog) -> list[tuple[str, ...]]:
    """Группы L2 таксономии (интересы пользователя), объекты в порядке id."""
    keys = catalog.distinct(lambda item: item.taste.prefix(2))
    return [tuple(i.id for i in catalog if i.taste.prefix(2) == key) for key in keys]


def likes_case(groups: Sequence[tuple[str, ...]]) -> Case:
    """ПСВ2: в каждой группе скрыт последний объект, остальные — лайки."""
    likes = tuple(item for group in groups for item in group[:-1])
    return Case(UserProfile(likes), tuple(group[-1] for group in groups), tuple(groups))


def inner_dislike_cases(groups: Sequence[tuple[str, ...]]) -> list[Case]:
    """ПСВ3-а: дизлайк внутри любимого жанра (пример с музыкой из лекции)."""
    big = [group for group in groups if len(group) >= 3]
    return [_inner(group, d, h) for group in big for d in group for h in group if d != h]


def _inner(group: tuple[str, ...], disliked: str, hidden: str) -> Case:
    likes = tuple(item for item in group if item not in (disliked, hidden))
    return Case(UserProfile(likes, (disliked,)), (hidden,), (group,))


def outer_dislike_cases(groups: Sequence[tuple[str, ...]]) -> list[Case]:
    """ПСВ3-б: лайки из группы A, дизлайк — первый объект чужой группы B."""
    pairs = [(a, b) for a in groups for b in groups if a is not b]
    return [Case(UserProfile(a[:-1], (b[0],)), (a[-1],), (a,), b[1:]) for a, b in pairs]


def runner(env: Env, ranker: str, policy: str = "exclude") -> Run:
    def run(case: Case) -> list[Recommendation]:
        mode = Mode.FULL if case.profile.dislikes else Mode.LIKES
        return env.recommender.recommend(RecommendRequest(mode, case.profile, TOP_N, ranker, policy))
    return run


def ids(recs: Sequence[Recommendation]) -> list[str]:
    return [rec.item.id for rec in recs]


def recall(case: Case, recs: list[Recommendation]) -> float:
    """Доля скрытых объектов, попавших в top-N."""
    return sum(hidden in ids(recs) for hidden in case.hidden) / len(case.hidden)


def coverage(case: Case, recs: list[Recommendation]) -> float:
    """Доля групп интересов, которым «служит» хотя бы один элемент выдачи (по ближайшему лайку)."""
    served = {i for i, group in enumerate(case.interests) for rec in recs if rec.anchor and rec.anchor.id in group}
    return len(served) / len(case.interests)


def support(matrix) -> Metric:
    """Средняя близость элемента выдачи к ближайшему лайку («ни на что не похож» → мало)."""
    return lambda case, recs: mean(matrix.best(rec.item.id, case.profile.likes)[1] for rec in recs)


def leakage(case: Case, recs: list[Recommendation]) -> float:
    """Доля выдачи из группы дизлайкнутого объекта (меньше — лучше)."""
    return sum(item in case.avoid for item in ids(recs)) / len(recs)


def average(cases: Iterable[Case], run: Run, metric: Metric) -> float:
    return round(mean(metric(case, run(case)) for case in cases), 4)


def write_csv(name: str, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows([header, *rows])


def likes_row(env: Env, ranker: str, size: int) -> list[object]:
    cases, run = env.likes[size], runner(env, ranker)
    metrics = (recall, coverage, support(env.recommender.matrix))
    return [ranker, size, len(cases)] + [average(cases, run, m) for m in metrics]


def threshold_row(env: Env, theta: float) -> list[object]:
    with swapped(env.recommender.rankers, "group", GroupRanker(env.recommender.matrix, theta)):
        run = runner(env, "group")
        return [theta] + [average(env.likes[k], run, metric) for k in SIZES for metric in (recall, coverage)]


@contextmanager
def swapped(mapping: dict, key: str, value: object) -> Iterator[None]:
    """Временная подмена стратегии в реестре (для перебора параметров)."""
    original, mapping[key] = mapping[key], value
    yield
    mapping[key] = original


def dislike_row(env: Env, ranker: str, policy: str) -> list[object]:
    run = runner(env, ranker, policy)
    values = [average(env.inner, run, recall), average(env.outer, run, recall), average(env.outer, run, leakage)]
    return [ranker, policy] + values


def strength_row(env: Env, policy: str, strength: float) -> list[object]:
    policy_type = {cls.key: cls for cls in POLICY_TYPES}[policy]
    with swapped(env.recommender.policies, policy, policy_type(env.recommender.matrix, strength)):
        return [policy, strength] + dislike_row(env, "group", policy)[2:]


def environment() -> Env:
    catalog = JsonCatalogLoader(DATASET).load()
    groups = l2_groups(catalog)
    likes = {size: [likes_case(combo) for combo in combinations(groups, size)] for size in SIZES}
    return Env(catalog, build_recommender(catalog), likes, inner_dislike_cases(groups), outer_dislike_cases(groups))


def main() -> None:
    env = environment()
    _likes(env)
    _dislikes(env)


def _likes(env: Env) -> None:
    write_csv("v2_rankers.csv", ["ranker", "groups", "cases", "recall", "coverage", "support"],
              [likes_row(env, cls.key, size) for size in SIZES for cls in RANKER_TYPES])
    write_csv("v2_threshold.csv", ["theta"] + [f"{m}_k{k}" for k in SIZES for m in ("recall", "coverage")],
              [threshold_row(env, theta) for theta in THRESHOLDS])


def _dislikes(env: Env) -> None:
    write_csv("v3_policies.csv", ["ranker", "policy", "recall_inner", "recall_outer", "leakage_outer"],
              [dislike_row(env, r, cls.key) for r in ("max", "roundrobin", "group") for cls in POLICY_TYPES])
    write_csv("v3_strength.csv", ["policy", "strength", "recall_inner", "recall_outer", "leakage_outer"],
              [strength_row(env, policy, s) for policy, values in STRENGTHS.items() for s in values])


if __name__ == "__main__":
    main()
