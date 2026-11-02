"""Проверка опорных слов: классификация вопросов, переформулировок и контрольных фраз ЛР5.

Запуск: python evaluate.py [keywords.json]
Без аргумента берётся data/keywords.json, таблицы пишутся в out/. С аргументом
(например, out/keywords_iteration1.json) результаты только печатаются.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional, Sequence

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dialogue.classifier import KeywordClassifier, Prediction  # noqa: E402
from dialogue.corpus import ORIGINAL, PARAPHRASE, Corpus, Sample  # noqa: E402
from dialogue.refusal import RefusalTemplates  # noqa: E402

DATA, OUT = ROOT / "data", ROOT / "out"
CONTROL = "контроль"
Result = tuple[Sample, Prediction]


def control_samples() -> list[Sample]:
    data = json.loads((DATA / "control.json").read_text(encoding="utf-8"))
    return [Sample(s["text"], s["label"], f"к{i}", CONTROL) for i, s in enumerate(data["samples"], 1)]


def run(samples: Iterable[Sample], keywords: Path) -> list[Result]:
    model = KeywordClassifier.load(keywords, DATA / "lexicon.json")
    return [(sample, model.classify(sample.text)) for sample in samples]


def accuracy(results: Sequence[Result]) -> str:
    right = sum(sample.label == prediction.key for sample, prediction in results)
    return f"{right}/{len(results)}"


def select(results: Sequence[Result], key: Optional[str], kind: str) -> list[Result]:
    return [r for r in results if r[0].kind == kind and key in (None, r[0].label)]


def summary_rows(results: list[Result], keys: Sequence[str]) -> list[list[str]]:
    kinds = (ORIGINAL, PARAPHRASE, CONTROL)
    return [[key or "всего"] + [accuracy(select(results, key, kind)) for kind in kinds] for key in [*keys, None]]


def confusion_rows(results: list[Result], keys: Sequence[str]) -> list[list[object]]:
    pairs = Counter((sample.label, prediction.key) for sample, prediction in results)
    return [[gold] + [pairs[(gold, predicted)] for predicted in keys] for gold in keys]


def error_rows(results: list[Result]) -> list[list[object]]:
    wrong = [(s, p) for s, p in results if s.label != p.key]
    return [[s.question, s.kind, s.text, s.label, p.key, scores(p)] for s, p in wrong]


def scores(prediction: Prediction) -> str:
    return "; ".join(f"{key}={value:g}" for key, value in prediction.scores.items() if value)


def refusal_rows(results: list[Result]) -> list[list[str]]:
    templates = RefusalTemplates.load(DATA / "refusals.json")
    chosen = [(s, p) for s, p in results if s.label == "refuse" and s.kind != PARAPHRASE]
    return [[s.question, s.text, templates.kind(p.utterance).key, templates.answer(p.utterance)] for s, p in chosen]


def write(name: str, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows([list(header), *rows])


def save(results: list[Result], keys: list[str]) -> None:
    write("summary.csv", ["class", "questions", "paraphrases", "control"], summary_rows(results, keys))
    write("confusion.csv", ["gold \\ predicted", *keys], confusion_rows(results, keys))
    write("errors.csv", ["id", "kind", "text", "gold", "predicted", "scores"], error_rows(results))
    write("refusals.csv", ["id", "text", "kind", "answer"], refusal_rows(results))


def show(results: list[Result], keys: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = summary_rows(results, keys)
    print("\n".join(f"{r[0]:<10} вопросы {r[1]:>6}  переформулировки {r[2]:>7}  контроль {r[3]:>5}" for r in rows))
    print("\n".join(f"  x {e[0]} {e[2]!r}: {e[3]} -> {e[4]} ({e[5]})" for e in error_rows(results)) or "  ошибок нет")


def main() -> None:
    keywords = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / "keywords.json"
    corpus = Corpus.load(DATA / "questions.json")
    results, keys = run([*corpus.samples(), *control_samples()], keywords), list(corpus.titles())
    show(results, keys)
    save(results, keys) if len(sys.argv) == 1 else None


if __name__ == "__main__":
    main()
