"""Общие объекты тестов ЛР4: модули ЛР3 подключаются через bootstrap."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bootstrap  # noqa: E402,F401
from recsys.service import RecommendationService  # noqa: E402
from unified.service import UnifiedService  # noqa: E402


@lru_cache(maxsize=1)
def unified() -> UnifiedService:
    return UnifiedService(RecommendationService.from_dataset())
