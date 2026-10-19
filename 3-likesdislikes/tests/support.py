"""Общие объекты для тестов: каталог и рекомендатель строятся один раз."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from recsys.service import RecommendationService  # noqa: E402


@lru_cache(maxsize=1)
def service() -> RecommendationService:
    return RecommendationService.from_dataset()
