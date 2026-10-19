"""Рисунки для отчёта по результатам experiments/evaluate.py. Запуск: python experiments/plots.py"""
from __future__ import annotations

import csv
import sys
from itertools import product
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from recsys.domain import JsonCatalogLoader  # noqa: E402
from recsys.recommend import build_matrix  # noqa: E402
from recsys.recommend.ranking import GROUP_THRESHOLD  # noqa: E402

OUT = ROOT / "experiments" / "out"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
RELATIONS = ["разные L1", "общий L1", "общий L2", "общий лист L3"]
RANKER_LABELS = {"mean": "А. среднее", "recency": "Б. время", "balanced": "В. баланс",
                 "max": "максимум", "roundrobin": "Г′. по лайкам", "group": "Г. группы"}
POLICY_LABELS = {"threshold": "2. порог τ", "subtract": "3. вычитание β", "contrastive": "4. контраст β"}
MARKERS = {"threshold": "s", "subtract": "^", "contrastive": "o"}


def rows(name: str) -> list[dict[str, str]]:
    with open(OUT / name, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def styled(ax: plt.Axes, title: str, ylabel: str) -> plt.Axes:
    ax.set_title(title, fontsize=11, color=INK, loc="left")
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    return ax


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


def relation_values() -> list[list[float]]:
    catalog = JsonCatalogLoader(ROOT.parent / "1-dataset" / "dataset.json").load()
    matrix, items = build_matrix(catalog), list(catalog)
    pairs = [(a, b) for a, b in product(items, items) if a.id < b.id]
    return [[matrix.get(a.id, b.id) for a, b in pairs if a.taste.common_depth(b.taste) == d] for d in range(4)]


def plot_relations() -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.boxplot(relation_values(), tick_labels=RELATIONS, widths=0.45, patch_artist=True,
               boxprops={"facecolor": "#cde0f6", "edgecolor": SERIES[0]}, medianprops={"color": INK})
    ax.axhline(GROUP_THRESHOLD, color=SERIES[1], linewidth=2, linestyle="--", label=f"θ = {GROUP_THRESHOLD}")
    save(_legend(styled(ax, "Итоговая близость пар по положению в таксономии", "sim(x, y)")), "sim_by_relation.png")


def _legend(ax: plt.Axes) -> plt.Figure:
    ax.legend(frameon=False, loc="upper left")
    return ax.figure


def plot_rankers() -> None:
    data, keys = rows("v2_rankers.csv"), list(RANKER_LABELS)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, metric in zip(axes, ("recall", "coverage")):
        _bars(styled(ax, f"{metric}(5)", "доля"), data, keys, metric)
    save(_legend(axes[0]), "v2_rankers.png")


def _bars(ax: plt.Axes, data: list[dict[str, str]], keys: list[str], metric: str) -> None:
    for shift, (size, color) in enumerate(zip(("2", "3"), SERIES)):
        values = [float(r[metric]) for k in keys for r in data if r["ranker"] == k and r["groups"] == size]
        ax.bar([i + 0.38 * shift for i in range(len(keys))], values, 0.36, color=color, label=f"{size} группы интересов")
    ax.set_xticks([i + 0.19 for i in range(len(keys))], [RANKER_LABELS[k] for k in keys], rotation=25, ha="right")
    ax.set_ylim(0.5, 1.02)


def plot_threshold() -> None:
    data = rows("v2_threshold.csv")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for key, label, color in (("recall_k3", "recall(5)", SERIES[0]), ("coverage_k3", "coverage(5)", SERIES[1])):
        ax.plot([float(r["theta"]) for r in data], [float(r[key]) for r in data], "-o", color=color, lw=2, label=label)
    _theta_line(ax)


def _theta_line(ax: plt.Axes) -> None:
    ax.axvline(GROUP_THRESHOLD, color=MUTED, linestyle=":")
    save(_legend(styled(ax, "Г. Группы лайков: выбор порога θ (3 группы интересов)", "доля")), "v2_threshold.png")


def plot_policies() -> None:
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for color, policy in zip(SERIES[1:], POLICY_LABELS):
        _policy_points(ax, [r for r in rows("v3_strength.csv") if r["policy"] == policy], policy, color)
    _baseline(ax, next(r for r in rows("v3_policies.csv") if r["ranker"] == "group" and r["policy"] == "exclude"))
    _finish_policies(ax)


def _finish_policies(ax: plt.Axes) -> None:
    ax.set_xlabel("recall(5) при дизлайке внутри любимого жанра (выше — лучше)", color=MUTED)
    save(_legend(styled(ax, "PCv3: сохранение жанра против «утечки» дизлайка", "leakage(5) (ниже — лучше)")),
         "v3_tradeoff.png")


def _baseline(ax: plt.Axes, row: dict[str, str]) -> None:
    point = (float(row["recall_inner"]), float(row["leakage_outer"]))
    ax.plot(*point, marker="D", color=SERIES[0], markersize=8, linestyle="none", label="1. только исключить")


def _policy_points(ax: plt.Axes, data: list[dict[str, str]], policy: str, color: str) -> None:
    xs, ys = [float(r["recall_inner"]) for r in data], [float(r["leakage_outer"]) for r in data]
    ax.plot(xs, ys, "-", marker=MARKERS[policy], color=color, markersize=8, lw=2, label=POLICY_LABELS[policy])
    for x, y, r in zip(xs, ys, data):
        ax.annotate(r["strength"], (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8, color=MUTED)


def main() -> None:
    for plot in (plot_relations, plot_rankers, plot_threshold, plot_policies):
        plot()


if __name__ == "__main__":
    main()
