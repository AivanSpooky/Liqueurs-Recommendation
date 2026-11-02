"""Общие объекты тестов ЛР5."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT))

from dialogue.classifier import KeywordClassifier  # noqa: E402
from dialogue.corpus import Corpus  # noqa: E402


@lru_cache(maxsize=1)
def classifier() -> KeywordClassifier:
    return KeywordClassifier.load(DATA / "keywords.json", DATA / "lexicon.json")


@lru_cache(maxsize=1)
def corpus() -> Corpus:
    return Corpus.load(DATA / "questions.json")
