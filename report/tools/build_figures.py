"""Сборка рисунков отчёта: диаграммы Graphviz, графики сравнений, тепловые карты ЛР2.

Запуск из корня репозитория: python report/tools/build_figures.py
Нужен Graphviz (dot) в PATH. Снимки интерфейса (img/ui) делаются вручную или Playwright.
Все рисунки дублируются в img/normcontrol/, т.к. imgmode.tex выбирает один из каталогов.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1]
ROOT = REPORT.parent
IMG = REPORT / "img"
LR2_HEATMAPS = ["num_euclidean_dist", "num_chebyshev_dist", "num_cosine_dist", "agg_total_sim",
                "agg_schemes_compare", "agg_weights_bar", "tax_taste_sim", "bin_sokal_michener_sim"]
LR3_PLOTS = ["v2_rankers", "v2_threshold", "sim_by_relation", "v3_tradeoff"]


def render_diagrams() -> None:
    subprocess.run([sys.executable, str(REPORT / "tools" / "taxonomy_dot.py")], check=True)
    subprocess.run([sys.executable, str(REPORT / "tools" / "uml_dot.py")], check=True)
    for dot in sorted((REPORT / "diags").glob("*.dot")):
        subprocess.run(["dot", "-Tpng", "-Gdpi=170", str(dot), "-o", str(IMG / "diags" / f"{dot.stem}.png")], check=True)


def copy_plots() -> None:
    sources = {"lr2": (ROOT / "2-metrics" / "out" / "heatmaps", LR2_HEATMAPS),
               "lr3": (ROOT / "3-likesdislikes" / "experiments" / "out", LR3_PLOTS)}
    for folder, (source, names) in sources.items():
        for name in names:
            shutil.copy2(source / f"{name}.png", IMG / folder / f"{name}.png")


def mirror_normcontrol() -> None:
    for folder in ("diags", "lr2", "lr3", "ui"):
        shutil.copytree(IMG / folder, IMG / "normcontrol" / folder, dirs_exist_ok=True)
    shutil.copy2(IMG / "bmstu_logo.jpg", IMG / "normcontrol" / "bmstu_logo.jpg")


def main() -> None:
    for folder in ("diags", "lr2", "lr3", "ui", "normcontrol"):
        (IMG / folder).mkdir(parents=True, exist_ok=True)
    render_diagrams()
    copy_plots()
    mirror_normcontrol()


if __name__ == "__main__":
    main()
